"""A subset of the LangGraph Agent Server API over Superstep workflows (`/api/lg`, DEC: docs/agent-server-api.md).

LangGraph clients (the `langgraph-sdk` Python / JS clients, `RemoteGraph`) talk to Superstep as to an Agent Server:
- an **assistant** is a workflow the caller may run (assistant_id = graph_id = workflow id);
- a **thread** is a row of `agent_threads`; its state is the state of its latest run, and a new run on it starts from
  that state with the new input on top;
- a **run** is an ordinary queued API run (it shows in the workflow's history as `api`), linked to its thread.
  A Human node pauses it: the thread is `interrupted` and a run with `command={"resume": answer}` continues it.
Callers authenticate with a workflow token (`wft_…`, scoped to its workflow) or a user JWT.
"""
from __future__ import annotations
import asyncio, json, time, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional
from ..core import config
from ..core import permissions as P
from ..core.errors import AppError
from ..engine.reducers import apply as apply_delta
from ..models import AgentThread, AgentThreadRun, Run
from ..repositories import AgentThreadRepository, RunRepository, WorkflowRepository
from .run_service import human_response
from .trigger_service import TOKEN_PREFIX, TriggerService
from .telemetry import trace_url

RUN_STATUS = {"queued": "pending", "running": "running", "ok": "success", "error": "error", "timeout": "timeout",
              "waiting": "interrupted", "paused": "interrupted", "cancelled": "interrupted", "expired": "error"}
