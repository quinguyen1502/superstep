"""Workflow tools (TASK-0133, REQ-0073, DEC-0066): an Agent node lists another saved workflow as a tool. Settings and
their validation, the parameter schema from the child's state fields, the child snapshot taken when a run is planned,
cycle and depth checks across subgraphs and workflow tools, and dependents. Child runs: test_workflow_tool_runs.py."""
import uuid
from app.engine import agents, subgraphs
from app.engine.runtime import run_stream
from app.engine.validator import validate
from tests.test_hitl import H, c, user

STATE = [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}, {"name": "count", "type": "integer"},
         {"name": "steps", "type": "list"}]


def tool(wid="w-child", **d):
    return {"name": "desk", "description": "Questions about orders", "source": "workflow", "workflow_id": wid,
            "inputs": ["message"], "outputs": ["answer"], **d}


def supervisor(*tools, name="Support team"):
    return {"name": name, "state": STATE,
            "nodes": [{"id": "start", "type": "start", "data": {}},
                      {"id": "ag", "type": "agent", "data": {"label": "Supervisor", "prompt": "Help: {{state.message}}",
                                                             "output_field": "answer", "steps_field": "steps", "tools": list(tools)}},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "ag"}, {"id": "2", "source": "ag", "target": "end"}]}


def specialist(name="Order desk"):
    return {"name": name, "state": STATE,
            "nodes": [{"id": "start", "type": "start", "data": {}},
                      {"id": "x", "type": "llm", "data": {"label": "Reply", "prompt": "{{state.message}}", "output_field": "answer"}},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "x"}, {"id": "2", "source": "x", "target": "end"}]}


def codes(errs): return sorted(e.code for e in errs)


# ---- settings ---------------------------------------------------------------------------------

def test_settings_are_validated():
    assert validate(supervisor(tool())) == []
    assert codes(validate(supervisor(tool(wid="")))) == ["AGENT_TOOL_WORKFLOW"]
    assert codes(validate(supervisor(tool(outputs=[])))) == ["AGENT_TOOL_OUTPUTS"]
    assert codes(validate(supervisor(tool(inputs=["message", "message"])))) == ["AGENT_TOOL_INPUTS"]
    assert codes(validate(supervisor(tool(inputs="message", outputs=["answer", 3])))) == ["AGENT_TOOL_INPUTS", "AGENT_TOOL_OUTPUTS"]
    assert subgraphs.check(supervisor(tool(inputs="message")), {"w-child": specialist()}.get) == []  # reported once, above
    assert validate(supervisor(tool(inputs=[]))) == []  # a workflow that needs no input


def test_parameters_come_from_the_child_state():
    plain = agents.parameters(tool(inputs=["message", "count"]))
    assert plain == {"type": "object", "properties": {"message": {"type": "string"}, "count": {"type": "string"}}, "required": ["message", "count"]}
    typed = agents.parameters(tool(inputs=["message", "count"], snapshot=specialist()))
    assert typed["properties"]["count"] == {"type": "integer"} and typed["required"] == ["message", "count"]


# ---- references (no database) -----------------------------------------------------------------

def test_references_cycles_depth_and_fields():
    store = {"b": supervisor(tool(wid="c")), "c": specialist(), "imp": {**specialist(), "source": {"kind": "langgraph_import"}}}
    load = store.get
    assert subgraphs.check(supervisor(tool(wid="b")), load, "a") == []
    store["c"] = supervisor(tool(wid="a"))
    store["a"] = supervisor(tool(wid="b"))
    errs = subgraphs.check(store["a"], load, "a")
    assert codes(errs) == ["WORKFLOW_TOOL_CYCLE"] and errs[0].params["chain"] == "a → b → c → a"
    # a cycle closed by a subgraph node counts too
    store["c"] = {**specialist(), "nodes": specialist()["nodes"] + [{"id": "sub", "type": "subgraph", "data": {"workflow_id": "a"}}]}
    assert codes(subgraphs.check(store["a"], load, "a")) == ["SUBGRAPH_CYCLE"]
    assert codes(subgraphs.check(supervisor(tool(wid="nope")), load)) == ["WORKFLOW_TOOL_NOT_FOUND"]
    assert codes(subgraphs.check(supervisor(tool(wid="imp")), load)) == ["WORKFLOW_TOOL_IMPORTED"]
    bad = subgraphs.check(supervisor(tool(wid="leaf", inputs=["question"], outputs=["reply"])), {"leaf": specialist()}.get)
    assert codes(bad) == ["WORKFLOW_TOOL_INPUT_UNKNOWN", "WORKFLOW_TOOL_OUTPUT_UNKNOWN"]
    # six levels of workflow tools are one too many
    chain = {f"w{i}": supervisor(tool(wid=f"w{i + 1}")) for i in range(6)}; chain["w6"] = specialist()
    assert codes(subgraphs.check(chain["w0"], chain.get, "w0")) == ["WORKFLOW_TOOL_TOO_DEEP"]
    chain["w5"] = specialist()
    assert subgraphs.check(chain["w0"], chain.get, "w0") == []


