"""Human node pauses a run (status waiting), pending list, owner-only resume, persistence across restarts."""
import json, uuid
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def user():
    return c.post("/api/auth/register", json={"email": f"h{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]

APPROVAL = {
    "name": "Approval", "state": [{"name": "message", "type": "string"}, {"name": "decision", "type": "string"}],
    "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
              {"id": "ask", "type": "human", "position": {"x": 0, "y": 0}, "data": {"label": "Manager approval", "prompt": "Approve refund for {{state.message}}?", "output_field": "decision"}},
              {"id": "route", "type": "condition", "position": {"x": 0, "y": 0}, "data": {"label": "Approved?", "field": "decision", "default": "rejected"}},
              {"id": "e", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
    "edges": [{"id": "1", "source": "s", "target": "ask"}, {"id": "2", "source": "ask", "target": "route"},
              {"id": "3", "source": "route", "target": "e", "label": "approved"}, {"id": "4", "source": "route", "target": "e", "label": "rejected"}]}


def ws(tok, msg, until=("run_summary",)):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in until or (evs[-1]["type"] == "error" and "run_id" not in evs[0]): return evs


def start(tok):
    wid = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]["id"]
    return wid, ws(tok, {"workflow_id": wid, "input": {"message": "order A100"}})


def test_validator_accepts_human_node():
    tok = user(); r = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]
    assert r["errors"] == []
    bad = json.loads(json.dumps(APPROVAL)); bad["nodes"][1]["data"]["output_field"] = ""
    assert any("output_field" in e for e in c.post("/api/validate", json=bad, headers=H(tok)).json()["data"]["errors"])


def test_pause_pending_resume_complete():
    tok = user(); wid, evs = start(tok)
    rid = evs[0]["run_id"]; waiting = next(e for e in evs if e["type"] == "run_waiting")
    assert waiting["node"] == "ask" and waiting["prompt"] == "Approve refund for order A100?" and "checkpoint" not in waiting
    assert evs[-1]["status"] == "waiting" and evs[-1]["trace_id"] is None
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]; assert h["status"] == "waiting"
    [p] = c.get("/api/runs/pending", headers=H(tok)).json()["data"]
    assert p["id"] == rid and p["workflow_name"] == "Approval" and p["label"] == "Manager approval" and p["prompt"].startswith("Approve")
    evs2 = ws(tok, {"resume_run_id": rid, "response": "approved"})
    assert evs2[0] == {**evs2[0], "type": "run_resumed", "run_id": rid, "node": "ask", "response": "approved"}
    fin = next(e for e in evs2 if e["type"] == "run_finished"); assert fin["state"]["decision"] == "approved"
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]  # still one run, one event log
    types = [e["type"] for e in h["events"]]
    assert h["status"] == "ok" and types[0] == "run_started" and "run_waiting" in types and "run_resumed" in types and types[-1] == "run_finished"
    assert c.get("/api/runs/pending", headers=H(tok)).json()["data"] == []
    again = ws(tok, {"resume_run_id": rid, "response": "approved"}, until=("error",))
    assert again[-1]["error"]["code"] == "RUN_NOT_WAITING"


def test_owner_only_resume_and_pending():
    tok = user(); _, evs = start(tok); rid = evs[0]["run_id"]; other = user()
    assert c.get("/api/runs/pending", headers=H(other)).json()["data"] == []
    r = ws(other, {"resume_run_id": rid, "response": "approved"}, until=("error",))
    assert r[-1]["error"]["code"] == "RUN_NOT_FOUND"
    assert c.post(f"/api/runs/{rid}/cancel", headers=H(other)).json()["error"]["code"] == "RUN_NOT_FOUND"


def test_response_validation_and_bool():
    tok = user(); _, evs = start(tok); rid = evs[0]["run_id"]
    bad = ws(tok, {"resume_run_id": rid, "response": {"x": 1}}, until=("error",))
    assert bad[-1]["error"]["code"] == "RUN_RESPONSE_INVALID"
    ok = ws(tok, {"resume_run_id": rid, "response": False})
    assert next(e for e in ok if e["type"] == "run_finished")["state"]["decision"] == "rejected"


def test_cancel_waiting_run():
    tok = user(); wid, evs = start(tok); rid = evs[0]["run_id"]
    assert c.post(f"/api/runs/{rid}/cancel", headers=H(tok)).json()["data"]["cancel_requested"] is True
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
    assert h["status"] == "cancelled" and h["events"][-1]["type"] == "run_cancelled"
    assert c.get("/api/runs/pending", headers=H(tok)).json()["data"] == []


def test_resume_survives_restart():
    """The checkpoint lives in the database: a fresh service (new process) resumes it."""
    import asyncio
    from app.api.deps import get_db
    from app.models.database import Database
    from app.repositories import RunRepository, WorkflowRepository
    from app.services.run_service import RunService
    tok = user(); _, evs = start(tok); rid = evs[0]["run_id"]
    uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    db = Database(get_db().url)  # new engine + sessions, nothing shared in memory
    svc = RunService(WorkflowRepository(db), RunRepository(db))
    plan = svc.plan(uid, {"resume_run_id": rid, "response": "approved"}); sent = []
    async def send(e): sent.append(e); return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.execute(plan, send, listen, uid)) == "ok"
    assert RunRepository(db).get(rid).status == "ok" and RunRepository(db).get(rid).checkpoint is None
