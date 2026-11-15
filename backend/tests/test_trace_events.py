from app.engine.runtime import run_stream, cap_payload
from app.engine.examples import EXAMPLE

def test_finished_events_carry_input_type_iteration():
    evs = list(run_stream(EXAMPLE, {"message": "Where is my order A100?"}))
    fin = [e for e in evs if e["type"] == "node_finished"]
    cls = next(e for e in fin if e["node"] == "classify")
    assert cls["node_type"] == "llm" and cls["iteration"] == 1
    assert cls["input"] == {"message": "Where is my order A100?"} and "intent" in cls["delta"]
    lookup = next(e for e in fin if e["node"] == "lookup")
    assert lookup["input"]["intent"] == cls["delta"]["intent"]
    assert all(e.get("node_type") for e in evs if e["type"] == "node_started")
    assert evs[-1]["type"] == "run_finished"

def loop_wf():
    return {"name": "loop", "state": [{"name": "message", "type": "string"}, {"name": "intent", "type": "string"}],
            "nodes": [{"id": "s", "type": "start", "data": {"label": "Start"}},
                      {"id": "think", "type": "llm", "data": {"label": "Think", "model": "m", "prompt": "{{state.message}}", "output_field": "message"}},
                      {"id": "check", "type": "condition", "data": {"label": "Check", "field": "intent", "default": "again"}},
                      {"id": "e", "type": "end", "data": {"label": "End"}}],
            "edges": [{"id": "1", "source": "s", "target": "think"}, {"id": "2", "source": "think", "target": "check"},
                      {"id": "3", "source": "check", "target": "think", "label": "again"}, {"id": "4", "source": "check", "target": "e", "label": "done"}]}

def test_loop_iterations_and_error_attributed_to_node():
    evs = list(run_stream(loop_wf(), {"message": "hi"}))
    its = [e["iteration"] for e in evs if e["type"] == "node_finished" and e["node"] == "think"]
    assert its[:3] == [1, 2, 3] and len(its) <= 25 and len(evs) < 120
    err = evs[-1]
    assert err["type"] == "error" and "Recursion" in err["errors"][0] and err.get("node") and err["node_type"]

def test_cap_payload():
    assert cap_payload({"a": 1}) == {"a": 1}
    big = cap_payload({"a": "x" * 50_000}, limit=1000)
    assert big["_truncated"] and big["size"] > 50_000 and len(big["preview"]) == 1000
