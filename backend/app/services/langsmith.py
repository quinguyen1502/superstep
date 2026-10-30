"""LangSmith (opt-in): trace links for runs traced to LangSmith, and workflow test suites sent as experiments.

Both need `LANGSMITH_API_KEY` (and `LANGSMITH_ENDPOINT` for a self-hosted LangSmith). Traces go to LangSmith over OTLP
(services.telemetry, `LANGSMITH_TRACING=true`); LangSmith names a run after the OTel span id of its root span, so a
run's link is built from `runs.trace_root` and the project (`LANGSMITH_PROJECT`, else "default"), looked up once.
Sending test results is a studio setting (`langsmith` -> {"evals": true}, admins): when a suite run ends, its cases
become examples of a dataset ("Superstep: <workflow> (<id>)", one example per test case, kept in sync) and the
suite becomes an experiment on that dataset: one run per case with the run's final state, and feedback `passed`
plus one score per check. The `langsmith` SDK is imported only when a client is needed.
"""
from __future__ import annotations
import json, os, threading, time, uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from ..core import permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..repositories.chat_sessions import feedback_is_pending

log = get_logger("langsmith")
SETTING = "langsmith"
TRUE = ("1", "true", "yes", "on")
WEB_DEFAULT = "https://smith.langchain.com"
RETRY_AFTER = 300  # seconds before a failed project lookup is tried again


def _env(name: str) -> str: return (os.environ.get(name) or "").strip()
def configured() -> bool: return bool(_env("LANGSMITH_API_KEY"))
def tracing() -> bool: return configured() and _env("LANGSMITH_TRACING").lower() in TRUE
def project_name() -> str: return _env("LANGSMITH_PROJECT") or "default"


def default_client():
    from langsmith import Client
    return Client(auto_batch_tracing=False)  # runs are written before their feedback


client_factory: Callable[[], Any] = default_client  # tests replace it with a fake
_project: dict = {}  # name -> (web url, tenant id, project id) or (None, retry time)
_lock = threading.Lock()


def run_id_of(span_id: str) -> str:
    """LangSmith's run id for an OTLP span: the 8-byte span id in the low bytes of a UUID."""
    return str(uuid.UUID(int=int(span_id, 16)))


def web_url(client) -> str:
    return (getattr(client, "_host_url", None) or WEB_DEFAULT).rstrip("/")


def _project_ids(name: str) -> Optional[tuple[str, str, str]]:
    with _lock:
        hit = _project.get(name)
        if hit and (hit[0] is not None or time.time() < hit[1]): return hit if hit[0] is not None else None
        try:
            c = client_factory(); p = c.read_project(project_name=name)
            _project[name] = (web_url(c), str(p.tenant_id), str(p.id))
        except Exception as e:  # noqa: BLE001  (unknown project, network, auth): no link, never an error
            log.info("LangSmith project %r lookup failed: %s", name, type(e).__name__); _project[name] = (None, time.time() + RETRY_AFTER)
            return None
        return _project[name]


def run_url(trace_root: Optional[str]) -> Optional[str]:
    """The LangSmith page of a run traced to LangSmith (None when not tracing there or not known)."""
    if not trace_root or not tracing(): return None
    ids = _project_ids(project_name())
    if ids is None: return None
    web, tenant, project = ids; rid = run_id_of(trace_root)
    return f"{web}/o/{tenant}/projects/p/{project}/r/{rid}?trace_id={rid}"


def _iso(ts: Optional[float]) -> Optional[datetime]:
    return datetime.fromtimestamp(ts, timezone.utc) if ts else None


