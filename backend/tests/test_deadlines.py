"""TASK-0066: Human node deadlines. Validation, reminders (at most 5), reject / approve / escalate on timeout, one
firing per reminder and deadline with several sweeps, all with an injected clock (no sleeping)."""
import json, threading, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service
from app.engine import deadlines as D, templates as T
from app.engine.validator import validate
from tests.test_hitl import APPROVAL

H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # lifespan: the worker that resumes timed-out runs


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    import app.services.approval_service as mod
    monkeypatch.setattr(mod, "BACKGROUND", False)


def user(c, email=None):
    d = c.post("/api/auth/register", json={"email": email or f"d{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def until(fn, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if v := fn(): return v
        time.sleep(0.05)
    raise AssertionError("timed out")


def graph(deadline, approvers=()):
    wf = json.loads(json.dumps(APPROVAL)); wf["name"] = f"Leave {uuid.uuid4().hex[:4]}"
    wf["nodes"][1]["data"]["approval"] = {"approvers": [a["email"] for a in approvers]}
    wf["nodes"][1]["data"]["deadline"] = deadline
    return wf


def waiting(c, owner, deadline, approvers=()):
    wid = c.post("/api/workflows", json=graph(deadline, approvers), headers=H(owner["token"])).json()["data"]["id"]
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"workflow_id": wid, "input": {"message": "3-5 March"}}); evs = []
        while (evs := evs + [w.receive_json()])[-1]["type"] != "run_summary": pass
    assert evs[-1]["status"] == "waiting"; rid = evs[0]["run_id"]
    return wid, rid, approval_service().repo.latest_wait(rid)


def run_row(c, owner, wid, rid): return next(r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(owner["token"])).json()["data"] if r["id"] == rid)
def audit(c, owner, rid): return [e["action"] for e in c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"] if e["run_id"] == rid][::-1]
def notes(c, u, kind): return [n for n in c.get("/api/notifications", headers=H(u["token"])).json()["data"]["items"] if n["kind"] == kind]
def fire(m, w):
    """Fire deadlines m minutes after the step started waiting, for this run only: waits left open by other tests of the
    same database would be due too and change the count."""
    svc = approval_service(); due = svc.repo.due_waits
    svc.repo.due_waits = lambda now, limit=200: [x for x in due(now, limit) if x.run_id == w.run_id]
    return svc.fire_deadlines(w.created + m * 60)


def test_durations_and_validation(monkeypatch):
    assert [D.seconds(v) for v in ("30m", "4h", "2d", " 1 h ", "0h", "4", "4w", 4, None)] == [1800, 14400, 172800, 3600, None, None, None, None, None]
    errs = lambda dl: [e for e in validate(graph(dl)) if "Human node ask" in e]  # noqa: E731
    assert errs({"after": "4h", "remind_every": "1h", "on_timeout": "reject"}) == [] and errs({}) == [] and errs({"after": ""}) == []
    assert errs({"after": "soon"}) == ["Human node ask: deadline must be a duration like 30m, 4h or 2d"]
    assert errs({"after": "1h", "remind_every": "1h"}) == ["Human node ask: reminders must come more often than the deadline"]
    assert errs({"after": "1h", "on_timeout": "escalate"}) == ["Human node ask: add who to escalate to"]
    assert errs({"after": "1h", "on_timeout": "escalate", "escalate_to": ["boss"]}) == ["Human node ask: escalate to needs e-mail addresses"]
    assert errs({"after": "1h", "on_timeout": "later"})[0].startswith("Human node ask: on timeout must be one of")
    monkeypatch.setenv("STUDIO_WAIT_TTL", str(3 * 86400))
    assert errs({"after": "2d"}) == [] and errs({"after": "4d"})[0].startswith("Human node ask: the deadline is longer than the wait limit")
    assert errs({"after": "2d", "on_timeout": "escalate", "escalate_to": ["a@x.io"]})  # escalation waits twice
    # a saved template keeps the timing, not the escalation addresses
    dl = {"after": "1d", "on_timeout": "escalate", "escalate_to": ["boss@example.com"]}
    assert T.sanitize(graph(dl))["nodes"][1]["data"]["deadline"] == {"after": "1d", "on_timeout": "escalate"}


def test_reminders_then_reject(c):
    owner, approver = user(c), user(c)
    wid, rid, w = waiting(c, owner, {"after": "2h", "remind_every": "30m", "on_timeout": "reject"}, [approver])
    assert w.due_at == pytest.approx(w.created + 7200) and w.next_remind_at == pytest.approx(w.created + 1800)
    assert [x["due_at"] for x in c.get("/api/approvals/inbox", headers=H(approver["token"])).json()["data"] if x["run_id"] == rid] == [w.due_at]
    assert fire(10, w) == 0
    assert fire(31, w) == 1 and fire(31, w) == 0  # claimed once
    assert len(notes(c, approver, "run_reminder")) == 1 and notes(c, owner, "run_reminder")[0]["link"] == "/approvals"
    assert fire(119, w) == 1  # missed reminders while down: one, and none after it since the deadline is near
    assert approval_service().repo.latest_wait(rid).next_remind_at is None
    assert fire(121, w) == 1 and fire(122, w) == 0
    done = until(lambda: (x := run_row(c, owner, wid, rid))["status"] == "ok" and x)
    assert done["final_state"]["decision"] == "rejected"
    assert next(e for e in done["events"] if e["type"] == "run_resumed")["by"] == {"channel": "deadline", "on_timeout": "reject"}
    assert audit(c, owner, rid) == ["reminded", "reminded", "timed_out"]
    assert c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(approver["token"])).json()["error"]["code"] == "APPROVAL_ALREADY_DECIDED"


