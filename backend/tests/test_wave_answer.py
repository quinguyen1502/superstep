"""A studio answer names the question on screen (TASK-0158). It does not approve another tool in the same wave,
and two settles at once on SQLite both stick."""
import asyncio, json, threading, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.main import app
from app.api.deps import approval_service, run_service
from app.models import ApprovalRequest, ApprovalWait, Run
from app.models.database import Database
from app.repositories.runs import RunRepository

H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
A, B = "ag/__tool/1", "ag/__tool/2"


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client


def user(c):
    d = c.post("/api/auth/register", json={"email": f"w{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def waiting(uid):
    """A run paused on two refund approvals, each with an open inbox row and a pending channel button."""
    rid = uuid.uuid4().hex[:10]
    cp = {"node": A, "nodes": [A, B], "state": {}, "counts": {}, "workflow": {"nodes": [], "edges": [], "state": []},
          "waits": [{"node": A, "kind": "approval", "prompt": "Refund A?", "label": "Refund A", "tool": "send_refund", "arguments": {"order": "A"}},
                    {"node": B, "kind": "approval", "prompt": "Refund B?", "label": "Refund B", "tool": "send_refund", "arguments": {"order": "B"}}]}
    now = time.time()
    run_service().runs.add(Run(id=rid, workflow_id="adhoc", input="{}", events=json.dumps([
        {"type": "run_waiting", "node": A, "prompt": "Refund A?", "label": "Refund A", "tool": "send_refund"}]),
        status="waiting", started=now, ended=now, owner=uid, source="ui", checkpoint=json.dumps(cp)))
    approvals = approval_service()
    for node, prompt in ((A, "Refund A?"), (B, "Refund B?")):
        approvals.repo.add_wait(ApprovalWait(id=uuid.uuid4().hex[:12], run_id=rid, node_id=node, owner=uid, workflow_id="adhoc",
                                             label=prompt, prompt=prompt, channel="slack", status="waiting", created=now, reminders=0), [])
        approvals.repo.add_request(ApprovalRequest(id=uuid.uuid4().hex[:12], run_id=rid, node_id=node, owner=uid, workflow_id="adhoc",
                                                   channel_id="ch", kind="slack", target="C1", approvers="[]", nonce=uuid.uuid4().hex[:8],
                                                   expires=now + 3600, status="pending", created=now))
    return rid


def checkpoint(rid):
    return json.loads(run_service().runs.get(rid).checkpoint)


def test_an_unnamed_answer_does_not_approve_the_first_tool(c):
    uid = user(c)["id"]; rid = waiting(uid); svc = run_service()
    with pytest.raises(AppError) as e:
        svc.plan(uid, {"resume_run_id": rid, "response": "approved"})
    assert e.value.code == "RUN_NOT_WAITING"
    cp = checkpoint(rid)
    assert [w["node"] for w in cp["waits"]] == [A, B] and "answers" not in cp
    assert approval_service().repo.open_wait(rid, A) and approval_service().repo.open_wait(rid, B)
    assert {r.node_id for r in approval_service().repo.requests_for_run(rid, "pending")} == {A, B}


def test_the_panel_answers_the_slot_it_shows_and_the_next_question_follows(c):
    uid = user(c)["id"]; rid = waiting(uid); svc = run_service()
    plan = svc.plan(uid, {"resume_run_id": rid, "response": "approved", "node": A})
    assert plan.pending_wave and plan.pending_event["node"] == B and plan.pending_event["prompt"] == "Refund B?"
    assert "checkpoint" not in plan.pending_event
    cp = checkpoint(rid)
    assert cp["answers"] == {A: "approved"} and [w["node"] for w in cp["waits"]] == [B]
    assert approval_service().repo.open_wait(rid, A) is None and approval_service().repo.open_wait(rid, B)
    statuses = {r.node_id: r.status for r in approval_service().repo.requests_for_run(rid)}
    assert statuses == {A: "superseded", B: "pending"}
    sent = []

    async def send(ev):
        sent.append(ev); return True

    async def listen():
        await asyncio.sleep(3600)

    assert asyncio.run(svc.execute(plan, send, listen, uid)) == "waiting"
    assert sent[0]["type"] == "run_waiting" and sent[0]["node"] == B and sent[0]["prompt"] == "Refund B?"
    assert sent[1] == {**sent[1], "type": "run_summary", "status": "waiting", "run_id": rid}
    with pytest.raises(AppError) as e:  # the screen still saying A must not approve B
        svc.plan(uid, {"resume_run_id": rid, "response": "approved", "node": A})
    assert e.value.code == "RUN_NOT_WAITING" and checkpoint(rid)["answers"] == {A: "approved"}
    assert approval_service().repo.open_wait(rid, B)
    go = svc.plan(uid, {"resume_run_id": rid, "response": "rejected", "node": B})
    assert go.resume["answers"] == {A: "approved", B: "rejected"} and go.pending_wave is False
    assert approval_service().repo.open_wait(rid, B) is None
    assert {r.status for r in approval_service().repo.requests_for_run(rid)} == {"superseded"}


def test_the_inbox_answers_the_row_it_shows(c):
    u = user(c); rid = waiting(u["id"])
    r = c.post(f"/api/approvals/inbox/{rid}", json={"response": "rejected", "node": B}, headers=H(u["token"]))
    assert r.status_code == 200 and r.json()["data"] == {"run_id": rid, "response": "rejected"}
    assert approval_service().repo.open_wait(rid, B) is None and approval_service().repo.open_wait(rid, A)
    assert {x.node_id: x.status for x in approval_service().repo.requests_for_run(rid)}[B] == "superseded"


def test_sqlite_keeps_both_answers_when_two_settles_overlap(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/wave.db"); db.migrate()
    repo = RunRepository(db); rid = "wave"; now = time.time()
    cp = {"waits": [{"node": "a", "kind": "approval"}, {"node": "b", "kind": "approval"}], "answers": {}}
    repo.add(Run(id=rid, workflow_id="adhoc", input="{}", events="[]", status="waiting", started=now, ended=now, owner="u",
                 checkpoint=json.dumps(cp)))
    gate = threading.Barrier(2); seen = {"n": 0}; lock = threading.Lock()

    def settle(node, value):
        def apply(checkpoint):
            with lock:
                seen["n"] += 1; wait = seen["n"] <= 2
            if wait: gate.wait(timeout=5)
            hit = next(w for w in checkpoint["waits"] if w["node"] == node)
            checkpoint["answers"][node] = value
            checkpoint["waits"] = [w for w in checkpoint["waits"] if w is not hit]
            return node
        assert repo.update_waiting(rid, apply) == node

    threads = [threading.Thread(target=settle, args=("a", "approved")), threading.Thread(target=settle, args=("b", "rejected"))]
    for t in threads: t.start()
    for t in threads: t.join()
    saved = json.loads(repo.get(rid).checkpoint)
    assert saved["answers"] == {"a": "approved", "b": "rejected"} and saved["waits"] == [] and "_next_wait" not in saved
