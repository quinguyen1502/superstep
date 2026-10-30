"""Run lifecycle: resolve what to run, execute it off-thread with cancel/timeout, persist history.

Transport-agnostic: the WebSocket controller passes `send(ev)` and `listen()` callables.
"""
import asyncio, contextvars, functools, json, threading, time, uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterator, Optional
from ..core import config
from ..core import permissions as P
from ..core.errors import CATALOG, AppError
from ..engine import repo_import
from ..engine import agents, subgraphs
from ..engine.errors import ValidationError
from ..engine.issues import Issue, issues_of
from ..engine.limits import cap_event, cap_run, safe_error, size
from ..engine.effects import Effects
from ..engine.ports import Ports
from ..engine.runtime import resume_nodes, run_stream
from ..models import Run
from ..repositories import RunRepository, StaleLease, WorkflowRepository
from .job_queue import enqueue_resume
from .run_bus import InMemoryRunBus, RunBus
from . import time_travel
from .telemetry import Telemetry, summarize, trace_url
from ..core.logging import get_logger
from .workflow_diff import same_content


@dataclass
class RunPlan:
    workflow_id: Optional[str]
    workflow: dict
    input: dict
    resolve: Optional[Callable[[str], dict]] = None  # credential lookup bound to the run's user
    # resuming a waiting run (TASK-0006): same run id, earlier events, {node, value, state}
    run_id: Optional[str] = None
    previous: Optional["Run"] = None
    resume: Optional[dict] = None
    source: str = "ui"  # ui | api (TASK-0007) | schedule | test (TASK-0067)
    version: Optional[int] = None  # stored workflow version that runs; None = unsaved edits (TASK-0008)
    trace_parent: Optional[dict] = None  # {trace_id, span_id} of the previous trace segment (TASK-0020)
    recovered: bool = False       # continuing a queue job whose worker died (TASK-0020)
    checkpointing: bool = False   # save a progress checkpoint after each node (queue jobs, TASK-0020)
    fence: Optional[int] = None   # lease generation of the queue job (TASK-0021): every write carries it
    attempt: int = 1              # queue delivery attempt, sent to side effects as X-Studio-Attempt
    effects: Optional[Effects] = None  # idempotency keys / ledger / fencing guard, set by RunService._execute
    resumed_by: Optional[dict] = None  # {channel, user_id} when an approval channel answered (TASK-0022)
    ports: Optional[Ports] = None  # knowledge base / MCP services bound to the run's user (TASK-0012/0013)
    invalid: Optional[list] = None  # subgraph reference errors found while planning (TASK-0011), reported as WORKFLOW_INVALID
    steps: Optional[int] = None  # stop after this many working supersteps (TASK-0036); None runs to the end
    until: Optional[str] = None  # pause after this node finishes (TASK-0036); None runs to the end
    forked: Optional[dict] = None  # {run_id, checkpoint, nodes, edited}: a new run forked from a checkpoint of another one
    pending_wave: bool = False  # an answer of one wait in a wave was stored; the run stays waiting (TASK-0158)
    pending_event: Optional[dict] = None  # the next slot's run_waiting, so the panel stops showing the one just answered

    @property
    def imported(self) -> bool:
        return (self.workflow.get("source") or {}).get("kind") == "langgraph_import"

    def events(self) -> Iterator[dict]:
        if self.imported: return repo_import.run_imported(self.workflow, dict(self.input), resume=self.resume, checkpointing=self.checkpointing)
        if self.invalid: raise ValidationError(self.invalid)
        return run_stream(self.workflow, self.input, self.resolve, self.resume, self.effects, ports=self.ports, steps=self.steps, until=self.until)


def error_event(error: dict, **extra) -> dict:
    """WebSocket error event: structured `error` {code, message, details?} plus the legacy `errors` list, and the
    codes of validation messages in `issues` (TASK-0132)."""
    details = error.get("details")
    errors = details if isinstance(details, list) and details else [error["message"]]
    return {"type": "error", **extra, "error": error, "errors": errors,
            **({"issues": issues_of(errors)} if any(isinstance(e, Issue) for e in errors) else {})}


def _normalise(ev: dict) -> dict:
    """Give engine/sandbox error events (which only carry `errors`) the structured `error` field."""
    if ev.get("type") != "error" or "error" in ev: return ev
    msgs = ev.get("errors") or [CATALOG["RUN_FAILED"][1]]
    code = ev.pop("code", None) or ("NODE_FAILED" if ev.get("node") else "RUN_FAILED")
    ev["error"] = {"code": code, "message": msgs[0], **({"details": msgs} if len(msgs) > 1 else {})}
    return ev


RESPONSE_MAX = 10_000  # characters of a human response


def human_response(response) -> str:
    """A Human node's answer: text, or JSON true / false for approved / rejected (DEC-0013)."""
    if isinstance(response, bool): response = "approved" if response else "rejected"
    if not isinstance(response, str) or len(response) > RESPONSE_MAX: raise AppError("RUN_RESPONSE_INVALID", max=RESPONSE_MAX)
    return response


def _request_node(req: dict) -> Optional[str]:
    """The slot a studio answer names. Missing or blank means the caller did not say which question it showed."""
    node = req.get("node")
    return node if isinstance(node, str) and node else None


def _approval_node(cp: dict, node: Optional[str]) -> Optional[str]:
    """Which approval this answer is for. One open approval can be unnamed. Several cannot: naming none would
    answer the first, which may not be the question on screen."""
    approvals = [w.get("node") for w in cp.get("waits") or [] if isinstance(w, dict) and w.get("kind") == "approval" and w.get("node")]
    if node:
        if node not in approvals: raise AppError("RUN_NOT_WAITING")
        return node
    if len(approvals) > 1: raise AppError("RUN_NOT_WAITING")
    return approvals[0] if approvals else None


def _follow_up_wait(cp: dict) -> Optional[dict]:
    """The run_waiting event for the next open slot, after one of a wave was stored. An approval comes before a child."""
    waits = [w for w in cp.get("waits") or [] if isinstance(w, dict)]
    w = next((x for x in waits if x.get("kind") == "approval"), None) or (waits[0] if waits else None)
    if not w: return None
    ev = {"type": "run_waiting", "node": w.get("node"), "prompt": w.get("prompt") or "", "ts": time.time()}
    for k in ("label", "tool", "arguments"):
        if w.get(k) is not None: ev[k] = w[k]
    if w.get("kind") == "child" and w.get("run_id"):
        ev["wait"] = {"kind": "child", "run_id": w["run_id"]}
        if w.get("workflow_id") is not None: ev["workflow_id"] = w["workflow_id"]
    return cap_event(ev)

log = get_logger("runs")
def code_runtime_of(events: list) -> Optional[str]:
    """Where this run's Code nodes ran (TASK-0056): `subprocess` if any call ran unisolated, else `docker`, else None."""
    seen = {(e.get("code_output") or {}).get("runtime") for e in events if isinstance(e, dict) and isinstance(e.get("code_output"), dict)}
    return "subprocess" if "subprocess" in seen else ("docker" if "docker" in seen else None)


CANCEL_API = object()  # worker -> loop marker: the bus reported a cancel request
FENCED = object()      # worker -> loop marker: another worker claimed this run (stale lease, TASK-0021)
RESUME_KEYS = ("node", "nodes", "state", "counts", "blob")  # what a progress checkpoint stores to continue from


class _RunLedger:
    """Ledger adapter for one run (engine.effects.Ledger): JSON in the node_results table, fenced writes."""
    def __init__(self, repo, rid: str, fence: Optional[int]): self.repo, self.rid, self.fence = repo, rid, fence
    def get(self, nid, it):
        row = self.repo.get(self.rid, nid, it)
        return json.loads(row.delta) if row else None
    def put(self, nid, it, delta, key): self.repo.put(self.rid, nid, it, _dumps(delta), key, self.fence)


