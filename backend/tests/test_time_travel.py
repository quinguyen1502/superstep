"""Time travel: a run's checkpoints (read back from its events) and a new run forked from one, with its state or an
edited one; permissions and the error codes."""
from app.services import time_travel as TT
from tests.test_hitl import APPROVAL, H, c, user, ws


def finished(tok, answer="approved"):
    wid = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]["id"]
    rid = ws(tok, {"workflow_id": wid, "input": {"message": "order A100"}})[0]["run_id"]
    ws(tok, {"resume_run_id": rid, "response": answer}); return wid, rid


def test_checkpoints_group_a_superstep_and_end_with_the_final_state():
    evs = [{"type": "run_started"}, {"type": "node_finished", "node": "s", "node_type": "start", "input": {}},
           {"type": "node_finished", "node": "a", "label": "A", "node_type": "llm", "input": {"x": 1}, "iteration": 1},
           {"type": "node_finished", "node": "b", "node_type": "llm", "input": {"x": 1}, "iteration": 1},
           {"type": "node_finished", "node": "a", "node_type": "llm", "input": {"x": 2}, "iteration": 2},
           {"type": "node_finished", "node": "c", "node_type": "llm", "input": {"_truncated": True, "size": 9, "preview": "{"}, "iteration": 1}]
    cps = TT.checkpoints(evs, {"x": 3})
    assert [(c["nodes"], c["counts"], c["forkable"]) for c in cps] == [
        (["a", "b"], {}, True), (["a"], {"a": 1, "b": 1}, True), (["c"], {"a": 2, "b": 1}, False), ([], {"a": 2, "b": 1, "c": 1}, False)]
    assert cps[0]["labels"] == ["A", "b"] and cps[-1]["final"] and cps[-1]["state"] == {"x": 3}


def test_list_and_fork_with_an_edited_state():
    tok = user(); wid, rid = finished(tok)
    d = c.get(f"/api/runs/{rid}/checkpoints", headers=H(tok)).json()["data"]
    cps = d["checkpoints"]
    assert d["workflow_id"] == wid and [x["nodes"] for x in cps] == [["ask"], ["route"], []]
    assert cps[1]["state"] == {"message": "order A100", "decision": "approved"} and cps[2]["final"]
    # fork before "route" with the decision edited: a new run that starts there
    evs = ws(tok, {"fork": {"run_id": rid, "checkpoint": 1, "state": {**cps[1]["state"], "decision": "rejected"}}})
    assert evs[0]["type"] == "run_started" and evs[0]["run_id"] != rid
    assert evs[0]["forked_from"] == {"run_id": rid, "checkpoint": 1, "nodes": ["route"], "edited": True}
    ran = [e["node"] for e in evs if e["type"] == "node_finished"]
    assert "ask" not in ran and "route" in ran and evs[-1]["status"] == "ok"
    runs = {r["id"]: r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]}
    assert runs[evs[0]["run_id"]]["final_state"]["decision"] == "rejected" and runs[rid]["final_state"]["decision"] == "approved"
    # fork before the Human node, state unchanged: it asks again
    evs = ws(tok, {"fork": {"run_id": rid, "checkpoint": 0}}, until=("run_summary",))
    assert evs[0]["forked_from"]["edited"] is False and any(e["type"] == "run_waiting" for e in evs)


def test_fork_errors_and_permissions():
    tok = user(); _, rid = finished(tok); other = user()
    assert c.get(f"/api/runs/{rid}/checkpoints", headers=H(other)).json()["error"]["code"] == "RUN_NOT_FOUND"
    err = lambda t, f: next(e for e in ws(t, {"fork": f}, until=("run_summary", "error")) if e["type"] == "error")["error"]["code"]  # noqa: E731
    assert err(other, {"run_id": rid, "checkpoint": 0}) == "RUN_NOT_FOUND"
    assert err(tok, {"run_id": rid, "checkpoint": 2}) == "CHECKPOINT_NOT_FOUND"  # the final state is not a fork point
    assert err(tok, {"run_id": rid, "checkpoint": "0"}) == "CHECKPOINT_NOT_FOUND"
    assert err(tok, {"run_id": rid, "checkpoint": 1, "state": [1]}) == "RUN_INPUT_INVALID"
    assert err(tok, "x") == "RUN_REQUEST_INVALID"


def test_checkpoints_follow_the_superstep_numbers():
    """TASK-0123: nodes group by `superstep`, not by equal input state. A Condition leaves the state unchanged, so the
    node after it starts from the same state, yet runs in the next superstep; parallel nodes keep their superstep's state."""
    evs = [{"type": "node_finished", "node": "s", "node_type": "start", "input": {}, "superstep": 1},
           {"type": "node_finished", "node": "route", "node_type": "condition", "input": {"m": "go"}, "superstep": 2},
           {"type": "node_finished", "node": "yes", "node_type": "llm", "input": {"m": "go"}, "superstep": 3},
           {"type": "node_finished", "node": "a", "node_type": "llm", "input": {"m": "go", "y": 1}, "superstep": 4},
           {"type": "node_finished", "node": "b", "node_type": "llm", "input": {"m": "go", "y": 1, "a": 2}, "superstep": 4}]
    assert [(c["nodes"], c["state"]) for c in TT.checkpoints(evs)] == [
        (["route"], {"m": "go"}), (["yes"], {"m": "go"}), (["a", "b"], {"m": "go", "y": 1})]


ROUTED = {"name": "Routed", "state": [{"name": "message", "type": "string"}, {"name": "a", "type": "string"}, {"name": "b", "type": "string"}],
          "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
                    {"id": "route", "type": "condition", "position": {"x": 0, "y": 0}, "data": {"label": "Route", "field": "message", "default": "x"}},
                    {"id": "yes", "type": "llm", "position": {"x": 0, "y": 0}, "data": {"label": "Yes", "prompt": "Say yes", "output_field": "a"}},
                    {"id": "no", "type": "llm", "position": {"x": 0, "y": 0}, "data": {"label": "No", "prompt": "Say no", "output_field": "b"}},
                    {"id": "e", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
          "edges": [{"id": "1", "source": "s", "target": "route"}, {"id": "2", "source": "route", "target": "yes", "label": "go"},
                    {"id": "3", "source": "route", "target": "no", "label": "x"}, {"id": "4", "source": "yes", "target": "e"},
                    {"id": "5", "source": "no", "target": "e"}]}


def test_fork_before_a_condition_takes_one_branch():
    """TASK-0123: forking before a Condition with an edited state runs the Condition alone, then the branch it picks
    (it used to run the old branch alongside it, and End twice)."""
    tok = user(); wid = c.post("/api/workflows", json=ROUTED, headers=H(tok)).json()["data"]["id"]
    rid = ws(tok, {"workflow_id": wid, "input": {"message": "go"}})[0]["run_id"]
    cps = c.get(f"/api/runs/{rid}/checkpoints", headers=H(tok)).json()["data"]["checkpoints"]
    assert [x["nodes"] for x in cps] == [["route"], ["yes"], []]
    evs = ws(tok, {"fork": {"run_id": rid, "checkpoint": 0, "state": {"message": "nope"}}})
    assert [e["node"] for e in evs if e["type"] == "node_finished"] == ["route", "no", "e"] and evs[-1]["status"] == "ok"
