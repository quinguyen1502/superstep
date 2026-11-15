import copy, os
os.environ.pop("OPENAI_API_KEY", None)
import tempfile
os.environ["STUDIO_DB"] = tempfile.mktemp(suffix=".db")
import pytest
from fastapi.testclient import TestClient
from app.engine.validator import validate
from app.engine.compiler import compile_workflow
from app.engine.runtime import run_stream
from app.engine.errors import ValidationError
from app.engine.examples import EXAMPLE
from app.main import app

def test_example_valid():
    assert validate(EXAMPLE) == []

def test_invalid_detected():
    wf = copy.deepcopy(EXAMPLE); wf["nodes"] = [n for n in wf["nodes"] if n["type"] != "start"]
    with pytest.raises(ValidationError): compile_workflow(wf)

def test_condition_label_required():
    wf = copy.deepcopy(EXAMPLE); wf["edges"][2].pop("label")
    assert any("label" in e for e in validate(wf))

def test_order_branch():
    out = compile_workflow(EXAMPLE).invoke({"message": "Where is my order A100?"})
    assert out["intent"] == "order_status" and "A100" in out["tool_result"] and out["answer"]

def test_general_branch():
    out = compile_workflow(EXAMPLE).invoke({"message": "What are your opening hours?"})
    assert out["intent"] == "general" and "tool_result" not in out

def test_stream_events():
    evs = list(run_stream(EXAMPLE, {"message": "order B200"}))
    fin = [e["node"] for e in evs if e["type"] == "node_finished"]
    assert fin == ["start", "classify", "route", "lookup", "reply_order", "end"]
    assert evs[-1]["type"] == "run_finished"

def test_ws_run_and_history():
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": "example", "input": {"message": "where is order C300"}})
        evs = []
        while True:
            try: evs.append(ws.receive_json())
            except Exception: break
            if evs[-1]["type"] in ("run_finished", "error"): break
    assert evs[-1]["type"] == "run_finished"
    assert "C300" in evs[-1]["state"]["tool_result"]
    import time; time.sleep(0.3)
    assert len(c.get("/api/workflows/example/runs", headers={"Authorization": f"Bearer {tok}"}).json()["data"]) >= 1
