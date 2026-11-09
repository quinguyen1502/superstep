"""parallel branches with reducers, Join (fan-in), subgraph nodes (inline expansion)."""
import copy, os, uuid
os.environ.pop("OPENAI_API_KEY", None)
import pytest
from fastapi.testclient import TestClient
from app.engine import subgraphs
from app.engine.compiler import compile_workflow
from app.engine.errors import ValidationError
from app.engine.reducers import apply
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.main import app


def n(i, t, **d): return {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}}
def e(s, t, **k): return {"id": f"{s}-{t}", "source": s, "target": t, **k}
def llm(i, out, prompt="Say {{state.message}}"): return n(i, "llm", model="mock", prompt=prompt, output_field=out)


def fan(reducer="append", join=True):
    """start -> a, b (parallel, a two steps long) -> join -> end"""
    nodes = [n("start", "start"), llm("a1", "notes"), llm("a2", "notes"), llm("b", "notes"), n("end", "end")]
    edges = [e("start", "a1"), e("start", "b"), e("a1", "a2")]
    if join: nodes.append(n("j", "join")); edges += [e("a2", "j"), e("b", "j"), e("j", "end")]
    else: edges += [e("a2", "end"), e("b", "end")]
    return {"name": "fan", "state": [{"name": "message", "type": "string"}, {"name": "notes", "type": "list", **({"reducer": reducer} if reducer else {})}],
            "nodes": nodes, "edges": edges}


def test_reducers():
    s = [{"name": "l", "type": "list", "reducer": "append"}, {"name": "d", "type": "object", "reducer": "merge"}, {"name": "c", "type": "number", "reducer": "add"}]
    out = apply({"l": [1], "d": {"a": 1}, "c": 1, "x": 1}, {"l": 2, "d": {"b": 2}, "c": 2.5, "x": 9}, s)
    assert out == {"l": [1, 2], "d": {"a": 1, "b": 2}, "c": 3.5, "x": 9}
    assert apply({}, {"l": [3, 4]}, s)["l"] == [3, 4]


def test_validation_rules():
    assert validate(fan()) == []
    assert any("give the field a reducer" in x for x in validate(fan(reducer=None)))  # b and a1 both write notes in one step
    bad = fan(); bad["state"][1]["type"] = "string"
    assert any("reducer 'append' needs type list" in x for x in validate(bad))
    bad = fan(); bad["state"][1]["reducer"] = "max"
    assert any("unknown reducer" in x for x in validate(bad))
    one = fan(); one["edges"] = [x for x in one["edges"] if x["source"] != "b"] + [e("b", "end")]
    assert any("Join node j: needs at least two" in x for x in validate(one))


def test_parallel_branches_merge_and_join_waits():
    evs = list(run_stream(fan(), {"message": "hi"}))
    fin = [x["node"] for x in evs if x["type"] == "node_finished"]
    assert set(fin[1:3]) == {"a1", "b"}  # same superstep
    assert fin.count("j") == 1 and fin.index("j") > fin.index("a2")  # the Join waited for the longer branch
    final = evs[-1]["state"]
    assert evs[-1]["type"] == "run_finished" and len(final["notes"]) == 3  # append reducer kept all three outputs
    assert compile_workflow(fan()).invoke({"message": "hi"})["notes"] == final["notes"]  # runtime tracking == LangGraph state


def test_without_join_the_end_runs_per_branch_but_values_still_merge():
    evs = list(run_stream(fan(join=False), {"message": "hi"}))
    assert len(evs[-1]["state"]["notes"]) == 3


CHILD = {"name": "child", "state": [{"name": "message", "type": "string"}, {"name": "summary", "type": "string"}],
         "nodes": [n("s", "start"), llm("sum", "summary", "Summarise {{state.message}}"), n("e", "end")], "edges": [e("s", "sum"), e("sum", "e")]}


def parent(ref):
    return {"name": "parent", "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}],
            "nodes": [n("start", "start"), n("sub", "subgraph", workflow_id=ref, label="Summary"), llm("reply", "answer", "Reply {{state.summary}}"), n("end", "end")],
            "edges": [e("start", "sub"), e("sub", "reply"), e("reply", "end")]}


