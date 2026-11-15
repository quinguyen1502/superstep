"""the Approvals inbox. Waiting steps for every Human node, listing for owner / approver / stranger,
answers from the inbox, first answer wins across inbox and editor."""
import json, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service
from tests.test_hitl import APPROVAL

H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
code = lambda r: r.json()["error"]["code"]  # noqa: E731


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # lifespan: the worker that resumes inbox answers


def user(c):
    d = c.post("/api/auth/register", json={"email": f"i{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def until(fn, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if v := fn(): return v
        time.sleep(0.05)
    raise AssertionError("timed out")


def waiting(c, owner, approvers=()):
    """A studio-only Human node naming `approvers`, and a run waiting at it -> (workflow id, run id)."""
    wf = json.loads(json.dumps(APPROVAL)); wf["name"] = f"Refund {uuid.uuid4().hex[:4]}"
    wf["nodes"][1]["data"]["approval"] = {"approvers": [a["email"].upper() for a in approvers] + ["nobody@example.com"]}
    wid = c.post("/api/workflows", json=wf, headers=H(owner["token"])).json()["data"]["id"]
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"workflow_id": wid, "input": {"message": "order A100"}}); evs = []
        while (evs := evs + [w.receive_json()])[-1]["type"] != "run_summary": pass
    assert evs[-1]["status"] == "waiting"; return wid, evs[0]["run_id"]


def inbox(c, u): return [x for x in c.get("/api/approvals/inbox", headers=H(u["token"])).json()["data"]]
def row(c, u, rid): return next((x for x in inbox(c, u) if x["run_id"] == rid), None)
def run_row(c, owner, wid, rid): return next(r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(owner["token"])).json()["data"] if r["id"] == rid)


def test_inbox_lists_owner_and_approvers_only(c):
    owner, approver, stranger = user(c), user(c), user(c)
    wid, rid = waiting(c, owner, [approver])
    mine = row(c, owner, rid)
    assert mine == {**mine, "workflow_id": wid, "node": "ask", "label": "Manager approval", "prompt": "Approve refund for order A100?",
                    "channel": None, "mine": True, "owner_email": None, "can_open": True} and mine["workflow_name"].startswith("Refund")
    theirs = row(c, approver, rid)
    assert theirs["mine"] is False and theirs["owner_email"] == owner["email"] and theirs["can_open"] is False
    assert set(theirs) == set(mine)  # the request only: no state, input or trace
    assert row(c, stranger, rid) is None
    # the rest of the run stays the owner's
    assert c.get("/api/runs/pending", headers=H(approver["token"])).json()["data"] == []
    assert code(c.get(f"/api/workflows/{wid}/runs", headers=H(approver["token"]))) == "WORKFLOW_NOT_FOUND"
    assert code(c.post(f"/api/runs/{rid}/cancel", headers=H(approver["token"]))) == "RUN_NOT_FOUND"


def test_approver_answers_from_the_inbox(c):
    owner, approver, stranger = user(c), user(c), user(c)
    wid, rid = waiting(c, owner, [approver])
    assert code(c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(stranger["token"]))) == "RUN_NOT_FOUND"
    assert code(c.post(f"/api/approvals/inbox/{rid}", json={"response": 12}, headers=H(approver["token"]))) == "RUN_RESPONSE_INVALID"
    assert code(c.post("/api/approvals/inbox/nope", json={"response": "approved"}, headers=H(approver["token"]))) == "RUN_NOT_FOUND"
    r = c.post(f"/api/approvals/inbox/{rid}", json={"response": True}, headers=H(approver["token"])).json()["data"]
    assert r == {"run_id": rid, "response": "approved"}
    done = until(lambda: (x := run_row(c, owner, wid, rid))["status"] == "ok" and x)
    assert done["final_state"]["decision"] == "approved"
    assert next(e for e in done["events"] if e["type"] == "run_resumed")["by"] == {"channel": "studio", "user_id": approver["id"]}
    assert row(c, owner, rid) is None and row(c, approver, rid) is None
    again = c.post(f"/api/approvals/inbox/{rid}", json={"response": "rejected"}, headers=H(owner["token"]))
    assert code(again) == "APPROVAL_ALREADY_DECIDED"
    [e] = [e for e in c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"] if e["run_id"] == rid]
    assert (e["kind"], e["action"], e["actor"]) == ("studio", "approved", approver["email"])


def test_text_reply_from_the_inbox(c):
    owner = user(c); wid, rid = waiting(c, owner)
    c.post(f"/api/approvals/inbox/{rid}", json={"response": "Need the receipt first"}, headers=H(owner["token"]))
    done = until(lambda: (x := run_row(c, owner, wid, rid))["status"] == "ok" and x)
    assert done["final_state"]["decision"] == "Need the receipt first"
    assert [e["action"] for e in c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"] if e["run_id"] == rid] == ["answered"]


def test_first_answer_wins_between_editor_and_inbox(c):
    owner, approver = user(c), user(c)
    wid, rid = waiting(c, owner, [approver])
    assert approval_service().claim(rid) and not approval_service().claim(rid)  # someone answered: the step is closed
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:  # the editor loses, the run is untouched
        w.send_json({"resume_run_id": rid, "response": "approved"}); assert w.receive_json()["error"]["code"] == "RUN_NOT_WAITING"
    assert code(c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(approver["token"]))) == "APPROVAL_ALREADY_DECIDED"
    assert run_row(c, owner, wid, rid)["status"] == "waiting"
    # the editor answers first: the step leaves every inbox
    wid, rid = waiting(c, owner, [approver])
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"resume_run_id": rid, "response": "rejected"}); evs = []
        while (evs := evs + [w.receive_json()])[-1]["type"] != "run_summary": pass
    assert row(c, approver, rid) is None
    assert code(c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(approver["token"]))) == "APPROVAL_ALREADY_DECIDED"


def test_cancel_and_expiry_close_the_step(c, monkeypatch):
    owner, approver = user(c), user(c)
    wid, rid = waiting(c, owner, [approver])
    c.post(f"/api/runs/{rid}/cancel", headers=H(owner["token"]))
    assert row(c, approver, rid) is None and approval_service().repo.latest_wait(rid).outcome == "cancelled"
    wid, rid = waiting(c, owner, [approver])
    monkeypatch.setenv("STUDIO_WAIT_TTL", "60")
    with approval_service().repo.db.session() as s:  # waited two minutes
        from app.models import Run
        s.get(Run, rid).ended = time.time() - 120; s.commit()
    assert row(c, approver, rid) is None and approval_service().repo.latest_wait(rid).outcome == "expired"
    assert code(c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(approver["token"]))) == "APPROVAL_ALREADY_DECIDED"


def test_open_run_is_offered_to_an_admin_approver(c, monkeypatch):
    """An admin may read every run, so "Open run" shows for them; a plain approver gets the request only."""
    email = f"adm{uuid.uuid4().hex[:6]}@example.com"; monkeypatch.setenv("STUDIO_ADMIN_EMAILS", email)
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]; adm = {"token": d["token"], **d["user"]}
    owner, approver = user(c), user(c)
    _, rid = waiting(c, owner, [adm, approver])
    assert row(c, adm, rid)["can_open"] is True and row(c, approver, rid)["can_open"] is False