class LangSmithService:
    def __init__(self, settings, access, tests, workflows, runs, audit=None, sessions=None):
        self.settings, self.access, self.tests, self.workflows, self.runs, self.audit = settings, access, tests, workflows, runs, audit
        self.sessions = sessions  # chat ratings sent as feedback on the run's trace (TASK-0165)

    # ---- the studio setting (admins) ----
    def evals_on(self) -> bool:
        return bool((self.settings.get(SETTING, {}) or {}).get("evals"))

    def evals_enabled(self) -> bool:
        return configured() and self.evals_on()

    def status(self) -> dict:
        return {"configured": configured(), "tracing": tracing(), "evals": self.evals_on(), "project": project_name(),
                "endpoint": _env("LANGSMITH_ENDPOINT") or None}

    def get(self, uid: str) -> dict:
        self.access.require(uid, P.USERS_MANAGE); return self.status()

    def update(self, uid: str, evals: bool) -> dict:
        self.access.require(uid, P.USERS_MANAGE)
        before = self.evals_on()
        self.settings.set(SETTING, {"evals": bool(evals)}, uid, time.time())
        if self.audit: self.audit.record(uid, "policy.langsmith", "policy", SETTING, "langsmith", before={"evals": before}, after={"evals": bool(evals)})
        return self.status()

    # ---- a suite run as an experiment ----
    def push_suite(self, sid: str) -> str:
        """Send the suite run to LangSmith (dataset kept in sync, a new experiment); returns the experiment's URL."""
        if not configured(): raise AppError("LANGSMITH_NOT_CONFIGURED")
        s = self.tests.suite(sid)
        if s is None: raise AppError("TEST_SUITE_NOT_FOUND")
        w = self.workflows.get(s.workflow_id); name = (w.name if w else None) or s.workflow_id
        results = [r for r in self.tests.results(sid) if r.status in ("passed", "failed")]
        try:
            c = client_factory()
            ds_name = f"Superstep: {name} ({s.workflow_id})"
            ds = next(iter(c.list_datasets(dataset_name=ds_name)), None) or c.create_dataset(
                ds_name, description=f"Test cases of the Superstep workflow {name}", metadata={"superstep_workflow_id": s.workflow_id})
            examples = {(e.metadata or {}).get("test_id"): e for e in c.list_examples(dataset_id=ds.id)}
            example_of: dict = {}
            for r in results:
                case = json.loads(r.case)
                body = {"inputs": case["input"], "outputs": {"checks": case["checks"]},
                        "metadata": {"test_id": r.test_id, "name": r.name, "answers": case.get("answers") or {}}}
                if (e := examples.get(r.test_id)) is not None:
                    c.update_example(e.id, **body); example_of[r.test_id] = e.id
                else:
                    example_of[r.test_id] = c.create_example(dataset_id=ds.id, **body).id
            exp = c.create_project(f"{name} v{s.version if s.version is not None else '-'} · {sid}", reference_dataset_id=ds.id,
                                   description="Superstep workflow test suite run",
                                   metadata={"superstep_workflow_id": s.workflow_id, "suite_id": sid, "version": s.version, "mock": bool(s.mock)})
            for r in results:
                run = self.runs.get(r.run_id) if r.run_id else None
                rid = uuid.uuid4(); case = json.loads(r.case)
                c.create_run(r.name, case["input"], "chain", id=rid, project_name=exp.name, reference_example_id=example_of[r.test_id],
                             outputs=json.loads(run.final_state or "null") or {} if run else {}, error=r.reason,
                             start_time=_iso(run.started if run else s.started), end_time=_iso((run.ended if run else None) or r.ended),
                             extra={"metadata": {"superstep_run_id": r.run_id, "status": run.status if run else None}})
                c.create_feedback(rid, "passed", score=1.0 if r.status == "passed" else 0.0)
                for i, chk in enumerate(json.loads(r.checks or "[]")):
                    if chk.get("passed") is None: continue
                    c.create_feedback(rid, f"check {i + 1}: {case['checks'][i].get('kind')}", score=1.0 if chk["passed"] else 0.0,
                                      comment=f"expected {chk.get('expected')}, got {chk.get('actual')}")
            c.update_project(exp.id, end_time=datetime.now(timezone.utc))
            url = f"{web_url(c)}/o/{exp.tenant_id}/datasets/{ds.id}/compare?selectedSessions={exp.id}"
        except AppError: raise
        except Exception as e:  # noqa: BLE001
            log.warning("sending suite %s to LangSmith failed: %s", sid, e)
            raise AppError("LANGSMITH_PUSH_FAILED", reason=type(e).__name__)
        self.tests.set_suite(sid, langsmith_url=url)
        return url

    def on_suite_done(self, sid: str) -> None:
        """A suite run ended: send it when the setting is on (failures are logged, the suite is unaffected)."""
        if not self.evals_enabled(): return
        try: self.push_suite(sid)
        except AppError as e: log.warning("suite %s not sent to LangSmith: %s", sid, e.code)

    def on_rating(self, turn_id: str) -> Optional[str]:
        """Send one chat rating to the run's LangSmith trace (DEC-0070).

        Returns "busy" when another worker is creating the feedback, so the caller can try again.
        A missing key, no trace, or a down LangSmith leaves the rating in the studio and does not raise.
        A failed create releases the claim. A second job updates the same feedback instead of creating one.
        """
        if not configured() or not tracing() or self.sessions is None: return None
        rating = self.sessions.rating(turn_id)
        if rating is None: return None
        turn = self.sessions.turn(turn_id)
        run = self.runs.get(turn.run_id) if turn is not None and turn.run_id else None
        if run is None or not run.trace_root: return None
        claim = self.sessions.claim_feedback(turn_id)
        if claim == "busy": return "busy"
        if claim == "gone": return None
        rating = self.sessions.rating(turn_id)
        if rating is None:
            if claim != "create": self._delete_feedback(claim)
            return None
        score = 1.0 if rating.value == "up" else 0.0
        comment = rating.comment or None
        try:
            c = client_factory()
            if claim == "create":
                fb = c.create_feedback(run_id_of(run.trace_root), "user_rating", score=score, comment=comment)
                fid = str(getattr(fb, "id", "") or "")
                if not fid:
                    self.sessions.release_feedback_claim(turn_id)
                    return None
                if self.sessions.rating(turn_id) is None:
                    self._delete_feedback(fid, c)
                    return None
                self.sessions.set_rating_feedback(turn_id, fid)
            else:
                fid = claim
                c.update_feedback(fid, score=score, comment=comment)
            latest = self.sessions.rating(turn_id)
            if latest is None:
                self._delete_feedback(fid, c)
                return None
            if latest.value != rating.value or (latest.comment or "") != (rating.comment or ""):
                c.update_feedback(fid, score=1.0 if latest.value == "up" else 0.0, comment=latest.comment or None)
        except Exception as e:  # noqa: BLE001
            if claim == "create": self.sessions.release_feedback_claim(turn_id)
            log.warning("rating %s not sent to LangSmith: %s", turn_id, type(e).__name__)
        return None

    def on_rating_removed(self, feedback_id: str) -> None:
        """Drop the LangSmith feedback after the studio rating is gone. No key means there is nothing to call."""
        if not feedback_id or feedback_is_pending(feedback_id) or not configured(): return
        self._delete_feedback(feedback_id)

    def _delete_feedback(self, feedback_id: str, client=None) -> None:
        try:
            (client or client_factory()).delete_feedback(feedback_id)
        except Exception as e:  # noqa: BLE001
            log.warning("rating feedback %s not deleted: %s", feedback_id, type(e).__name__)
