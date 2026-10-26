"""Approvals inside a workflow tool's child run are passed up (TASK-0135, REQ-0073, DEC-0066 decision 6), and the runs
API links parents and children."""
import json, uuid
import pytest
from app.api.deps import approval_service, run_service
from app.services.trigger_service import run_result
from tests.test_agent_workflow_tools import supervisor, tool
from tests.test_hitl import H, c, user, ws
from tests.test_workflow_tool_runs import drain, specialist


def human(): return {"id": "ask", "type": "human", "data": {"label": "Refund approval", "prompt": "Refund {{state.message}}?", "output_field": "answer"}}


@pytest.fixture(autouse=True)
def no_key(monkeypatch): monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def waiting_child(tok):
    """A supervisor whose specialist stops at a Human node: (parent run, child run, child name, parent name)."""
    cname, pname = f"Refund desk {uuid.uuid4().hex[:4]}", f"Support team {uuid.uuid4().hex[:4]}"
    child = c.post("/api/workflows", json={**specialist(cname, human()), "name": cname}, headers=H(tok)).json()["data"]["id"]
    sup = c.post("/api/workflows", json={**supervisor(tool(wid=child)), "name": pname}, headers=H(tok)).json()["data"]["id"]
    evs = ws(tok, {"workflow_id": sup, "input": {"message": "B200"}})
    rid = evs[0]["run_id"]; cid = next(e for e in evs if e["type"] == "run_waiting")["wait"]["run_id"]
    drain()  # the child runs and stops at its Human node
    return rid, cid, cname, pname, child, sup


@pytest.mark.parametrize("answer", ["approved", "rejected"])
def test_an_approval_in_a_child_is_answered_from_the_inbox(answer):
    tok = user(); rid, cid, cname, pname, *_ = waiting_child(tok)
    svc = run_service()
    assert svc.runs.get(cid).status == "waiting" and svc.runs.get(rid).status == "waiting"
    inbox = c.get("/api/approvals/inbox", headers=H(tok)).json()["data"]
    item = next(i for i in inbox if i["run_id"] == cid)
    assert item["workflow_name"] == f"{pname} › {cname}" and not any(i["run_id"] == rid for i in inbox)
    assert c.post(f"/api/approvals/inbox/{cid}", json={"response": answer}, headers=H(tok)).json()["success"]
    drain()  # the child's resume, then the parent's
    assert svc.runs.get(cid).status == "ok" and svc.runs.get(rid).status == "ok"
    step = json.loads(svc.runs.get(rid).final_state)["steps"][0]
    assert step["status"] == "ok" and json.loads(step["result"]) == {"answer": answer}


def test_a_deadline_that_ends_the_child_gives_the_parent_an_error():
    tok = user(); rid, cid, *_ = waiting_child(tok)
    svc = run_service(); svc._expire(svc.runs.get(cid))
    drain()
    parent = svc.runs.get(rid)
    step = json.loads(parent.final_state)["steps"][0]
    assert svc.runs.get(cid).status == "expired" and parent.status == "ok" and step["status"] == "error" and "expired" in step["result"]


def test_channel_messages_name_both_workflows():
    tok = user(); rid, cid, cname, pname, *_ = waiting_child(tok)
    assert approval_service().workflow_name(cid, run_service().runs.get(cid).workflow_id) == f"{pname} › {cname}"
    assert approval_service().workflow_name(rid, run_service().runs.get(rid).workflow_id) == pname


def test_runs_link_parents_and_children():
    tok = user(); rid, cid, cname, pname, child, sup = waiting_child(tok)
    parent_row = next(r for r in c.get(f"/api/workflows/{sup}/runs", headers=H(tok)).json()["data"] if r["id"] == rid)
    assert parent_row["waiting_for"] == {"run_id": cid, "workflow_id": child, "workflow_name": cname, "status": "waiting"}
    child_row = next(r for r in c.get(f"/api/workflows/{child}/runs", headers=H(tok)).json()["data"] if r["id"] == cid)
    assert child_row["parent"]["run_id"] == rid and child_row["parent"]["workflow_name"] == pname and child_row["source"] == "tool"
    svc = run_service()
    assert run_result(svc.runs.get(rid))["waiting"]["child_run_id"] == cid and run_result(svc.runs.get(cid))["parent_run_id"] == rid
    other = user()  # someone who cannot open the parent's workflow sees no name
    assert svc.links(svc.runs.get(cid), c.get("/api/me", headers=H(other)).json()["data"]["id"])["parent"]["workflow_name"] is None
    c.post(f"/api/runs/{rid}/cancel", headers=H(tok))
