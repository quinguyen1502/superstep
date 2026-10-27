"""The trace of a workflow tool call (TASK-0136, REQ-0073): the tool step names its child run, the run API returns that
run to people who may read it, and a chat's full view carries the child run too."""
import json
import pytest
from app.api.deps import run_service
from app.services.chat_session_service import steps_of
from tests.test_hitl import H, c, user
from tests.test_workflow_tool_runs import drain, llm, setup, specialist, start


@pytest.fixture(autouse=True)
def no_key(monkeypatch): monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_the_tool_step_names_its_child_and_the_run_api_returns_it():
    tok = user(); child_id, sup = setup(tok, specialist("Desk", llm()))
    rid, _ = start(tok, sup); drain()
    events = json.loads(run_service().runs.get(rid).events)
    step = [e for e in events if e.get("type") == "node_finished" and e["node"] == "ag/__tool/1"][-1]["agent"]
    cid = step["child_run_id"]
    assert step["child_workflow_id"] == child_id and step["status"] == "ok"
    d = c.get(f"/api/runs/{cid}", headers=H(tok)).json()
    assert d["success"] and d["data"]["id"] == cid and d["data"]["parent"]["run_id"] == rid
    assert any(e["type"] == "node_finished" and e["node"] == "x" for e in d["data"]["events"])
    other = user()
    r = c.get(f"/api/runs/{cid}", headers=H(other))
    assert r.status_code == 404 and r.json()["error"]["code"] == "RUN_NOT_FOUND"
    full = steps_of(events, "full"); labels = steps_of(events, "labels")
    assert next(s for s in full if s["node"] == "ag/__tool/1")["child_run_id"] == cid
    assert next(s for s in labels if s["node"] == "ag/__tool/1") == {"node": "ag/__tool/1", "label": "Supervisor › desk", "type": "agent_tool", "status": "ok"}
