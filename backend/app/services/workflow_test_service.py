"""Workflow tests (TASK-0067, REQ-0042, DEC-0044): saved test cases and the suite runs that check them.

A test case is an input, the answers to give at Human nodes (in order, per node) and checks (engine.checks). A suite
runs some or all cases against the workflow's saved version. Each case is an ordinary queued run with
`source="test"` and the job flag `test`, so the run sends no e-mail, channel message, notification or callback, and with
the suite's `mock` option every LLM node uses the offline mock. At most STUDIO_TEST_PARALLEL cases of a suite run at
once; when a test run settles (RunService.settled -> `on_settled`) the suite records it, or answers its Human node with
the next scripted answer, and starts the next case. One suite runs per workflow at a time.

A suite result is compared with the latest finished suite run on an earlier version (TASK-0068): per case regression,
fixed, still failing, still passing or new. A suite can also run on a stored earlier version, and a draft case can be
made from a run (its input, its Human answers in order and checks that the run passes).

Permissions: users who can view the workflow see its cases and results; users who can edit it change and run them.
"""
import json, time, uuid
from typing import Callable, List, Optional
from ..core import config, permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..engine import agents, checks as C
from ..engine.limits import size
from ..models import Run, WorkflowTest, WorkflowTestResult, WorkflowTestSuite
from ..repositories import RunRepository, WorkflowRepository, WorkflowTestRepository, WorkflowVersionRepository
from .langsmith import configured as langsmith_configured
from .job_queue import JobQueue, enqueue_resume
from .run_service import RESPONSE_MAX

log = get_logger("tests")
NAME_MAX = 120
ANSWERS_MAX = 20  # scripted answers per Human node
FINAL = ("passed", "failed", "cancelled")
RESUME_DELAY = 1.0  # seconds before a scripted Human answer resumes a test run
CHANGE = {("passed", "failed"): "regression", ("failed", "passed"): "fixed", ("failed", "failed"): "still_failing", ("passed", "passed"): "still_passing"}
CHANGES = ("regression", "fixed", "still_failing", "still_passing", "new")
PREFILL_TEXT = 200  # a longer final value is checked with "contains" its first characters


def _id() -> str: return uuid.uuid4().hex[:12]


def answer_key(node: Optional[str]) -> Optional[str]:
    """Answers are listed per Human node, and an Agent node's tool approvals under the Agent node's id (TASK-0117)."""
    return agents.agent_of_step(node or "") or node