def _dumps(x) -> str: return json.dumps(x, ensure_ascii=False, default=str)


def _parse_steps(req: dict) -> Optional[int]:
    """One-step runs send steps: 1. Omit the field to run until the end."""
    if "steps" not in req or req["steps"] is None: return None
    raw = req["steps"]
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1: raise AppError("RUN_REQUEST_INVALID")
    return raw


def _parse_until(req: dict) -> Optional[str]:
    """Run-to-node sends until: the node id to pause after. Omit the field to ignore it."""
    if "until" not in req or req["until"] is None: return None
    raw = req["until"]
    if not isinstance(raw, str) or not raw: raise AppError("RUN_REQUEST_INVALID")
    return raw



def _write_in_thread(fn, *args, **kwargs) -> asyncio.Future:
    """Run a write (run history, run bus entry) on a worker thread, submitted now and never cancelled (TASK-0059/0060).
    Cancelling the task that awaits it (client gone, server or test client shutting its loop down) raises CancelledError
    there but does not drop the write: plain `await asyncio.to_thread(...)` cancels the queued work item if no thread
    has picked it up."""
    call = functools.partial(contextvars.copy_context().run, fn, *args, **kwargs)
    return asyncio.shield(asyncio.get_running_loop().run_in_executor(None, call))


class RunService:
    def __init__(self, workflows: WorkflowRepository, runs: RunRepository, credentials=None, bus: RunBus | None = None,
                 telemetry: Telemetry | None = None, versions=None, notifier=None, ledger=None, approvals=None,
                 deliveries: Optional[Callable[[], object]] = None, knowledge=None, mcp=None, access=None, policy=None, quota=None, audit=None,
                 tests: Optional[Callable[[], object]] = None, chat: Optional[Callable[[], object]] = None,
                 jobs: Optional[Callable[[], object]] = None):
        """credentials: CredentialService (optional; without it, nodes with credential_id fail clearly).
        bus: RunBus for cross-process cancel + event fan-out (in-memory when not given)."""
        self.workflows, self.runs, self.credentials = workflows, runs, credentials
        self.bus = bus or InMemoryRunBus()
        self.versions = versions  # WorkflowVersionRepository (optional): tags runs with the version they ran
        self.telemetry = telemetry or Telemetry(exporters=[], metric_readers=[])  # no-op unless an exporter is configured
        self.notifier = notifier  # NotificationService (optional): in-app/e-mail/webhook when a run waits or expires (TASK-0020)
        self.ledger = ledger      # NodeResultRepository (optional): node-result ledger of queue jobs (TASK-0021)
        self.deliveries = deliveries  # -> DeliveryService (optional): callback_url webhook when an API run settles
        self.approvals = approvals  # ApprovalService (optional): Slack/Telegram approval requests of Human nodes (TASK-0022)
        self.knowledge = knowledge  # KnowledgeService (optional): Retriever nodes (TASK-0012)
        self.audit = audit  # AuditService (optional): Code nodes running without isolation (TASK-0056)
        self.mcp = mcp  # McpService (optional): MCP tool nodes (TASK-0013)
        self.policy = policy  # PolicyService (optional): org resources at run time (TASK-0029)
        self.access = access  # AccessService (optional): shared workflows and roles (TASK-0014); None = owner-only
        self.quota = quota  # rate_limit.Counter (optional): recipients Send email nodes may reach per owner per hour (TASK-0051)
        self.tests = tests  # -> WorkflowTestService (optional): records a finished test run, answers a waiting one (TASK-0067)
        self.chat = chat  # -> ChatRunService (optional): answers a chat-trigger run in its thread (TASK-0075)
        self.jobs = jobs  # -> JobQueue (optional): child runs of workflow tools and their parents' resumes (TASK-0134)

    # ---- cancel from any API process (POST /api/runs/{id}/cancel) ----
    def cancel(self, rid: str, uid: str) -> None:
        row = self.runs.get(rid) if self.bus.owner(rid) is None else None  # not running here or elsewhere
        if row is not None and row.status == "queued" and row.owner == uid:  # API run not picked up yet: worker skips it
            self.runs.set_status(rid, "cancelled")
            if row.parent_run_id: self.resume_parent(rid)  # a cancelled child still answers its parent (TASK-0134)
            return None
        if row is not None and row.status == "paused":
            if row.owner != uid: raise AppError("RUN_NOT_FOUND")
            return self._close_waiting(row, {"type": "run_cancelled", "ts": time.time(), "reason": "api"}, "cancelled", uid)
        if row is not None: return self.cancel_waiting(rid, uid)
        if self.bus.owner(rid) != uid: raise AppError("RUN_NOT_FOUND")  # unknown, finished or not yours
        self.bus.request_cancel(rid)

    # ---- planning / validation of the client request ----
    def plan(self, uid: str, req) -> RunPlan:
        if not isinstance(req, dict): raise AppError("RUN_REQUEST_INVALID")
        steps = _parse_steps(req); until = _parse_until(req)
        if req.get("chat_session_id"): return self._plan_chat(uid, req, steps, until)
        if req.get("fork") is not None: return self._plan_fork(uid, req["fork"], steps, until)
        if req.get("resume_run_id"): return self.plan_resume(uid, req["resume_run_id"], req.get("response"), steps=steps, until=until, node=_request_node(req))
        wid = req.get("workflow_id"); row = None
        if wid: row = self._workflow(wid, uid, P.RUN)
        elif self.access is not None: self.access.require(uid, P.WORKFLOWS_CREATE)  # ad-hoc graphs: viewers only run saved workflows
        inp = req.get("input", {})
        if not isinstance(inp, dict): raise AppError("RUN_INPUT_INVALID")
        if size(inp) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE", max_kb=config.input_max() // 1024)
        stored = json.loads(row.data or "{}") if row else {}
        edits = row is None or self.access is None or self.access.may(wid, uid, P.EDIT)
        # public demo: visitors (viewers) may run their unsaved edits; the engine refuses code, HTTP and email there
        if config.demo_mode() and not stored.get("source"): edits = True
        wf = stored if stored.get("source") or not edits else (req.get("workflow") or stored)  # unsaved edits need edit access
        if not isinstance(wf, dict) or size(wf) > config.workflow_max(): raise AppError("WORKFLOW_TOO_LARGE", max_kb=config.workflow_max() // 1024)
        if config.demo_mode() and P.code_sources(wf): raise AppError("DEMO_CODE_DISABLED")  # the clear code, not WORKFLOW_INVALID
        n = req.get("version")  # a stored version's snapshot instead (workflow tests run against version, TASK-0068)
        if n is not None:
            v = self.versions.get(wid, n) if wid and edits and self.versions is not None and isinstance(n, int) and not isinstance(n, bool) else None
            if v is None: raise AppError("VERSION_NOT_FOUND")
            wf = json.loads(v.data or "{}")
        version = n if n is not None else self._version_of(wid, wf)
        res = row.owner if row is not None and row.owner else uid  # a saved workflow uses its owner's resources (DEC-0023)
        wf, invalid = self._expand(res, wid, wf)
        if (steps is not None or until) and (wf.get("source") or {}).get("kind") == "langgraph_import":
            raise AppError("RUN_REQUEST_INVALID")  # imported graphs stay full-run only (TASK-0036)
        return RunPlan(wid, wf, inp, self.credentials.resolver(res) if self.credentials else None, version=version, invalid=invalid,
                       ports=self.ports(res, uid), steps=steps, until=until)

    def _plan_chat(self, uid: str, req: dict, steps, until) -> RunPlan:
        """A chat message or a visitor's answer from the chat (TASK-0084): the run gets the history as input and
        source "chat"; ChatRunService.on_settled writes the answer turn."""
        web = self.chat().web if self.chat else None
        sid = req["chat_session_id"]
        if web is None or not isinstance(sid, str): raise AppError("CHAT_NOT_ENABLED")
        if req.get("resume_run_id"):
            if req.get("attachment_ids"): raise AppError("RUN_REQUEST_INVALID")  # a Human node's answer is text only
            web.check_answer(uid, sid, str(req["resume_run_id"]))
            return self.plan_resume(uid, req["resume_run_id"], req.get("response"), steps=steps, until=until, node=_request_node(req))
        prep = web.input_for(uid, sid, req.get("message"), req.get("attachment_ids"))
        plan = self.plan(uid, {"workflow_id": prep["workflow_id"], "input": prep["input"]})
        plan.run_id, plan.source = uuid.uuid4().hex[:10], "chat"
        web.record(uid, sid, prep["text"], plan.run_id, prep["attachment_ids"])
        return plan

    def _workflow(self, wid: str, uid: str, action: str = P.VIEW):
        if self.access is not None: return self.access.workflow(wid, uid, action)
        row = self.workflows.get_owned(wid, uid)
        if row is None: raise AppError("WORKFLOW_NOT_FOUND")
        return row

    def resources_of(self, wid: Optional[str], uid: str) -> str:
        """Whose credentials, knowledge bases and MCP servers a run uses: the saved workflow's owner, else the caller."""
        row = self.workflows.get(wid) if wid and wid != "adhoc" else None
        return row.owner if row is not None and row.owner else uid

    def ports(self, uid: str, actor: Optional[str] = None) -> Ports:
        """Services nodes may call during a run, bound to the resource owner `uid`. Org-wide MCP servers follow the admin
        policy for the person running (`actor`, TASK-0029)."""
        org = self.policy.org_allowed(actor or uid) if self.policy is not None else True
        web = self.chat().web if self.chat else None
        return Ports(retrieve=self.knowledge.retriever(uid) if self.knowledge else None, mcp_call=self.mcp.caller(uid, org) if self.mcp else None,
                     email_quota=self.email_quota(uid), code_audit=self.code_audit(actor or uid),
                     attachment=web.file_loader(uid) if web is not None else None)

    # ---- child runs of workflow tools (TASK-0134, DEC-0066) ----
    def top_run(self, r: Run) -> Run:
        """The run at the top of a chain of workflow tool calls (the run itself when it has no parent)."""
        for _ in range(subgraphs.MAX_DEPTH + 2):
            p = self.runs.get(r.parent_run_id) if r.parent_run_id else None
            if p is None: return r
            r = p
        return r

    def run_resources(self, r: Run, uid: str) -> str:
        """Whose resources a stored run uses: a child run uses its top parent's, as an inlined subgraph would (DEC-0023)."""
        top = self.top_run(r) if r.parent_run_id else r
        return self.resources_of(top.workflow_id, top.owner or uid if top is not r else uid)

    def under_test(self, r: Run) -> bool:
        """A child run under a workflow test run (TASK-0137): it keeps the test rules, and a question for a person inside it
        is not sent anywhere; the test cancels it and the parent's tool call fails."""
        return bool(r.parent_run_id) and self.top_run(r).source == "test"

    def run_ports(self, r: Run, uid: str) -> Ports:
        """Ports of a stored run's next segment. A child of a workflow test run keeps the test rules (DEC-0044) without
        becoming a test run itself."""
        ports = self.ports(self.run_resources(r, uid), uid)
        top = self.top_run(r) if r.parent_run_id else r
        test = self.tests().test_job(top.id) if top.source == "test" and self.tests else None
        if test is not None: ports.test, ports.mock_models = True, bool(test.get("mock"))
        return ports

    def _child_starter(self, rid: str, plan: RunPlan, uid: str):
        """ports.start_child of one run: insert the child (once per call key) and queue it."""
        def start(key: str, wf: dict, version: Optional[int], inp: dict, meta: dict) -> str:
            if self.jobs is None: raise RuntimeError("workflow tools need the job queue")
            found = self.runs.child_of(rid, key)
            if found is not None: return found.id
            depth, r = 1, self.runs.get(rid)
            while r is not None and r.parent_run_id: depth += 1; r = self.runs.get(r.parent_run_id)
            if depth > subgraphs.MAX_DEPTH: raise AppError("WORKFLOW_TOOL_TOO_DEEP", max=subgraphs.MAX_DEPTH)
            child = self.runs.add_child(Run(id=uuid.uuid4().hex[:10], workflow_id=meta.get("workflow_id") or "adhoc", input=_dumps(inp), events="[]",
                                            status="queued", started=time.time(), owner=uid or None, source="tool", workflow_version=version,
                                            parent_run_id=rid, parent_step=key, checkpoint=_dumps({"kind": "child", "workflow": wf})))
            if child.status == "queued":
                self.jobs().enqueue({"run_id": child.id, "workflow_id": child.workflow_id, "owner": uid, "input": inp, "source": "tool"})
            return child.id
        return start

    def plan_child(self, r: Run) -> RunPlan:
        """The first segment of a child run: the snapshot its parent's plan took (DEC-0066 decision 2)."""
        cp = json.loads(r.checkpoint or "{}"); uid = r.owner or ""
        res = self.run_resources(r, uid)
        return RunPlan(r.workflow_id, cp.get("workflow") or {}, json.loads(r.input or "{}"), self.credentials.resolver(res) if self.credentials else None,
                       run_id=r.id, source="tool", version=r.workflow_version, ports=self.run_ports(r, uid))

    def child_value(self, r: Run) -> dict:
        """What the parent's tool step gets from a finished child: its status, final state or error, and usage."""
        err = next((e for e in reversed(json.loads(r.events or "[]")) if isinstance(e, dict) and e.get("type") == "error"), None)
        error = ((err.get("error") or {}).get("message") or "; ".join(err.get("errors") or [])) if err else None
        usage = None
        if (r.tokens_in or 0) + (r.tokens_out or 0):
            usage = {"provider": "workflow", "model": r.workflow_id, "tokens_in": r.tokens_in or 0, "tokens_out": r.tokens_out or 0,
                     "tokens": (r.tokens_in or 0) + (r.tokens_out or 0), "cost_usd": r.cost_usd, "estimated": False}
        return {"child_run_id": r.id, "status": r.status, "output": json.loads(r.final_state or "null"),
                **({"error": error} if error else {}), **({"usage": usage} if usage else {})}

    def absorb_wave(self, rid: str, node: Optional[str] = None, value=None, child: Optional[dict] = None) -> tuple[str, bool]:
        """Store one settled wait of a wave. The string is 'plain' when this run is not waiting on a wave, 'stay' when
        other waits remain, 'go' when this was the last and the checkpoint is ready for the one resume (TASK-0158).
        The bool is whether this call stored the settle. A lost compare-and-set stores nothing, so the caller must not
        close the wait first."""
        def apply(cp: dict) -> tuple[str, bool]:
            waits = cp.get("waits")
            if not isinstance(waits, list): return "plain", False
            if not waits: return ("go" if cp.get("wave_ready") else "plain"), False
            if child is not None:
                cid = child.get("child_run_id")
                hit = next((w for w in waits if w.get("kind") == "child" and w.get("run_id") == cid), None)
                if hit is None: return ("go" if cp.get("wave_ready") else "stay"), False
                cp.setdefault("children", {})[hit["node"]] = child
            else:
                hit = next((w for w in waits if w.get("kind") == "approval" and w.get("node") == node), None)
                if hit is None: return ("go" if cp.get("wave_ready") else "stay"), False
                cp.setdefault("answers", {})[hit["node"]] = value
            cp["waits"] = [w for w in waits if w is not hit]
            if cp["waits"]:
                cp["_next_wait"] = _follow_up_wait(cp)  # the panel's next question; update_waiting appends it and drops the key
                return "stay", True
            cp["wave_ready"] = True
            return "go", True
        got = self.runs.update_waiting(rid, apply)
        return got if isinstance(got, tuple) else ("plain", False)

    def _wave_plan(self, r: Run, steps: Optional[int], until: Optional[str]) -> RunPlan:
        """The one resume of a settled wave: every stored answer and child result, re-entering every slot."""
        cp = json.loads(r.checkpoint or "{}"); uid = r.owner or ""
        res = self.run_resources(r, uid)
        resume = {k: cp[k] for k in RESUME_KEYS if k in cp}
        resume["answers"] = dict(cp.get("answers") or {})
        resume["children"] = dict(cp.get("children") or {})
        return RunPlan(r.workflow_id if r.workflow_id != "adhoc" else None, cp["workflow"], json.loads(r.input or "{}"),
                       self.credentials.resolver(res) if self.credentials else None,
                       run_id=r.id, previous=r, resume=resume, source=r.source or "ui", version=r.workflow_version,
                       trace_parent=cp.get("trace"), ports=self.run_ports(r, uid), steps=steps, until=until)

    def resume_parent(self, rid: str) -> bool:
        """Queue the resume of the run waiting for child `rid`, once the child has ended. Called when the child settles and
        when the parent records its wait (the child may have ended first). A wave resumes once, after every child and
        approval of that superstep has settled. A second resume is dropped by the claim."""
        r = self.runs.get(rid)
        if r is None or not r.parent_run_id or r.status in ("queued", "running", "waiting", "paused") or self.jobs is None: return False
        p = self.runs.get(r.parent_run_id)
        if p is None or p.status != "waiting": return False
        cp = json.loads(p.checkpoint or "{}")
        if isinstance(cp.get("waits"), list):
            if self.absorb_wave(p.id, child=self.child_value(r))[0] != "go": return False
            enqueue_resume(self.runs, self.jobs().enqueue, {"kind": "resume", "run_id": p.id, "owner": p.owner, "wave": True})
            return True
        if ((cp.get("wait") or {}).get("run_id")) != rid: return False
        enqueue_resume(self.runs, self.jobs().enqueue, {"kind": "resume", "run_id": p.id, "owner": p.owner, "child": self.child_value(r)})
        return True

    def cancel_children(self, rid: str) -> None:
        """A parent that ends without its child's result takes its unfinished children (and theirs) with it."""
        for ch in self.runs.children(rid):
            try:
                if ch.status == "queued": self.runs.set_status(ch.id, "cancelled"); self.cancel_children(ch.id)
                elif ch.status in ("waiting", "paused"):
                    self._close_waiting(ch, {"type": "run_cancelled", "ts": time.time(), "reason": "parent"}, "cancelled", ch.owner or "")
                elif ch.status == "running": self.bus.request_cancel(ch.id)
            except Exception: log.exception("cancelling child run %s failed", ch.id)

    @staticmethod
    def apply_test(plan: RunPlan, test: Optional[dict]) -> RunPlan:
        """A workflow test run (TASK-0067, DEC-0044): Send email nodes do a dry run; with `mock`, every LLM and Decision node
        uses the offline mock. The queue job carries `test`, so a resumed or recovered segment keeps it."""
        if test is None: return plan
        plan.source = "test"; plan.ports = plan.ports or Ports()
        plan.ports.test, plan.ports.mock_models = True, bool(test.get("mock"))
        return plan

    def code_audit(self, uid: str) -> Optional[Callable[[], None]]:
        """Audit entry for the first Code call that runs on the host without isolation (TASK-0056)."""
        if self.audit is None: return None
        return lambda: self.audit.record(uid or None, "system.code_runtime_subprocess", "system", None, "Code nodes", runtime="subprocess")

    def email_quota(self, uid: str) -> Optional[Callable[[int], None]]:
        """Send email nodes of `uid`'s workflows reach at most STUDIO_EMAIL_NODE_HOURLY_LIMIT recipients an hour."""
        if self.quota is None: return None
        def take(n: int) -> None:
            limit = config.email_node_hourly_limit()
            count, retry = self.quota.add(f"email:{uid}", n, 3600)
            if count > limit: raise AppError("EMAIL_RATE_LIMITED", limit=limit, retry=retry)
        return take

    def _expand(self, uid: str, wid: Optional[str], wf: dict) -> tuple[dict, Optional[list]]:
        """Inline subgraph nodes (TASK-0011) with the workflows this user may read, copy in the children of workflow tools
        (TASK-0133, DEC-0066), then add Agent nodes' steps (TASK-0116). The expanded graph is what runs and what checkpoints
        store, so a resumed or recovered run continues on the same graph even if a child changed."""
        if wf.get("source"): return wf, None
        load = self.workflow_loader(uid)
        try: wf = agents.snapshot(subgraphs.expand(wf, load, wid), load, wid, self._version_of)
        except ValidationError as e: return wf, e.errors
        return agents.expand(wf), None

    def workflow_loader(self, uid: str):
        def load(ref: str) -> Optional[dict]:
            if self.access is not None: row = self.workflows.get(ref) if self.access.may(ref, uid) else None
            else: row = self.workflows.get_owned(ref, uid)
            return json.loads(row.data or "{}") if row else None
        return load

    def _version_of(self, wid, wf: dict) -> Optional[int]:
        """The latest stored version number if `wf` matches it in content, else None (unsaved edits)."""
        if not wid or self.versions is None: return None
        v = self.versions.latest(wid)
        return v.version if v and same_content(json.loads(v.data or "{}"), wf) else None

    # ---- time travel: checkpoints of a run, and a fork from one ----
    def _readable_run(self, rid, uid: str) -> Run:
        """A run of a saved workflow its owner (or the workflow's owner / an admin) may inspect, as in the run history."""
        r = self.runs.get(rid) if isinstance(rid, str) else None
        if r is None or not r.workflow_id or r.workflow_id == "adhoc": raise AppError("RUN_NOT_FOUND")
        if r.owner != uid:
            row = self.workflows.get(r.workflow_id)
            if row is None or self.access is None or self.access.access_of(row, uid) != "owner": raise AppError("RUN_NOT_FOUND")
        return r

    def checkpoints(self, rid: str, uid: str) -> dict:
        r = self._readable_run(rid, uid)
        done = r.status not in ("running", "queued")
        return {"run_id": r.id, "workflow_id": r.workflow_id, "version": r.workflow_version, "status": r.status,
                "checkpoints": time_travel.checkpoints(json.loads(r.events or "[]"), json.loads(r.final_state or "null") if done else None)}

    def _plan_fork(self, uid: str, fork, steps: Optional[int], until: Optional[str]) -> RunPlan:
        """A new run of the same workflow that starts at a checkpoint of `fork.run_id`, with its state or an edited one.
        It runs the version the original run ran when that is stored, else the saved workflow."""
        if not isinstance(fork, dict): raise AppError("RUN_REQUEST_INVALID")
        r = self._readable_run(fork.get("run_id"), uid)
        cps = time_travel.checkpoints(json.loads(r.events or "[]")); i = fork.get("checkpoint")
        if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(cps) or not cps[i]["forkable"]: raise AppError("CHECKPOINT_NOT_FOUND")
        cp = cps[i]; state = fork.get("state", cp["state"])
        if not isinstance(state, dict) or state.get("_truncated"): raise AppError("RUN_INPUT_INVALID")
        if size(state) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE", max_kb=config.input_max() // 1024)
        req = {"workflow_id": r.workflow_id, "input": {}}
        try: plan = self.plan(uid, {**req, "version": r.workflow_version} if r.workflow_version else req)
        except AppError as e:
            if e.code != "VERSION_NOT_FOUND": raise
            plan = self.plan(uid, req)  # the version is gone (or not readable): the saved workflow
        if plan.imported: raise AppError("RUN_FORK_UNSUPPORTED")
        ids = {n.get("id") for n in plan.workflow.get("nodes") or []}
        if not set(cp["nodes"]) <= ids: raise AppError("CHECKPOINT_NOT_FOUND")
        plan.input, plan.steps, plan.until = state, steps, until
        plan.resume = {"node": cp["nodes"][0], "nodes": cp["nodes"], "state": state, "counts": cp["counts"]}
        plan.forked = {"run_id": r.id, "checkpoint": i, "nodes": cp["nodes"], "edited": state != cp["state"]}
        return plan

    # ---- human-in-the-loop (TASK-0006) ----
    def waiting_run(self, rid: str, uid: str) -> Run:
        r = self.runs.get(rid)
        if r is None or r.owner != uid: raise AppError("RUN_NOT_FOUND")  # owner only (DEC-0013)
        if r.status != "waiting" or not r.checkpoint: raise AppError("RUN_NOT_WAITING")
        if self.expire_if_stale(r): raise AppError("RUN_EXPIRED")
        return r

    def expire_if_stale(self, r: Run) -> bool:
        """Expire a waiting run past STUDIO_WAIT_TTL now (lazily on access). True when it did."""
        if not self._is_stale(r): return False
        self._expire(r); return True

    @staticmethod
    def _is_stale(r: Run, now: float | None = None) -> bool:
        ttl = config.wait_ttl()
        return bool(ttl) and (r.ended or r.started or 0) < (now or time.time()) - ttl

    def _close_waiting(self, r: Run, ev: dict, status: str, uid: str) -> None:
        """End a waiting run without executing it (cancel / expiry): one more trace segment, no node spans."""
        cp = json.loads(r.checkpoint or "{}")
        self.record(r.id, r.workflow_id, json.loads(r.input or "{}"), json.loads(r.events or "[]") + [ev], None, status, r.started, uid,
                    source=r.source or "ui", version=r.workflow_version, trace_parent=cp.get("trace"), trace_events=[] if cp.get("trace") else None)
        if (cp.get("wait") or {}).get("kind") == "child" or any(
                isinstance(w, dict) and w.get("kind") == "child" for w in cp.get("waits") or []): self.cancel_children(r.id)
        if r.parent_run_id: self.resume_parent(r.id)  # a child that ended this way still answers its parent

    def _expire(self, r: Run) -> None:
        self._close_waiting(r, {"type": "run_expired", "ts": time.time(), "ttl_s": config.wait_ttl()}, "expired", r.owner or "")

    def expire_waiting(self) -> int:
        """Expire runs that waited longer than STUDIO_WAIT_TTL (periodic sweep + lazily on access). Returns the count."""
        ttl = config.wait_ttl()
        if not ttl: return 0
        stale = self.runs.list_waiting_before(time.time() - ttl)
        for r in stale: self._expire(r)
        return len(stale)

    def plan_resume(self, uid: str, rid: str, response, via_channel: bool = False, steps: Optional[int] = None, until: Optional[str] = None,
                    child: Optional[dict] = None, node: Optional[str] = None, wave: bool = False) -> RunPlan:
        """child: the finished child run a run waits for (TASK-0134), from the worker only. A run waiting for a child
        cannot be answered by a person, and a child's result cannot answer a person's question.
        wave: the checkpoint already holds every answer of a settled wave (TASK-0158). node: which approval this answer is for."""
        row = self.runs.get(rid)
        if row is not None and row.status == "paused" and not via_channel:
            if row.owner != uid: raise AppError("RUN_NOT_FOUND")  # owner only, same as a human resume
            return self._plan_paused(row, uid, steps, until)
        if wave:
            r = self.waiting_run(rid, uid)
            if not json.loads(r.checkpoint or "{}").get("wave_ready"): raise AppError("RUN_NOT_WAITING")
            return self._wave_plan(r, steps, until)
        if child is None and response is not None: response = human_response(response)
        r = self.waiting_run(rid, uid); cp = json.loads(r.checkpoint)
        if isinstance(cp.get("waits"), list):
            if child is not None: outcome, wrote = self.absorb_wave(rid, child=child)
            else:
                node = _approval_node(cp, node)  # never guess among several: the panel names the question it is showing
                if node is None or response is None: raise AppError("RUN_NOT_WAITING")
                outcome, wrote = self.absorb_wave(rid, node=node, value=response)
                if wrote and self.approvals is not None and not via_channel:
                    self.approvals.answered_slot(rid, node)  # stored first: a lost claim does not drop the answer
            if outcome == "stay":
                fresh = self.runs.get(rid)
                evs = json.loads(fresh.events or "[]") if fresh is not None else []
                pending = evs[-1] if evs and isinstance(evs[-1], dict) and evs[-1].get("type") == "run_waiting" else None
                return RunPlan(r.workflow_id, cp.get("workflow") or {}, {}, run_id=rid, pending_wave=True, pending_event=pending)
            if outcome == "go": return self._wave_plan(self.runs.get(rid), steps, until)
            raise AppError("RUN_NOT_WAITING")  # the wave changed under this answer; do not close the other slots
        if child is None: response = human_response(response)
        r = self.waiting_run(rid, uid); cp = json.loads(r.checkpoint)
        wait = cp.get("wait") or {}
        if (child is None) == (wait.get("kind") == "child") or (child is not None and wait.get("run_id") != child.get("child_run_id")):
            raise AppError("RUN_NOT_WAITING")
        if child is not None: response = child
        elif self.approvals is not None and not via_channel:  # answered in the studio: the channel buttons stop working (TASK-0022)
            if self.approvals.decided_elsewhere(rid) or not self.approvals.claim(rid): raise AppError("RUN_NOT_WAITING")  # first answer wins (DEC-0043)
            self.approvals.close_run(rid, "answered")
        res = self.run_resources(r, uid)
        return RunPlan(r.workflow_id if r.workflow_id != "adhoc" else None, cp["workflow"], json.loads(r.input or "{}"),
                       self.credentials.resolver(res) if self.credentials else None,
                       run_id=rid, previous=r, resume={**{k: cp[k] for k in RESUME_KEYS if k in cp}, "value": response}, source=r.source or "ui",
                       version=r.workflow_version, trace_parent=cp.get("trace"), ports=self.run_ports(r, uid))

    def _plan_paused(self, r: Run, uid: str, steps: Optional[int], until: Optional[str] = None) -> RunPlan:
        """Continue a one-step pause (TASK-0036). No human response, and no approval notification."""
        if not r.checkpoint: raise AppError("RUN_NOT_WAITING")
        cp = json.loads(r.checkpoint)
        resume = {k: cp[k] for k in RESUME_KEYS if k in cp}
        if not (resume.get("node") or resume.get("nodes")): raise AppError("RUN_NOT_WAITING")
        res = self.run_resources(r, uid)
        return RunPlan(r.workflow_id if r.workflow_id != "adhoc" else None, cp["workflow"], json.loads(r.input or "{}"),
                       self.credentials.resolver(res) if self.credentials else None,
                       run_id=r.id, previous=r, resume=resume, source=r.source or "ui", steps=steps, until=until,
                       version=r.workflow_version, trace_parent=cp.get("trace"), ports=self.run_ports(r, uid))

    def plan_recover(self, r: Run, fence: Optional[int] = None, attempt: int = 2) -> RunPlan:
        """A recovered queue job (its worker died or lost its lease mid-run). With a progress checkpoint it continues
        from there (same checkpoint shape as HITL; parallel branches and imported graphs included, TASK-0021);
        without one it starts over. Either way the lost segment's root span is exported first (DEC-0018)."""
        cp = json.loads(r.checkpoint or "null") or {}
        snapshot = cp.get("workflow") if r.parent_run_id else None  # a child restarts on its parent's snapshot (TASK-0134)
        if cp.get("kind") != "progress": cp = {}
        lost = cp.get("trace")
        if lost:
            try: self.telemetry.close_lost(lost, cp.get("ts") or time.time())
            except Exception: log.warning("exporting the lost segment of run %s failed", r.id)
        common = dict(run_id=r.id, source=r.source or "api", trace_parent=lost, checkpointing=True, fence=fence, attempt=attempt)
        if not (cp.get("node") or cp.get("nodes")):  # nothing finished yet: restart from the beginning
            if snapshot is not None:
                plan = self.plan_child(r)
                for k, v in common.items(): setattr(plan, k, v)
                return plan
            pin = {"version": r.workflow_version} if r.source == "test" and r.workflow_version else {}  # a test run keeps its version
            plan = self.plan(r.owner or "", {"workflow_id": r.workflow_id, "input": json.loads(r.input or "{}"), **pin})
            for k, v in common.items(): setattr(plan, k, v)
            return plan
        return RunPlan(r.workflow_id if r.workflow_id != "adhoc" else None, cp["workflow"], json.loads(r.input or "{}"),
                       self.credentials.resolver(self.run_resources(r, r.owner or "")) if self.credentials else None, previous=r,
                       resume={k: cp[k] for k in RESUME_KEYS if k in cp}, version=r.workflow_version, recovered=True,
                       ports=self.run_ports(r, r.owner or ""), **common)

    def recovery_job(self, r: Run) -> dict:
        """The queue job that continues an unfinished run after a restart (RunWorker.recover_unfinished)."""
        test = self.tests().test_job(r.id) if r.source == "test" and self.tests else None
        return {"run_id": r.id, "workflow_id": r.workflow_id, "owner": r.owner, "input": json.loads(r.input or "{}"), "source": r.source,
                "callback_url": r.callback_url, "token_id": r.callback_token_id, "recovered": True, "attempt": (r.lease_gen or 0) + 1,
                **({"test": test} if test is not None else {}), **({"version": r.workflow_version} if r.source == "test" and r.workflow_version else {})}

    @staticmethod
    def interruptions(r: Run) -> int:
        """How many times an unfinished run has been cut off by a restart or a lost worker, this time included. Every claim
        bumps `lease_gen`: the first start, each recovery and each resume after a Human node or an Agent tool approval;
        the resumes (one `run_resumed` event each) are not interruptions."""
        resumes = sum(1 for e in json.loads(r.events or "[]") if isinstance(e, dict) and e.get("type") == "run_resumed")
        return max(0, (r.lease_gen or 0) - resumes)

    def interrupted(self, r: Run, attempts: int) -> None:
        """End an unfinished run that recovery gave up on: `error` RUN_INTERRUPTED, its events so far kept."""
        err = AppError("RUN_INTERRUPTED", attempts=attempts).to_dict()
        self.record(r.id, r.workflow_id, json.loads(r.input or "{}"), json.loads(r.events or "[]") + [error_event(err, ts=time.time())], None, "error",
                    r.started, r.owner or "", source=r.source or "api", version=r.workflow_version)

    def pending(self, uid: str) -> list[dict]:
        """Runs of this user waiting for a human response (newest first)."""
        out = []; self.expire_waiting()
        for r in self.runs.list_waiting(uid):
            ev = next((e for e in reversed(json.loads(r.events or "[]")) if e.get("type") == "run_waiting"), {})
            if ev.get("wait"): continue  # waiting for a child run, not for a person (TASK-0134)
            w = self.workflows.get(r.workflow_id) if r.workflow_id and r.workflow_id != "adhoc" else None
            out.append({"id": r.id, "workflow_id": r.workflow_id, "workflow_name": w.name if w else None, "node": ev.get("node"),
                        "label": ev.get("label"), "prompt": ev.get("prompt"), "started": r.started, "waiting_since": r.ended})
        return out

    def cancel_waiting(self, rid: str, uid: str) -> None:
        r = self.waiting_run(rid, uid)
        self._close_waiting(r, {"type": "run_cancelled", "ts": time.time(), "reason": "api"}, "cancelled", uid)

    # ---- history ----
    def history(self, wid: str, uid: str, tests: bool = False) -> list[dict]:
        """tests: the workflow's test runs instead of its other runs (TASK-0067)."""
        row = self._workflow(wid, uid)
        everyone = self.access is None or self.access.access_of(row, uid) == "owner"  # owner and admins see every run
        rows = [r for r in self.runs.list_for_workflow(wid, tests=tests) if everyone or r.owner == uid]
        chat = self.chat().runs_info([r.id for r in rows if r.source == "chat"]) if self.chat else {}  # TASK-0075: who sent the message
        return [self.row(r, uid, chat) for r in rows]

    def run_detail(self, rid: str, uid: str) -> dict:
        """One run as the history lists it (TASK-0136: a workflow tool's child steps in its parent's trace)."""
        return self.row(self._readable_run(rid, uid), uid)

    def row(self, r: Run, uid: str, chat: Optional[dict] = None) -> dict:
        return {"id": r.id, "workflow_id": r.workflow_id, "input": json.loads(r.input or "null"), "events": json.loads(r.events or "[]"),
                 "final_state": json.loads(r.final_state or "null"), "status": r.status, "started": r.started, "ended": r.ended, "source": r.source or "ui", "version": r.workflow_version,
                 "metrics": None if r.duration_ms is None else {"duration_ms": r.duration_ms, "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
                                                                "tokens": (r.tokens_in or 0) + (r.tokens_out or 0), "cost_usd": r.cost_usd, "error_count": r.error_count},
                 "trace_id": r.trace_id, "trace_url": trace_url(r.trace_id, r.trace_root), "code_runtime": r.code_runtime, "chat": (chat or {}).get(r.id),
                 **self.links(r, uid)}

    def links(self, r: Run, uid: str) -> dict:
        """A workflow tool's child run names its parent; a parent waiting for a child names the child (TASK-0135). Names of
        workflows the caller cannot open are left out."""
        def ref(x: Optional[Run]) -> Optional[dict]:
            if x is None: return None
            seen = x.workflow_id and x.workflow_id != "adhoc" and (self.access is None or self.access.may(x.workflow_id, uid))
            w = self.workflows.get(x.workflow_id) if seen else None
            return {"run_id": x.id, "workflow_id": x.workflow_id, "workflow_name": w.name if w else None, "status": x.status}
        out = {}
        if r.parent_run_id: out["parent"] = ref(self.runs.get(r.parent_run_id))
        if r.status == "waiting" and r.checkpoint and (wait := json.loads(r.checkpoint).get("wait")): out["waiting_for"] = ref(self.runs.get(wait.get("run_id")))
        return out

    def record(self, rid, wid, inp, events, final, status, t0, uid: str = "", checkpoint: dict | None = None, source: str = "ui",
               version: Optional[int] = None, span=None, trace_parent: Optional[dict] = None, trace_events: Optional[list] = None,
               fence: Optional[int] = None) -> dict:
        """Persist the run with its summary metrics and close its trace segment. Returns {metrics, trace_id, trace_url}.
        span: the live root span (node spans were already exported). Without one, the trace is built post-hoc from
        `trace_events` (default: all events) under `trace_parent` (the previous segment of a paused run).
        A waiting run keeps its checkpoint, which remembers the trace so the resumed segment joins it.
        fence: lease generation of a queue job; raises StaleLease (nothing written) when another worker owns the run."""
        if fence is not None and self.runs.lease_gen(rid) != fence: raise StaleLease(rid)  # before any side effect (spans, notifications)
        t1 = time.time(); metrics = summarize(events, t0, t1)  # from the full events, before capping
        trace_id = trace_root = None; run_meta = {"id": rid, "workflow_id": wid, "owner": uid, "status": status, "started": t0, "ended": t1, "source": source}
        try:
            if span is not None:
                if checkpoint is not None: checkpoint = {**checkpoint, "trace": span.ref}
                trace_id = self.telemetry.end_run(span, {**run_meta, "started": span.run["started"]}, metrics)
                if trace_id and not span.parent: trace_root = span.ids["span_id"]  # the first segment: the trace's root
            elif status not in ("waiting", "paused"):
                trace_id = self.telemetry.record_run(run_meta, events if trace_events is None else trace_events, metrics, trace_parent)
        except Exception: trace_id = None  # tracing must never fail a run
        if trace_id is None and trace_parent: trace_id = trace_parent.get("trace_id")
        root = {"trace_root": trace_root} if trace_root else {}  # later segments keep the first one's
        test = source == "test"  # a workflow test answers its own Human nodes and sends nothing (DEC-0044)
        wave_waits = (checkpoint or {}).get("waits") if isinstance((checkpoint or {}).get("waits"), list) else []
        if status == "waiting" and checkpoint and checkpoint.get("wait"): test = True  # waiting for a child run: nobody to ask (TASK-0134)
        elif status == "waiting" and wave_waits and all(w.get("kind") == "child" for w in wave_waits): test = True
        if source == "tool" and not test and (row := self.runs.get(rid)) is not None and self.under_test(row): test = True  # TASK-0137
        if self.notifier is not None and uid and status in ("waiting", "expired") and not test:
            ev = next((e for e in reversed(events) if e.get("type") == "run_waiting"), None)
            try:  # a step AI review may answer is announced by the review instead (TASK-0187)
                reviewed = status == "waiting" and self.approvals is not None and self.approvals.answers_itself(wid, (checkpoint or {}).get("workflow") or {}, ev)
                if not reviewed: self.notifier.run_event("run_waiting" if status == "waiting" else "run_expired", uid, rid, wid, ev)
            except Exception: log.exception("notification for run %s failed", rid)  # never fails a run
        state, all_events = (final if isinstance(final, dict) else None), events
        def approvals() -> None:  # after the run row is stored, so an answer AI review gives at once finds it waiting (TASK-0187)
            if self.approvals is not None and uid and not test:
                try:
                    if status == "waiting":
                        asked = [{"type": "run_waiting", "node": w.get("node"), "prompt": w.get("prompt"), "label": w.get("label"),
                                  "tool": w.get("tool"), "arguments": w.get("arguments")}
                                 for w in wave_waits if w.get("kind") == "approval"]
                        if not asked:
                            ev = next((e for e in reversed(all_events) if e.get("type") == "run_waiting"), None)
                            if ev and not ev.get("wait"): asked = [ev]
                        wf = (checkpoint or {}).get("workflow") or {}
                        for ev in asked: self.approvals.on_waiting(rid, uid, wid, wf, ev, state)
                    elif status in ("cancelled", "expired", "error", "timeout"): self.approvals.close_run(rid, status)
                except Exception: log.exception("approval request for run %s failed", rid)  # never fails a run
        events = cap_run([cap_event(e) for e in events])
        final = cap_event({"state": final})["state"] if final is not None else None
        self.runs.add(Run(id=rid, workflow_id=wid or "adhoc", input=_dumps(inp), events=_dumps(events), code_runtime=code_runtime_of(events),
                          final_state=_dumps(final), status=status, started=t0, ended=t1, trace_id=trace_id, owner=uid or None, source=source, workflow_version=version,
                          checkpoint=_dumps(checkpoint) if checkpoint else None, resume_job=None, **root, **metrics),
                      **({"fence": fence} if fence is not None else {}))  # resume_job: a kept answer is used up (TASK-0127)
        approvals()
        if self.ledger is not None and status not in ("waiting", "paused"):
            try: self.ledger.purge(rid)  # finished: the ledger only matters while the run can still be recovered
            except Exception: log.warning("purging the node ledger of run %s failed", rid)
        return {"metrics": {**metrics, "tokens": metrics["tokens_in"] + metrics["tokens_out"]}, "trace_id": trace_id, "trace_url": trace_url(trace_id, trace_root)}

    async def _save_progress(self, rid, events, ev, plan, span) -> None:
        """Persist events so far + where to continue from if this worker dies (TASK-0020/0021): the next node(s),
        state and iteration counts (or the imported graph's serialized LangGraph checkpoint), plus the trace segment.
        Raises StaleLease when another worker claimed the run (this one must stop)."""
        cp = {"kind": "progress", **{k: ev[k] for k in RESUME_KEYS if k in ev}, "workflow": plan.workflow, "ts": time.time(),
              **({"trace": span.ref} if span else {})}
        try: await asyncio.to_thread(self.runs.save_progress, rid, _dumps(cap_run([cap_event(e) for e in events])), _dumps(cp), plan.fence)
        except StaleLease: raise
        except Exception: log.warning("saving progress of run %s failed", rid)  # recovery falls back to a restart

    # ---- execution ----
    async def execute(self, plan: RunPlan, send: Callable[[dict], Awaitable[bool]],
                      listen: Callable[[], Awaitable[str]], uid: str = "") -> str:
        """Stream events through `send` (returns False once the client is gone). `listen` resolves to
        "cancelled" or "disconnected"; a cancel can also arrive through the RunBus (reason "api").
        Returns the final status: ok | error | cancelled | timeout."""
        if plan.pending_wave:  # one slot of a wave was answered; the other waits are still open
            if plan.pending_event: await send(cap_event(plan.pending_event))  # the next question, not the one just answered
            if plan.pending_event and self.chat is not None and plan.run_id:
                await _write_in_thread(self._note_chat, plan.run_id)  # the published page then shows that question
            await send({"type": "run_summary", "run_id": plan.run_id, "status": "waiting", "ts": time.time()})
            return "waiting"
        rid = plan.run_id or uuid.uuid4().hex[:10]; await self.bus.astart(rid, uid)  # registered so REST/other workers can cancel it
        status = None
        try:
            status = await self._execute(rid, plan, send, listen, uid)
            if status != "fenced": await self.settled(rid, plan.source)
            return status
        finally:
            if status != "fenced": await _write_in_thread(self.bus.finish, rid)  # a fenced worker leaves the new owner's entry alone

    async def settled(self, rid: str, source: Optional[str] = None) -> None:
        """Every run segment ends here (first run, studio/Slack/Telegram resume, recovery): an API run's callback_url
        gets the result or the next pause, once (DeliveryService.for_run is idempotent). A test run (`source`) goes to its
        suite instead, which records it or answers its Human node (TASK-0067). A chat run answers its thread (TASK-0075).
        The work is one thread job submitted at once and never cancelled (_write_in_thread): the handler is often cancelled
        right after the run ends (the client closes the socket on run_summary), and a cancelled plain to_thread would drop
        the queued job, so the chat reply or callback would silently never happen (TASK-0083)."""
        await _write_in_thread(self._settle, rid, source)

    def _note_chat(self, rid: str) -> None:
        """A chat run stayed waiting after one slot of a wave. Record the next question as its own turn."""
        try: self.chat().on_settled(rid)
        except Exception: log.exception("noting the next question of chat run %s failed", rid)

    def _settle(self, rid: str, source: Optional[str]) -> None:
        if source == "tool":  # a workflow tool's child run: its parent goes on (TASK-0134)
            try:
                r = self.runs.get(rid)
                if r is not None and r.status == "waiting" and self.under_test(r):  # nobody answers a person's question in a test run
                    return self._close_waiting(r, {"type": "run_cancelled", "ts": time.time(), "reason": "test"}, "cancelled", r.owner or "")
                self.resume_parent(rid)
            except Exception: log.exception("resuming the parent of run %s failed", rid)
            return
        if source == "test":
            if self.tests:
                try: self.tests().on_settled(rid)
                except Exception: log.exception("recording test run %s failed", rid)
            return
        if source == "chat" and self.chat:
            try: self.chat().on_settled(rid)
            except Exception: log.exception("answering chat run %s failed", rid)
        if not self.deliveries: return
        try: self.deliveries().for_run(self.runs.get(rid))
        except Exception: log.exception("queueing the callback of run %s failed", rid)

    async def _execute(self, rid, plan, send, listen, uid) -> str:
        t0 = time.time(); events: list = []; final = None; status = "ok"; connected = True; bus = self.bus; checkpoint = None
        prev = plan.previous; started = prev.started if prev else t0
        try: span = self.telemetry.start_run({"id": rid, "workflow_id": plan.workflow_id, "owner": uid, "started": t0,
                                              "segment": "recovered" if plan.recovered or plan.fence and plan.attempt > 1 else "resumed"}, plan.trace_parent,
                                             links=[plan.trace_parent] if plan.trace_parent and (plan.recovered or plan.attempt > 1) else None)
        except Exception: span = None  # tracing must never fail a run
        if prev: events.extend(json.loads(prev.events or "[]"))  # resumed: one run, one event log
        q: asyncio.Queue = asyncio.Queue(); loop = asyncio.get_running_loop(); cancel = threading.Event()

        def put(x):
            try: loop.call_soon_threadsafe(q.put_nowait, x)
            except RuntimeError: pass  # loop closed after client went away

        if plan.ports is not None:  # a Code node's sandbox is killed when the run is cancelled or times out (TASK-0053)
            plan.ports.cancelled = lambda: cancel.is_set() or bus.is_cancelled(rid)
            plan.ports.start_child = self._child_starter(rid, plan, uid)  # workflow tools (TASK-0134)
        plan.effects = Effects(rid, plan.attempt, ledger=_RunLedger(self.ledger, rid, plan.fence) if self.ledger is not None else None,
                          guard=self._guard(rid, plan.fence))

        def worker():
            g = None
            try:
                g = plan.events()
                for ev in g:
                    if cancel.is_set(): break  # cooperative cancel between steps
                    if bus.is_cancelled(rid): put(CANCEL_API); break  # cancel requested via REST / another worker
                    put(ev)
            except StaleLease:
                put(FENCED)
            except ValidationError as e:
                put(error_event(AppError("WORKFLOW_INVALID", details=e.errors).to_dict()))
            except AppError as e:
                put(error_event(e.to_dict()))
            except Exception as e:
                put(error_event({"code": "RUN_FAILED", "message": safe_error(e)}))
            finally:
                if g is not None:
                    try: g.close()  # stops LangGraph stream / kills import subprocess
                    except Exception: pass
                put(None)

        async def emit(ev):
            nonlocal connected
            if ev.get("type") != "node_token": events.append(ev)  # live LLM text is not part of the stored event log
            if span is not None and ev.get("type") in ("node_finished", "error"):
                try: self.telemetry.node(span, ev)  # live span (TASK-0020)
                except Exception: pass
            try: await bus.apublish(rid, ev)
            except Exception: pass  # fan-out is best effort; the socket and history stay authoritative
            if connected: connected = await send(cap_event(ev))

        try:
            if plan.recovered: first = {"type": "run_recovered", "run_id": rid, "ts": t0, "node": plan.resume["node"], "nodes": resume_nodes(plan.resume),
                                        "attempt": plan.attempt}
            elif prev: first = {"type": "run_resumed", "run_id": rid, "ts": t0, "node": plan.resume["node"], "nodes": resume_nodes(plan.resume),
                                **({"response": plan.resume["value"]} if "value" in plan.resume else {}),
                                **({"by": plan.resumed_by} if plan.resumed_by else {})}
            else: first = {"type": "run_started", "run_id": rid, "ts": t0, **({"forked_from": plan.forked} if plan.forked else {})}
            await emit(first)
            if plan.checkpointing: await self._save_progress(rid, events, plan.resume or {}, plan, span)  # this segment's trace, before any node
            threading.Thread(target=worker, daemon=True).start()
            listener = asyncio.create_task(listen()); deadline = t0 + config.run_timeout(); ended = None
            while True:
                get = asyncio.ensure_future(q.get())
                done, _ = await asyncio.wait({get, listener}, timeout=max(0.0, deadline - time.time()), return_when=asyncio.FIRST_COMPLETED)
                if get in done:
                    ev = get.result()
                    if ev is None: break
                    if ev is CANCEL_API: ended = "api"; cancel.set(); break
                    if ev is FENCED: ended = "fenced"; cancel.set(); break
                    if ev.get("type") == "_checkpoint":  # engine progress marker: never sent or stored as an event
                        if plan.checkpointing:
                            try: await self._save_progress(rid, events, ev, plan, span)
                            except StaleLease: ended = "fenced"; cancel.set(); break
                        continue
                    if ev.get("type", "").startswith("_"): continue  # other internal markers (e.g. sandbox `_restart`)
                    ev = _normalise(ev); ev["ts"] = time.time()
                    if ev["type"] == "run_finished": final = ev.get("state")
                    if ev["type"] == "error": status = "error"
                    if ev["type"] in ("run_waiting", "run_paused"):
                        status = "waiting" if ev["type"] == "run_waiting" else "paused"
                        checkpoint = {**ev.pop("checkpoint"), "workflow": plan.workflow, **({"wait": ev["wait"]} if ev.get("wait") else {})}
                    await emit(ev); continue
                get.cancel()
                if listener in done:
                    ended = listener.result(); connected = connected and ended == "cancelled"
                else:
                    ended = "timeout"
                cancel.set(); break
            if not listener.done(): listener.cancel()
            if ended == "fenced": return self._fenced(rid, span, plan, uid, t0)
            if ended in ("cancelled", "disconnected", "api"):
                status = "cancelled"
                reason = {"cancelled": "client", "disconnected": "disconnect"}.get(ended, "api")
                await emit({"type": "run_cancelled", "ts": time.time(), "reason": reason})
            elif ended == "timeout":
                status = "timeout"
                await emit(error_event(AppError("RUN_TIMEOUT", seconds=f"{config.run_timeout():g}").to_dict(), status="timeout", ts=time.time()))
        except asyncio.CancelledError:  # handler cancelled (server shutdown / client gone mid-await): still keep history
            cancel.set(); status = "cancelled"
            events.append({"type": "run_cancelled", "ts": time.time(), "reason": "disconnect"})
            def keep():
                try: self.record(rid, plan.workflow_id, plan.input, events, final, status, started, uid, None, plan.source, plan.version, span, fence=plan.fence)
                except StaleLease: self._fenced(rid, span, plan, uid, t0)
            try: await _write_in_thread(keep)  # submitted before this await, so a closing loop cannot drop it
            except asyncio.CancelledError: pass  # cancelled again while waiting: the thread still finishes the write
            raise
        try: summary = await _write_in_thread(self.record, rid, plan.workflow_id, plan.input, events, final, status, started, uid, checkpoint,
                                              plan.source, plan.version, span, fence=plan.fence)
        except StaleLease: return self._fenced(rid, span, plan, uid, t0)
        child_ids = []
        if checkpoint and (checkpoint.get("wait") or {}).get("kind") == "child": child_ids.append(checkpoint["wait"]["run_id"])
        for w in (checkpoint or {}).get("waits") or []:
            if isinstance(w, dict) and w.get("kind") == "child" and w.get("run_id"): child_ids.append(w["run_id"])
        for cid in child_ids:  # a child may have ended before this wait was recorded
            await _write_in_thread(self.resume_parent, cid)
        if connected: await send({"type": "run_summary", "run_id": rid, "status": status, "ts": time.time(), **summary})  # not stored as an event
        return status

    def _guard(self, rid: str, fence: Optional[int]):
        """Fencing check before every side-effect node of a queue job (TASK-0021)."""
        if fence is None: return None
        def check():
            if self.runs.lease_gen(rid) != fence: raise StaleLease(rid)
        return check

    def _fenced(self, rid, span, plan, uid, t0) -> str:
        """Another worker claimed this run: stop without writing anything; close our trace segment as cancelled."""
        log.warning("run %s: lease generation %s is stale, this worker stops (another worker owns the run)", rid, plan.fence)
        try: self.telemetry.end_run(span, {"id": rid, "status": "cancelled", "started": t0, "ended": time.time(), "source": plan.source},
                                    {"error_count": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": None, "duration_ms": 0}, observe=False)
        except Exception: pass
        return "fenced"