def test_subgraph_expansion_runs_inner_nodes_with_events():
    wf = subgraphs.expand(parent("C"), {"C": CHILD}.get)
    assert {x["id"] for x in wf["nodes"]} >= {"sub", "sub/sum", "sub/__exit"}
    assert "summary" in {f["name"] for f in wf["state"]}  # child field added to the parent state
    evs = list(run_stream(wf, {"message": "a long text"}))
    fin = [x for x in evs if x["type"] == "node_finished"]
    assert [x["node"] for x in fin] == ["start", "sub", "sub/sum", "sub/__exit", "reply", "end"]
    assert next(x for x in fin if x["node"] == "sub/sum")["label"] == "Summary › sum"
    assert evs[-1]["state"]["summary"] and evs[-1]["state"]["answer"]


def test_subgraph_reference_errors():
    load = {"A": parent("B"), "B": parent("A"), "C": CHILD, "T": {**CHILD, "state": [{"name": "message", "type": "number"}]}}.get
    assert any("cycles are not allowed" in x for x in subgraphs.check(parent("B"), load, "A"))
    assert any("was not found" in x for x in subgraphs.check(parent("nope"), load))
    assert any("choose a workflow" in x for x in subgraphs.check(parent(""), load))
    with pytest.raises(ValidationError) as ex: subgraphs.expand(parent("T"), load)
    assert "state field message is number in the subgraph but string here" in ex.value.errors[0]
    deep = {f"W{i}": parent(f"W{i + 1}") for i in range(8)}
    assert any("deeper than" in x for x in subgraphs.check(parent("W0"), deep.get))


def test_nested_subgraphs_and_human_inside_pause_and_resume():
    inner = {"name": "inner", "state": [{"name": "message", "type": "string"}, {"name": "ok", "type": "string"}],
             "nodes": [n("s", "start"), n("ask", "human", prompt="OK?", output_field="ok"), n("e", "end")], "edges": [e("s", "ask"), e("ask", "e")]}
    mid = {"name": "mid", "state": [{"name": "message", "type": "string"}], "nodes": [n("s", "start"), n("in", "subgraph", workflow_id="I"), n("e", "end")],
           "edges": [e("s", "in"), e("in", "e")]}
    top = parent("M"); top["nodes"][2]["data"]["prompt"] = "Reply {{state.ok}}"
    wf = subgraphs.expand(top, {"M": mid, "I": inner}.get)
    evs = list(run_stream(wf, {"message": "x"}))
    wait = evs[-1]; assert wait["type"] == "run_waiting" and wait["node"] == "sub/in/ask"
    evs2 = list(run_stream(wf, {}, resume={**wait["checkpoint"], "value": "approved"}))
    assert evs2[-1]["type"] == "run_finished" and evs2[-1]["state"]["ok"] == "approved"


H = lambda t: {"Authorization": f"Bearer {t}"}


def test_api_save_reports_reference_errors_and_ws_runs_the_subgraph():
    c = TestClient(app); email = f"sg{uuid.uuid4().hex[:6]}@example.com"
    c.post("/api/auth/register", json={"email": email, "password": "secret123"})
    tok = c.post("/api/auth/login", json={"email": email, "password": "secret123"}).json()["data"]["token"]
    child = c.post("/api/workflows", json=CHILD, headers=H(tok)).json()["data"]
    assert child["errors"] == []
    p = c.post("/api/workflows", json=parent(child["id"]), headers=H(tok)).json()["data"]
    assert p["errors"] == []
    cyc = c.post("/api/workflows", json={**parent(p["id"]), "id": child["id"]}, headers=H(tok)).json()["data"]  # child now embeds parent
    assert any("cycles are not allowed" in x for x in cyc["errors"])
    c.post("/api/workflows", json={**CHILD, "id": child["id"]}, headers=H(tok))  # restore
    other = c.post("/api/workflows", json=parent("nope"), headers=H(tok)).json()["data"]
    assert any("was not found" in x for x in other["errors"])
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json({"workflow_id": p["id"], "input": {"message": "hello"}}); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in ("run_summary",): break
    assert "sub/sum" in [x.get("node") for x in evs if x["type"] == "node_finished"]
    with c.websocket_connect(f"/ws/run?token={tok}") as w:  # a missing reference fails the run with WORKFLOW_INVALID
        w.send_json({"workflow_id": other["id"], "input": {"message": "hello"}}); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in ("run_summary", "error") and evs[-1]["type"] == "error": break
    assert evs[-1]["error"]["code"] == "WORKFLOW_INVALID"