class WorkflowTestService:
    def __init__(self, repo: WorkflowTestRepository, workflows: WorkflowRepository, runs: RunRepository, versions: WorkflowVersionRepository,
                 jobs: JobQueue, run_service: Callable[[], object], access=None, langsmith: Optional[Callable[[], object]] = None):
        self.repo, self.workflows, self.runs, self.versions, self.jobs, self.access = repo, workflows, runs, versions, jobs, access
        self.run_service = run_service  # -> RunService: closes a test run that waits with no answer left, cancels running cases
        self.langsmith = langsmith  # -> LangSmithService: a finished suite goes to LangSmith when that setting is on

    def _workflow(self, wid: str, uid: str, action: str = P.VIEW):
        if self.access is not None: return self.access.workflow(wid, uid, action)
        w = self.workflows.get_owned(wid, uid)
        if w is None: raise AppError("WORKFLOW_NOT_FOUND")
        return w

    def _editable(self, wid: str, uid: str):
        w = self._workflow(wid, uid, P.EDIT)
        if json.loads(w.data or "{}").get("source"): raise AppError("TEST_NOT_SUPPORTED")  # imported LangGraph repositories
        return w

    def _case(self, wid: str, tid: str) -> WorkflowTest:
        t = self.repo.get(tid)
        if t is None or t.workflow_id != wid: raise AppError("TEST_NOT_FOUND")
        return t

    # ---- views ----
    @staticmethod
    def public(t: WorkflowTest, last: Optional[WorkflowTestResult] = None) -> dict:
        return {"id": t.id, "name": t.name, "input": json.loads(t.input), "answers": json.loads(t.answers), "checks": json.loads(t.checks),
                "created": t.created, "updated": t.updated,
                "last": {"status": last.status, "suite_id": last.suite_id, "version": last.version, "ended": last.ended} if last else None}

    @staticmethod
    def public_suite(s: WorkflowTestSuite, results: Optional[list[WorkflowTestResult]] = None, by: Optional[str] = None,
                     compare: Optional[dict] = None) -> dict:
        out = {"id": s.id, "workflow_id": s.workflow_id, "version": s.version, "status": s.status, "mock": s.mock, "total": s.total,
               "passed": s.passed, "failed": s.failed, "started": s.started, "ended": s.ended, "by": by, "langsmith_url": s.langsmith_url}
        if results is not None:
            changes = (compare or {}).get("changes", {})
            out["compare"] = {k: compare[k] for k in ("suite_id", "version", "counts")} if compare else None
            out["results"] = []
            for r in results:
                case = json.loads(r.case); got = json.loads(r.checks) if r.checks else None
                out["results"].append({"id": r.id, "test_id": r.test_id, "name": r.name, "status": r.status, "run_id": r.run_id, "version": r.version,
                                       "reason": r.reason, "detail": r.detail, "ended": r.ended, "change": changes.get(r.id),
                                       "checks": [{**c, **(got[i] if got else {})} for i, c in enumerate(case["checks"])]})
        return out

    def list(self, wid: str, uid: str) -> dict:
        w = self._workflow(wid, uid)
        cases = self.repo.list_for_workflow(wid); last = self.repo.latest_results([t.id for t in cases])
        return {"items": [self.public(t, last.get(t.id)) for t in cases], "suites": self._suites(wid),
                "can_edit": (self.access is None or self.access.may(wid, uid, P.EDIT)) and not json.loads(w.data or "{}").get("source"),
                "limit": config.test_cases_max(), "langsmith": self.langsmith is not None and self.langsmith().evals_enabled(),
                "langsmith_configured": self.langsmith is not None and langsmith_configured()}

    def history(self, wid: str, uid: str) -> dict:
        """The workflow's last suite runs, newest first: version, who, when, passed / failed."""
        self._workflow(wid, uid); return {"items": self._suites(wid)}

    def _suites(self, wid: str) -> List[dict]: return [self.public_suite(s, by=e) for s, e in self.repo.suites(wid)]

    def suite(self, wid: str, sid: str, uid: str) -> dict:
        self._workflow(wid, uid); s = self.repo.suite(sid)
        if s is None or s.workflow_id != wid: raise AppError("TEST_SUITE_NOT_FOUND")
        results = self.repo.results(sid)
        return self.public_suite(s, results, compare=self._compare(s, results))

    def _compare(self, s: WorkflowTestSuite, results: List[WorkflowTestResult]) -> Optional[dict]:
        """Each finished case against the latest finished suite run on an earlier version, by test id (a case edited in
        between is the same case; one without an earlier result is new). None when there is no such suite run."""
        base = self.repo.baseline(s.workflow_id, s.version) if s.version else None
        if base is None: return None
        before = {r.test_id: r.status for r in self.repo.results(base.id) if r.status in ("passed", "failed")}
        changes = {r.id: CHANGE[(before[r.test_id], r.status)] if r.test_id in before else "new" for r in results if r.status in ("passed", "failed")}
        return {"suite_id": base.id, "version": base.version, "counts": {k: sum(v == k for v in changes.values()) for k in CHANGES}, "changes": changes}

    # ---- test cases ----
    @staticmethod
    def _clean(body) -> dict:
        if not isinstance(body, dict): raise AppError("TEST_CASE_INVALID", reason="the body must be an object")
        name = body.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > NAME_MAX:
            raise AppError("TEST_CASE_INVALID", reason=f"the name must be 1-{NAME_MAX} characters")
        inp = body.get("input") if body.get("input") is not None else {}
        if not isinstance(inp, dict): raise AppError("RUN_INPUT_INVALID")
        if size(inp) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE", max_kb=config.input_max() // 1024)
        answers = body.get("answers") if body.get("answers") is not None else {}
        if not isinstance(answers, dict) or any(not isinstance(k, str) or not isinstance(v, list) or len(v) > ANSWERS_MAX
                                                or any(not isinstance(a, str) or len(a) > RESPONSE_MAX for a in v) for k, v in answers.items()):
            raise AppError("TEST_CASE_INVALID", reason=f"answers must be text, at most {ANSWERS_MAX} per Human node")
        if (errs := C.errors(body.get("checks"))): raise AppError("TEST_CASE_INVALID", reason="; ".join(errs))
        return {"name": name.strip(), "input": json.dumps(inp, ensure_ascii=False), "answers": json.dumps({k: v for k, v in answers.items() if v}, ensure_ascii=False),
                "checks": json.dumps(body["checks"], ensure_ascii=False)}

    def create(self, wid: str, uid: str, body) -> dict:
        self._editable(wid, uid); v = self._clean(body)
        n = self.repo.count_for_workflow(wid)
        if n >= config.test_cases_max(): raise AppError("TEST_CASES_LIMIT", max=config.test_cases_max())
        now = time.time()
        return self.public(self.repo.add(WorkflowTest(id=_id(), workflow_id=wid, position=n, author=uid, created=now, updated=now, **v)))

    def update(self, wid: str, tid: str, uid: str, body) -> dict:
        self._editable(wid, uid); self._case(wid, tid)
        self.repo.set_fields(tid, updated=time.time(), **self._clean(body))
        return self.public(self.repo.get(tid))

    def delete(self, wid: str, tid: str, uid: str) -> dict:
        self._editable(wid, uid); self._case(wid, tid); self.repo.delete(tid)
        return {"ok": True}

    # ---- suite runs ----
    def run(self, wid: str, uid: str, body) -> dict:
        """Run the cases `test_ids` (all when omitted) on the saved version, or on the stored `version`.
        TEST_SUITE_RUNNING while one runs."""
        self._editable(wid, uid); body = body if isinstance(body, dict) else {}
        cases = self.repo.list_for_workflow(wid); ids = body.get("test_ids")
        if ids is not None:
            if not isinstance(ids, list) or not ids or any(i not in {t.id for t in cases} for i in ids): raise AppError("TEST_NOT_FOUND")
            cases = [t for t in cases if t.id in ids]
        if not cases: raise AppError("TEST_NOT_FOUND")
        n = body.get("version")
        if n is None: latest = self.versions.latest(wid); n = latest.version if latest else None
        elif isinstance(n, bool) or not isinstance(n, int) or self.versions.get(wid, n) is None: raise AppError("VERSION_NOT_FOUND")
        now = time.time()
        suite = WorkflowTestSuite(id=_id(), workflow_id=wid, version=n, owner=uid, status="running",
                                  mock=bool(body.get("mock")), total=len(cases), passed=0, failed=0, started=now)
        results = [WorkflowTestResult(id=_id(), suite_id=suite.id, test_id=t.id, name=t.name, position=i, status="queued",
                                      case=json.dumps({"input": json.loads(t.input), "answers": json.loads(t.answers), "checks": json.loads(t.checks)},
                                                      ensure_ascii=False)) for i, t in enumerate(cases)]
        if not self.repo.start_suite(suite, results): raise AppError("TEST_SUITE_RUNNING")
        self._advance(suite.id)
        return self.suite(wid, suite.id, uid)

    def cancel(self, wid: str, sid: str, uid: str) -> dict:
        self._editable(wid, uid); s = self.repo.suite(sid)
        if s is None or s.workflow_id != wid: raise AppError("TEST_SUITE_NOT_FOUND")
        rs = self.repo.results(sid); now = time.time()
        if self.repo.end_suite(sid, "cancelled", sum(r.status == "passed" for r in rs), sum(r.status == "failed" for r in rs), now):
            for r in rs:
                if r.status in FINAL or not self.repo.finish_result(r.id, "cancelled", now): continue
                if r.run_id:
                    try: self.run_service().cancel(r.run_id, s.owner)  # queued, running or waiting for its next answer
                    except AppError: pass  # already finished
        return self.suite(wid, sid, uid)

    def _advance(self, sid: str) -> None:
        """Start queued cases up to the parallel limit; end the suite once every case has a result."""
        s = self.repo.suite(sid)
        if s is None or s.status != "running": return
        rs = self.repo.results(sid); running = sum(r.status == "running" for r in rs)
        for r in rs:
            if r.status != "queued": continue
            if running >= config.test_parallel(): return
            if self._start(s, r): running += 1
        if running == 0 and all(r.status in FINAL for r in self.repo.results(sid)):
            rs = self.repo.results(sid)
            if self.repo.end_suite(sid, "done", sum(r.status == "passed" for r in rs), sum(r.status == "failed" for r in rs), time.time()) \
                    and self.langsmith is not None and self.langsmith().evals_enabled():
                self.jobs.enqueue({"kind": "langsmith_suite", "suite_id": sid})  # network: the worker sends it, not this request

    def test_job(self, rid: str) -> Optional[dict]:
        """The `test` field of a test run's queue job, rebuilt from its suite (start-up recovery, TASK-0115)."""
        res = self.repo.result_for_run(rid); s = self.repo.suite(res.suite_id) if res else None
        return {"mock": bool(s.mock)} if s else None

    def _start(self, s: WorkflowTestSuite, r: WorkflowTestResult) -> bool:
        rid = uuid.uuid4().hex[:10]
        if not self.repo.claim_result(r.id, rid): return False
        inp = json.loads(r.case)["input"]
        self.runs.add(Run(id=rid, workflow_id=s.workflow_id, input=json.dumps(inp, ensure_ascii=False), events="[]", status="queued",
                          started=time.time(), owner=s.owner, source="test", workflow_version=s.version))
        self.jobs.enqueue({"run_id": rid, "workflow_id": s.workflow_id, "owner": s.owner, "input": inp, "callback_url": None, "token_id": None,
                           "source": "test", "test": {"mock": bool(s.mock)}, **({"version": s.version} if s.version else {})})  # that version's snapshot
        return True

    def send_to_langsmith(self, wid: str, sid: str, uid: str) -> dict:
        """Send a finished suite run to LangSmith now (again: a new experiment)."""
        self._editable(wid, uid); s = self.repo.suite(sid)
        if s is None or s.workflow_id != wid: raise AppError("TEST_SUITE_NOT_FOUND")
        if s.status == "running" or self.langsmith is None: raise AppError("TEST_SUITE_RUNNING" if s.status == "running" else "LANGSMITH_NOT_CONFIGURED")
        self.langsmith().push_suite(sid)
        return self.suite(wid, sid, uid)

    # ---- a draft case from a run ----
    def from_run(self, wid: str, rid: str, uid: str) -> dict:
        """A test case (not saved) that replays run `rid`: its input, the Human answers it was given in order, and checks it
        passes: its status, each node that ran (but Start and End), each field it set (a long value as "contains" its first characters)."""
        w = self._editable(wid, uid); run = self.runs.get(rid)
        mine = self.access is None or self.access.access_of(w, uid) == "owner"  # the run history rule: others see only their runs
        if run is None or run.workflow_id != wid or not (mine or run.owner == uid) or run.status in ("queued", "running"):
            raise AppError("RUN_NOT_FOUND")
        events = json.loads(run.events or "[]"); inp = json.loads(run.input or "{}") or {}
        final = json.loads(run.final_state or "null"); final = final if isinstance(final, dict) else {}
        answers: dict = {}
        for e in events:
            if e.get("type") == "run_resumed" and isinstance(e.get("response"), str): answers.setdefault(answer_key(e.get("node")), []).append(e["response"])
        checks = [{"kind": "status", "value": run.status}] if run.status in C.STATUSES else []
        trivial = {n.get("id") for n in self._graph(run).get("nodes") or [] if isinstance(n, dict) and n.get("type") in ("start", "end")}
        ran = list(dict.fromkeys(e.get("node") for e in events if e.get("type") == "node_finished" and e.get("node") and e["node"] not in trivial))
        checks += [{"kind": "node", "node": n, "ran": True} for n in ran]
        for k, v in final.items():
            if k in inp and inp[k] == v: continue  # passed through unchanged
            if v in (None, "", [], {}): checks.append({"kind": "field", "field": k, "op": "empty"}); continue
            t = C.text(v)
            checks.append({"kind": "field", "field": k, "op": "equals", "value": t} if len(t) <= PREFILL_TEXT
                          else {"kind": "field", "field": k, "op": "contains", "value": t[:PREFILL_TEXT]})
        return {"name": f"Run {rid}", "input": inp, "answers": {k: v[:ANSWERS_MAX] for k, v in answers.items() if k}, "checks": checks[:C.MAX_CHECKS]}

    # ---- a test run settled (RunService.settled) ----
    def on_settled(self, rid: str) -> None:
        res = self.repo.result_for_run(rid)
        if res is None or res.status != "running": return
        run = self.runs.get(rid); s = self.repo.suite(res.suite_id)
        if run is None or s is None or run.status in ("queued", "running"): return
        case = json.loads(res.case); now = time.time()
        if s.status != "running": self.repo.finish_result(res.id, "cancelled", now); return
        if run.status == "waiting":
            events = json.loads(run.events or "[]")
            node = next((e.get("node") for e in reversed(events) if e.get("type") == "run_waiting"), None)
            used = sum(1 for e in events if e.get("type") == "run_resumed" and e.get("node") == node)
            answers = case["answers"].get(answer_key(node)) or []
            if used < len(answers):  # answer like a channel decision would; the worker's claim makes it happen once
                # a second later: this segment is still settling, and must leave the run bus before the next one joins it
                enqueue_resume(self.runs, lambda job: self.jobs.enqueue_at(job, now + RESUME_DELAY),
                               {"kind": "resume", "run_id": rid, "owner": run.owner, "response": answers[used], "workflow_id": run.workflow_id,
                                "by": {"channel": "test"}, "test": {"mock": bool(s.mock)}})
                return
            try: self.run_service().cancel_waiting(rid, run.owner)
            except AppError: pass
            self.repo.finish_result(res.id, "failed", now, version=run.workflow_version, reason="no_answer", detail=node)
        else:
            got = C.evaluate(case["checks"], {"status": run.status, "final_state": json.loads(run.final_state or "null"),
                                              "events": json.loads(run.events or "[]"), "duration_ms": run.duration_ms, "cost_usd": run.cost_usd},
                             self._graph(run))
            ok = C.passed(case["checks"], got, run.status or "error")
            self.repo.finish_result(res.id, "passed" if ok else "failed", now, version=run.workflow_version, checks=json.dumps(got, ensure_ascii=False),
                                    reason=None if ok or run.status == "ok" else "run_status", detail=None if run.status == "ok" else run.status)
        self._advance(s.id)

    def _graph(self, run: Run) -> dict:
        """The graph the test run ran: its stored version, else the workflow as it is now."""
        v = self.versions.get(run.workflow_id, run.workflow_version) if run.workflow_version else None
        if v is not None: return json.loads(v.data or "{}")
        w = self.workflows.get(run.workflow_id)
        return json.loads(w.data or "{}") if w else {}