def test_snapshot_copies_children_recursively():
    store = {"b": supervisor(tool(wid="c"), name="Refund desk"), "c": specialist()}
    wf = supervisor(tool(wid="b"))
    out = agents.snapshot(wf, store.get, "a", lambda ref, raw: {"b": 3, "c": 7}[ref])
    t = out["nodes"][1]["data"]["tools"][0]
    assert t["version"] == 3 and t["snapshot"]["name"] == "Refund desk"
    inner = t["snapshot"]["nodes"][1]["data"]["tools"][0]
    assert inner["version"] == 7 and inner["snapshot"]["nodes"][1]["type"] == "llm"
    assert "snapshot" not in wf["nodes"][1]["data"]["tools"][0]  # the input is left alone
    # a snapshot sent with the workflow is never run: planning drops it, also on an already expanded tool step
    forged = agents.expand(supervisor(tool(wid="b", snapshot=specialist("Forged"), version=99)))
    clean = agents.snapshot(forged, store.get, "a")
    for n in clean["nodes"]:
        for t in (n.get("data") or {}).get("tools") or []:
            assert (t.get("snapshot") or {}).get("name") in (None, "Refund desk") and t.get("version") is None
    x = agents.expand(out)
    data = {n["id"]: n["data"] for n in x["nodes"]}
    assert data["ag/__tool/1"]["tools"][0]["snapshot"]["nodes"]  # the tool step runs the child
    for nid in ("ag", "ag/__model", "ag/__exit"):  # the other steps keep only the child's state fields
        assert data[nid]["tools"][0]["snapshot"] == {"state": STATE}


def test_without_the_run_service_a_call_fails_clearly(monkeypatch):
    """The engine alone has no child runs (TASK-0134 binds them per run): the call is a failed tool call, and the run
    still answers."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evs = list(run_stream(supervisor(tool()), {"message": "Where is B200?"}))
    st = next(e for e in evs if e["type"] == "run_finished")["state"]
    assert st["steps"][0]["tool"] == "desk" and st["steps"][0]["status"] == "error"


# ---- through the API --------------------------------------------------------------------------

def save(tok, wf):
    d = c.post("/api/workflows", json=wf, headers=H(tok)).json()["data"]
    return d["id"], d


def test_save_plan_and_dependents():
    from app.api.deps import run_service
    tok = user(); uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    name = f"Order desk {uuid.uuid4().hex[:4]}"
    child, d = save(tok, specialist(name))
    sup, d = save(tok, supervisor(tool(wid=child)))
    assert d["errors"] == []
    # unknown fields and a missing workflow are reported in the UI language
    bad = c.post("/api/validate", json=supervisor(tool(wid=child, outputs=["reply"])), headers=H(tok)).json()["data"]
    assert [i["code"] for i in bad["issues"]] == ["WORKFLOW_TOOL_OUTPUT_UNKNOWN"]
    gone = c.post("/api/validate", json=supervisor(tool(wid=uuid.uuid4().hex)), headers=H(tok)).json()["data"]
    assert [i["code"] for i in gone["issues"]] == ["WORKFLOW_TOOL_NOT_FOUND"]
    # the child calling its supervisor back is a cycle
    _, r = save(tok, {**supervisor(tool(wid=sup), name=name), "id": child})
    assert [i["code"] for i in r["issues"]] == ["WORKFLOW_TOOL_CYCLE"]
    save(tok, {**specialist(name), "id": child})
    # a planned run carries the child's latest saved version
    plan = run_service().plan(uid, {"workflow_id": sup, "input": {"message": "hi"}})
    assert plan.invalid is None
    t = next(n for n in plan.workflow["nodes"] if n["id"] == "ag/__tool/1")["data"]["tools"][0]
    assert t["snapshot"]["nodes"][1]["type"] == "llm" and isinstance(t["version"], int)
    # a workflow used as a tool is in use
    r = c.delete(f"/api/workflows/{child}", headers=H(tok))
    assert r.status_code == 409 and r.json()["error"]["code"] == "WORKFLOW_IN_USE"