def test_at_most_five_reminders_and_approve_on_timeout(c):
    owner = user(c)
    wid, rid, w = waiting(c, owner, {"after": "1d", "remind_every": "1h", "on_timeout": "approve"})
    assert sum(fire(m, w) for m in range(61, 23 * 60, 61)) == 5
    assert fire(24 * 60 + 1, w) == 1
    assert until(lambda: run_row(c, owner, wid, rid)["status"] == "ok")
    assert run_row(c, owner, wid, rid)["final_state"]["decision"] == "approved"


def test_escalate_once_then_reject(c):
    owner, first = user(c), user(c); boss = user(c)
    wid, rid, w = waiting(c, owner, {"after": "1h", "on_timeout": "escalate", "escalate_to": [boss["email"].upper(), "ghost@example.com"]}, [first])
    inbox = lambda u: [x for x in c.get("/api/approvals/inbox", headers=H(u["token"])).json()["data"] if x["run_id"] == rid]  # noqa: E731
    assert inbox(boss) == []
    assert fire(61, w) == 1
    [row] = inbox(boss); assert row["due_at"] == pytest.approx(w.created + 61 * 60 + 3600)
    assert inbox(first) and len(notes(c, boss, "run_escalated")) == 1 and run_row(c, owner, wid, rid)["status"] == "waiting"
    assert fire(62, w) == 0 and fire(61 + 61, w) == 1  # the second deadline rejects
    assert until(lambda: run_row(c, owner, wid, rid)["status"] == "ok")
    assert run_row(c, owner, wid, rid)["final_state"]["decision"] == "rejected"
    assert audit(c, owner, rid) == ["escalation_skipped", "escalated", "timed_out"]


def test_escalation_with_nobody_rejects_at_once(c):
    owner = user(c)
    wid, rid, w = waiting(c, owner, {"after": "1h", "on_timeout": "escalate", "escalate_to": ["nobody@example.com"]})
    assert fire(61, w) == 1 and until(lambda: run_row(c, owner, wid, rid)["status"] == "ok")
    assert run_row(c, owner, wid, rid)["final_state"]["decision"] == "rejected"
    assert audit(c, owner, rid) == ["escalation_skipped", "timed_out"]


def test_concurrent_sweeps_fire_once_and_answered_runs_never(c):
    owner = user(c)
    wid, rid, w = waiting(c, owner, {"after": "1h", "remind_every": "10m"})
    out = []; ts = [threading.Thread(target=lambda: out.append(fire(11, w))) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert sum(out) == 1 and audit(c, owner, rid).count("reminded") == 1
    c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(owner["token"]))
    assert fire(61, w) == 0 and fire(21, w) == 0  # answered: neither the deadline nor a reminder fires
    wid, rid, w = waiting(c, owner, {"after": "1h"})
    c.post(f"/api/runs/{rid}/cancel", headers=H(owner["token"]))
    assert fire(61, w) == 0


def test_late_sweep_leaves_a_later_step_alone(c, monkeypatch):
    """A sweep that read a step just before it was answered must not close the run's next step (same run, new pause)."""
    from app.models import ApprovalWait
    from app.repositories.approvals import ApprovalRepository
    owner = user(c)
    wid, rid, stale = waiting(c, owner, {"after": "1h"})
    svc = approval_service()
    svc.repo.close_wait(rid, "answered")  # answered, the run went on and paused again at another Human node
    later = svc.repo.add_wait(ApprovalWait(id=uuid.uuid4().hex[:12], run_id=rid, node_id="ask", owner=owner["id"], workflow_id=wid,
                                           status="waiting", created=time.time(), reminders=0), [])
    monkeypatch.setattr(ApprovalRepository, "due_waits", lambda self, now, limit=200: [stale])
    assert fire(61, stale) == 0
    assert svc.repo.latest_wait(rid).id == later.id and svc.repo.latest_wait(rid).status == "waiting"
    assert run_row(c, owner, wid, rid)["status"] == "waiting" and "timed_out" not in audit(c, owner, rid)