THREAD_STATUS = {"pending": "busy", "running": "busy", "interrupted": "interrupted", "error": "error", "timeout": "error"}
SETTLED = ("ok", "error", "cancelled", "timeout", "waiting", "expired", "paused")
JSON_TYPES = {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean", "object": "object", "list": "array"}
POLL = 0.25  # seconds between looks at a running run (the runs table is shared by all workers)


def iso(ts: Optional[float]) -> Optional[str]:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


def _load(text: Optional[str], default: Any = None) -> Any:
    try: return json.loads(text) if text else default
    except ValueError: return default


@dataclass(frozen=True)
class Principal:
    uid: str
    token_id: Optional[str] = None  # a workflow token: only its workflow, only its threads
    workflow_id: Optional[str] = None


class AgentServerService:
    def __init__(self, workflows: WorkflowRepository, runs: RunRepository, threads: AgentThreadRepository, triggers: TriggerService,
                 users: Callable[[str], dict], access=None, runner: Optional[Callable[[], Any]] = None):
        self.workflows, self.runs, self.threads, self.triggers = workflows, runs, threads, triggers
        self.users = users      # JWT -> user (AuthService.current)
        self.access = access    # AccessService: which workflows a signed-in user may see and run
        self.runner = runner    # -> RunService, for cancel

    # ---- auth ----
    def principal(self, token: Optional[str]) -> Principal:
        if not token: raise AppError("AUTH_REQUIRED")
        if token.startswith(TOKEN_PREFIX):
            t = self.triggers.authenticate(None, token)
            return Principal(t.owner, t.id, t.workflow_id)
        return Principal(self.users(token)["id"])

    async def check_rate(self, p: Principal) -> None:
        if p.token_id: await self.triggers.check_rate(self.triggers.tokens.get(p.token_id))

    # ---- assistants (workflows) ----
    def _workflow(self, p: Principal, aid: str, action: str = P.VIEW):
        if p.workflow_id is not None and aid != p.workflow_id: raise AppError("WORKFLOW_NOT_FOUND")
        if self.access is not None and p.token_id is None: return self.access.workflow(aid, p.uid, action)
        w = self.workflows.get(aid)
        if w is None: raise AppError("WORKFLOW_NOT_FOUND")
        return w

    @staticmethod
    def assistant(w) -> dict:
        return {"assistant_id": w.id, "graph_id": w.id, "name": w.name, "description": None, "config": {}, "context": {},
                "metadata": {"source": "superstep"}, "version": 1, "created_at": iso(w.updated),
                "updated_at": iso(w.updated)}

    def search_assistants(self, p: Principal, graph_id: Optional[str] = None, name: Optional[str] = None,
                          limit: int = 10, offset: int = 0) -> list[dict]:
        if p.token_id: rows = [self._workflow(p, p.workflow_id)]
        else: rows = [w for w, _ in self.access.visible(p.uid)] if self.access is not None else self.workflows.list_for_owner(p.uid)
        rows = [w for w in rows if (graph_id is None or w.id == graph_id) and (not name or name.lower() in (w.name or "").lower())]
        return [self.assistant(w) for w in rows[offset:offset + limit]]

    def get_assistant(self, p: Principal, aid: str) -> dict:
        return self.assistant(self._workflow(p, aid))

    def graph(self, p: Principal, aid: str) -> dict:
        """The workflow in LangGraph's drawable-graph JSON (what `graph.get_graph().to_json()` returns)."""
        wf = _load(self._workflow(p, aid).data, {})
        ids = {"start": "__start__", "end": "__end__"}
        name = lambda n: ids.get(n["type"], n["id"])  # noqa: E731
        nodes = [n for n in wf.get("nodes") or [] if n.get("type") != "note"]
        by_id = {n["id"]: name(n) for n in nodes}
        out = [{"id": name(n), "type": "schema" if n["type"] in ids else "runnable",
                "data": name(n) if n["type"] in ids else {"id": ["superstep", n["type"]], "name": (n.get("data") or {}).get("label") or n["id"]}}
               for n in nodes]
        edges = [{"source": by_id[e["source"]], "target": by_id[e["target"]], "conditional": bool(e.get("label")),
                  **({"data": e["label"]} if e.get("label") else {})}
                 for e in wf.get("edges") or [] if e.get("source") in by_id and e.get("target") in by_id]
        return {"nodes": out, "edges": edges}

    def schemas(self, p: Principal, aid: str) -> dict:
        wf = _load(self._workflow(p, aid).data, {})
        props = {f["name"]: {"type": JSON_TYPES.get(f.get("type"), "string")} for f in wf.get("state") or [] if f.get("name")}
        state = {"title": "State", "type": "object", "properties": props}
        return {"graph_id": aid, "input_schema": state, "output_schema": state, "state_schema": state,
                "config_schema": {"title": "Config", "type": "object", "properties": {}},
                "context_schema": {"title": "Context", "type": "object", "properties": {}}}

    # ---- threads ----
    def _thread(self, p: Principal, tid: str) -> AgentThread:
        t = self.threads.get(tid)
        if t is None or t.owner != p.uid or t.token_id != p.token_id: raise AppError("THREAD_NOT_FOUND")
        return t

    def create_thread(self, p: Principal, metadata: Optional[dict] = None, thread_id: Optional[str] = None, if_exists: str = "raise") -> dict:
        if thread_id and (old := self.threads.get(thread_id)) is not None:
            if if_exists == "do_nothing" and old.owner == p.uid and old.token_id == p.token_id: return self.thread(old)
            raise AppError("THREAD_EXISTS")
        now = time.time()
        t = self.threads.add(AgentThread(id=thread_id or str(uuid.uuid4()), owner=p.uid, token_id=p.token_id, workflow_id=p.workflow_id,
                                         meta=json.dumps(metadata or {}, ensure_ascii=False), created=now, updated=now))
        return self.thread(t)

    def get_thread(self, p: Principal, tid: str) -> dict:
        return self.thread(self._thread(p, tid))

    def search_threads(self, p: Principal, metadata: Optional[dict] = None, status: Optional[str] = None,
                       limit: int = 10, offset: int = 0) -> list[dict]:
        out = [self.thread(t) for t in self.threads.search(p.uid, p.token_id, 1000, 0)]
        out = [t for t in out if all(t["metadata"].get(k) == v for k, v in (metadata or {}).items()) and (not status or t["status"] == status)]
        return out[offset:offset + limit]

    def delete_thread(self, p: Principal, tid: str) -> None:
        self._thread(p, tid); self.threads.delete(tid)

    def _last_run(self, tid: str) -> Optional[Run]:
        links = self.threads.runs(tid, 1)
        return self.runs.get(links[0].run_id) if links else None

    def thread(self, t: AgentThread) -> dict:
        r = self._last_run(t.id)
        st = RUN_STATUS.get(r.status, "error") if r else None
        return {"thread_id": t.id, "created_at": iso(t.created), "updated_at": iso(t.updated), "metadata": _load(t.meta, {}),
                "status": THREAD_STATUS.get(st, "idle"), "values": self.values(r) if r else {},
                "interrupts": {w["id"]: [w] for w in self.interrupts(r)} if r else {}}

    def state(self, p: Principal, tid: str) -> dict:
        t = self._thread(p, tid); r = self._last_run(t.id)
        ints = self.interrupts(r) if r else []
        wait = next((e for e in reversed(_load(r.events, [])) if e.get("type") == "run_waiting"), None) if ints else None
        return {"values": self.values(r) if r else {}, "next": [wait["node"]] if wait else [],
                "tasks": [{"id": i["id"], "name": wait["node"], "interrupts": [i], "error": None, "state": None} for i in ints] if wait else [],
                "interrupts": ints, "metadata": _load(t.meta, {}), "created_at": iso(r.ended or r.started) if r else iso(t.created),
                "checkpoint": {"thread_id": t.id, "checkpoint_ns": "", "checkpoint_id": r.id if r else None}, "parent_checkpoint": None}

    # ---- runs ----
    @staticmethod
    def values(r: Run) -> dict:
        """The run's state: the final state, else the state where it waits, else its input."""
        if r.final_state and (v := _load(r.final_state)) is not None: return v
        ev = next((e for e in reversed(_load(r.events, [])) if e.get("type") in ("run_waiting", "run_paused")), None)
        return (ev or {}).get("state") or _load(r.input, {})

    @staticmethod
    def interrupts(r: Run) -> list[dict]:
        if r.status != "waiting": return []
        ev = next((e for e in reversed(_load(r.events, [])) if e.get("type") == "run_waiting"), None)
        return [{"id": f"{r.id}:{ev.get('node')}", "value": {"node": ev.get("node"), "question": ev.get("prompt")}}] if ev else []

    def run(self, r: Run, link: AgentThreadRun) -> dict:
        return {"run_id": r.id, "thread_id": link.thread_id, "assistant_id": r.workflow_id, "status": RUN_STATUS.get(r.status, "error"),
                "metadata": _load(link.meta, {}), "created_at": iso(link.created), "updated_at": iso(r.ended or r.started),
                "multitask_strategy": "reject", "kwargs": {}, "trace_url": trace_url(r.trace_id, r.trace_root)}

    def _run_of(self, p: Principal, tid: str, rid: str) -> tuple[Run, AgentThreadRun]:
        self._thread(p, tid); link = self.threads.run(rid); r = self.runs.get(rid)
        if link is None or link.thread_id != tid or r is None: raise AppError("RUN_NOT_FOUND")
        return r, link

    def get_run(self, p: Principal, tid: str, rid: str) -> dict:
        return self.run(*self._run_of(p, tid, rid))

    def list_runs(self, p: Principal, tid: str, limit: int = 10, offset: int = 0) -> list[dict]:
        self._thread(p, tid)
        return [self.run(r, link) for link in self.threads.runs(tid, limit, offset) if (r := self.runs.get(link.run_id))]

    def create_run(self, p: Principal, tid: Optional[str], assistant_id: str, inp: Any = None, command: Optional[dict] = None,
                   metadata: Optional[dict] = None) -> tuple[dict, Run, Optional[float]]:
        """Start a run on the thread (a new temporary thread when `tid` is None): (the run, its row, `since`).
        `command.resume` answers the Human node the thread waits at, continuing that run; `since` is then the end of
        its previous segment, so waiting and streaming follow the new one. Otherwise the workflow runs from the
        thread's state with `input` on top (`since` is None)."""
        w = self._workflow(p, assistant_id, P.RUN)
        t = self._thread(p, tid) if tid else self.threads.get(self.create_thread(p)["thread_id"])
        if t.workflow_id and t.workflow_id != w.id: raise AppError("THREAD_WORKFLOW_MISMATCH")
        last = self._last_run(t.id)
        if last is not None and last.status in ("queued", "running"): raise AppError("THREAD_BUSY")
        now = time.time()
        link = lambda rid: self.threads.add_run(AgentThreadRun(run_id=rid, thread_id=t.id, meta=json.dumps(metadata or {}), created=now))  # noqa: E731
        if command and "resume" in command:
            if last is None or last.status != "waiting": raise AppError("RUN_NOT_WAITING")
            human_response(command["resume"])  # text or true / false: refused here, not later by the worker
            self.threads.set_fields(t.id, updated=now)
            self.triggers.jobs.enqueue({"kind": "resume", "run_id": last.id, "owner": last.owner, "response": command["resume"],
                                        "workflow_id": last.workflow_id})
            return {**self.run(last, self.threads.run(last.id)), "status": "pending"}, last, last.ended or 0.0
        inp = {} if inp is None else inp
        self.triggers.check_input(inp)
        start = {**(self.values(last) if last is not None else {}), **inp}
        rid = self.triggers.queue(w.id, p.uid, start, token_id=p.token_id, before_enqueue=link)
        self.threads.set_fields(t.id, workflow_id=w.id, updated=now)
        r = self.runs.get(rid)
        return self.run(r, self.threads.run(rid)), r, None

    async def wait(self, p: Principal, tid: str, rid: str, since: Optional[float] = None) -> Run:
        """Poll until the run settles (a resumed run: settles again after `since`, its previous end)."""
        deadline = time.time() + config.run_timeout() + config.sync_wait_max()
        while True:
            r = await asyncio.to_thread(self.runs.get, rid)
            if r is not None and r.status in SETTLED and (since is None or (r.ended or 0) > since): return r
            if time.time() >= deadline: return r
            await asyncio.sleep(POLL)

    def output(self, r: Run) -> dict:
        """What `runs.wait` returns: the state, with `__interrupt__` when the run waits at a Human node."""
        ints = self.interrupts(r)
        if r.status in ("error", "timeout", "expired") and not ints:
            err = next((e.get("error") for e in reversed(_load(r.events, [])) if e.get("type") == "error"), None)
            return {**self.values(r), "__error__": err or {"code": r.status.upper()}}
        return {**self.values(r), **({"__interrupt__": ints} if ints else {})}

    async def stream(self, r0: Run, tid: str, modes: list[str], since: Optional[float] = None) -> AsyncIterator[tuple[str, Any]]:
        """(event, data) pairs in LangGraph's stream format while the run goes: `metadata`, then per finished node
        `updates` {node: delta} and/or `values` (the whole state), and `error` when the run fails. `since`: a resumed run (its
        previous end); the nodes it finished before the pause are not streamed again."""
        yield "metadata", {"run_id": r0.id, "thread_id": tid, "attempt": 1}
        w = self.workflows.get(r0.workflow_id)
        fields = (_load(w.data, {}) if w else {}).get("state") or []
        seen = sum(1 for e in _load(r0.events, []) if e.get("type") == "node_finished") if since is not None else 0
        state = self.values(r0) if since is not None else _load(r0.input, {})
        deadline = time.time() + config.run_timeout() + config.sync_wait_max()
        while True:
            r = await asyncio.to_thread(self.runs.get, r0.id) or r0
            events = _load(r.events, [])
            finished = [e for e in events if e.get("type") == "node_finished"]
            for e in finished[seen:]:
                if e.get("node_type") in ("start", "end"): continue  # not LangGraph nodes
                state = apply_delta(state, e.get("delta") or {}, fields)
                if "updates" in modes: yield "updates", {e.get("node"): e.get("delta") or {}}
                if "values" in modes: yield "values", state
            seen = max(seen, len(finished))
            if (r.status in SETTLED and (since is None or (r.ended or 0) > since)) or time.time() >= deadline:
                if ints := self.interrupts(r):
                    if "updates" in modes: yield "updates", {"__interrupt__": ints}
                    if "values" in modes: yield "values", {**self.values(r), "__interrupt__": ints}
                elif r.status in ("error", "timeout", "expired"):
                    err = next((e.get("error") for e in reversed(events) if e.get("type") == "error"), None) or {}
                    yield "error", {"error": err.get("code") or r.status.upper(), "message": err.get("message") or r.status}
                elif "values" in modes and self.values(r) != state: yield "values", self.values(r)
                return
            await asyncio.sleep(POLL)

    def cancel(self, p: Principal, tid: str, rid: str) -> None:
        r, _ = self._run_of(p, tid, rid)
        if self.runner is not None: self.runner().cancel(r.id, r.owner)
