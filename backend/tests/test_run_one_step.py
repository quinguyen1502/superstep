"""one superstep, then pause. A second step or continue uses the same run. Not a human wait."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.engine.errors import ValidationError
from app.engine.runtime import run_stream
from app.main import app

c = TestClient(app)


def H(t): return {"Authorization": f"Bearer {t}"}
def n(i, t, **d): return {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}}
def e(s, t): return {"id": f"{s}-{t}", "source": s, "target": t}
def llm(i, out): return n(i, "llm", model="mock", prompt="Say {{state.message}}", output_field=out)
def finished(evs): return [x["node"] for x in evs if x["type"] == "node_finished"]


def linear():
    """Start → A → B → End."""
    return {"name": "line", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "nodes": [n("start", "start"), llm("a", "out"), llm("b", "out"), n("end", "end")],
            "edges": [e("start", "a"), e("a", "b"), e("b", "end")]}


def parallel():
    """Start splits to A and B, then End."""
    return {"name": "fan", "state": [{"name": "message", "type": "string"}, {"name": "out_a", "type": "string"}, {"name": "out_b", "type": "string"}],
            "nodes": [n("start", "start"), llm("a", "out_a"), llm("b", "out_b"), n("end", "end")],
            "edges": [e("start", "a"), e("start", "b"), e("a", "end"), e("b", "end")]}


def human():
    return {"name": "ask", "state": [{"name": "message", "type": "string"}, {"name": "decision", "type": "string"}],
            "nodes": [n("start", "start"), n("ask", "human", prompt="Approve {{state.message}}?", output_field="decision"), n("end", "end")],
            "edges": [e("start", "ask"), e("ask", "end")]}


def test_one_step_pauses_after_the_first_working_node():
    evs = list(run_stream(linear(), {"message": "hi"}, steps=1))
    assert finished(evs) == ["start", "a"]
    assert evs[-1]["type"] == "run_paused" and evs[-1]["nodes"] == ["b"]
    assert "run_finished" not in [x["type"] for x in evs]


def test_second_step_then_continue_finishes():
    first = list(run_stream(linear(), {"message": "hi"}, steps=1))
    second = list(run_stream(linear(), {}, resume=first[-1]["checkpoint"], steps=1))
    assert finished(second) == ["b"] and second[-1]["type"] == "run_paused" and second[-1]["nodes"] == ["end"]
    rest = list(run_stream(linear(), {}, resume=second[-1]["checkpoint"]))
    assert finished(rest) == ["end"] and rest[-1]["type"] == "run_finished"


def test_parallel_superstep_is_one_step():
    evs = list(run_stream(parallel(), {"message": "hi"}, steps=1))
    assert set(finished(evs)) == {"start", "a", "b"} and evs[-1]["type"] == "run_paused"
    assert "end" not in finished(evs)


def test_unlimited_run_still_finishes():
    evs = list(run_stream(linear(), {"message": "hi"}))
    assert finished(evs) == ["start", "a", "b", "end"] and evs[-1]["type"] == "run_finished"


def branched():
    """Start → condition. message yes goes to A, anything else to B. Both end."""
    return {"name": "branch", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "nodes": [n("start", "start"), n("route", "condition", field="message", default="no"), llm("a", "out"), llm("b", "out"), n("end", "end")],
            "edges": [e("start", "route"), {"id": "yes", "source": "route", "target": "a", "label": "yes"},
                      {"id": "no", "source": "route", "target": "b", "label": "no"}, e("a", "end"), e("b", "end")]}


def test_run_until_node_pauses_after_it():
    evs = list(run_stream(linear(), {"message": "hi"}, until="b"))
    assert finished(evs) == ["start", "a", "b"]
    assert evs[-1]["type"] == "run_paused" and evs[-1]["nodes"] == ["end"]


def test_run_until_from_a_pause():
    first = list(run_stream(linear(), {"message": "hi"}, steps=1))  # paused before b
    rest = list(run_stream(linear(), {}, resume=first[-1]["checkpoint"], until="b"))
    assert finished(rest) == ["b"] and rest[-1]["type"] == "run_paused" and rest[-1]["nodes"] == ["end"]


def test_run_until_a_missed_branch_reports_it():
    evs = list(run_stream(branched(), {"message": "yes"}, until="b"))
    assert "b" not in finished(evs) and "a" in finished(evs)
    assert evs[-1]["type"] == "error" and evs[-1]["error"]["code"] == "RUN_NODE_NOT_REACHED"
    assert evs[-1]["error"]["details"]["node"] == "b"


def test_unknown_until_node_is_rejected():
    with pytest.raises(ValidationError, match="missing"):
        list(run_stream(linear(), {"message": "hi"}, until="missing"))


def test_human_step_still_waits_for_a_person():
    evs = list(run_stream(human(), {"message": "hi"}, steps=1))
    assert evs[-1]["type"] == "run_waiting" and evs[-1]["node"] == "ask"


def ws(tok, msg):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in ("run_summary", "error"): return evs


def test_paused_run_is_not_an_approval_and_resumes():
    tok = c.post("/api/auth/register", json={"email": f"s{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
    wid = c.post("/api/workflows", json=linear(), headers=H(tok)).json()["data"]["id"]
    evs = ws(tok, {"workflow_id": wid, "input": {"message": "hi"}, "steps": 1})
    assert evs[-1]["status"] == "paused" and not any(x["type"] == "run_waiting" for x in evs)
    paused = next(x for x in evs if x["type"] == "run_paused")
    assert "checkpoint" not in paused and paused["node"] == "b"
    rid = evs[0]["run_id"]
    assert c.get("/api/runs/pending", headers=H(tok)).json()["data"] == []
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
    assert h["status"] == "paused" and h["id"] == rid
    again = ws(tok, {"resume_run_id": rid, "steps": 1})
    assert again[0]["type"] == "run_resumed" and "response" not in again[0] and again[-1]["status"] == "paused"
    done = ws(tok, {"resume_run_id": rid})
    assert done[-1]["status"] == "ok" and any(x["type"] == "run_finished" for x in done)
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
    assert h["status"] == "ok" and [x["type"] for x in h["events"]].count("run_paused") == 2


def test_run_until_over_the_socket_is_not_an_approval():
    tok = c.post("/api/auth/register", json={"email": f"u{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
    wid = c.post("/api/workflows", json=linear(), headers=H(tok)).json()["data"]["id"]
    evs = ws(tok, {"workflow_id": wid, "input": {"message": "hi"}, "until": "b"})
    assert evs[-1]["status"] == "paused" and finished(evs) == ["start", "a", "b"]
    assert c.get("/api/runs/pending", headers=H(tok)).json()["data"] == []
    missed = ws(tok, {"workflow_id": wid, "workflow": branched(), "input": {"message": "yes"}, "until": "b"})
    assert missed[-1]["type"] == "error" and missed[-1]["error"]["code"] == "RUN_NODE_NOT_REACHED"
    assert missed[-1]["error"]["details"]["node"] == "b"
