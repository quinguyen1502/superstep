"""Hand-offs in the exports (TASK-0183, REQ-0078, DEC-0073 decision 5): the Python file and the LangGraph project run
the same steps as the studio with the offline model, and the TypeScript file has the same nodes and routes."""
from app.engine import python_export as X, typescript_export as TS
from tests.test_agent_handoff_model import TOOL, desk
from tests.test_python_export import offline, same_run, unused_imports  # noqa: F401 (fixture)
from tests.test_typescript_export import deno_env  # noqa: F401 (fixture)

HS = [{"target": "billing", "description": "Duplicate charges and refunds"}, {"target": "tech", "description": "Crashes and bugs"}]


def help_desk(**top):
    wf = desk(HS, **top); wf["name"] = "Help desk"
    wf["nodes"][1]["data"].update(system_prompt="You triage questions.", tools=[{**TOOL, "description": "Find the status of an order"}])
    return wf


def test_python_hands_off_like_the_studio(tmp_path):
    out = same_run(tmp_path, help_desk(), {"message": "I want a refund for a duplicate charge"}, ignore=("answer",))  # built-in Python tools are stubs in TS
    code = out.code
    assert unused_imports(code) == set()
    assert out.names["triage/__handoff"] == "triage_handoff"
    assert '"transfer_to_billing"' in code and "MAX_HANDOFFS = 5" in code
    assert 'builder.add_conditional_edges("triage_model", route_triage_model, {"tool": "triage_tool", "done": "triage_end", "handoff": "triage_handoff"})' in code
    assert 'builder.add_conditional_edges("triage_handoff", route_triage_handoff, {"billing": "billing", "technical": "technical"})' in code
    assert "builder.add_conditional_edges(START, route_start, [" in code and "start_agent: str" in code


def test_python_without_a_hand_off_answers_in_triage(tmp_path):
    same_run(tmp_path, help_desk(), {"message": "Where is order B200?"})


def test_python_limit_zero_offers_no_transfer(tmp_path):
    out = same_run(tmp_path, help_desk(max_handoffs=0), {"message": "I want a refund for a duplicate charge"}, ignore=("answer",))  # built-in Python tools are stubs in TS
    assert "MAX_HANDOFFS = 0" in out.code


def test_python_starts_at_the_agent_a_chat_continues_with(tmp_path):
    from tests.test_python_export import exported
    code = X.to_python(help_desk(), "Help desk", 1, None, {"input": {"message": "and the invoice?", "start_agent": "billing"}}).code
    assert 'ROUTE_START_AGENTS = ["billing", "technical"]' in code
    names, final = exported(tmp_path, code)
    assert names[0] == "billing" and "triage" not in names and final["answer"]


def test_typescript_has_the_same_steps():
    code = TS.to_typescript(help_desk(), "Help desk", 1).code
    assert '"transfer_to_billing"' in code and "MAX_HANDOFFS = 5" in code
    assert ".addNode(\"triage_handoff\"" in code
    assert 'handoff: "triage_handoff"' in code and "routeStart" in code


def test_the_langgraph_project_hands_off(tmp_path, monkeypatch):
    import importlib.util, sys
    from tests.test_project_export import files
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    (tmp_path / "agent.py").write_text(files("python", help_desk(), title="Help desk")["agent.py"])
    spec = importlib.util.spec_from_file_location("handoff_agent", tmp_path / "agent.py")
    mod = importlib.util.module_from_spec(spec); sys.modules["handoff_agent"] = mod
    try:
        spec.loader.exec_module(mod)
        out = mod.graph.invoke({"message": "I want a refund for a duplicate charge"}, ignore=("answer",))  # built-in Python tools are stubs in TS
        assert out["agent_handoffs"] == 1 and out["answer"]
        again = mod.graph.invoke({"message": "and the invoice?", "start_agent": "billing"})
        assert again.get("agent_handoffs") is None and again["answer"]
    finally:
        sys.modules.pop("handoff_agent", None)


def test_typescript_type_checks_and_hands_off_like_the_studio(tmp_path, deno_env):
    from tests.test_typescript_export import same_run as ts_same_run
    ts_same_run(tmp_path, deno_env, help_desk(), {"message": "I want a refund for a duplicate charge"}, ignore=("answer",))  # built-in Python tools are stubs in TS
    ts_same_run(tmp_path, deno_env, help_desk(max_handoffs=0), {"message": "I want a refund for a duplicate charge"}, ignore=("answer",))  # built-in Python tools are stubs in TS


def test_exports_do_not_skip_the_nodes_before_the_first_agent():
    """Review finding 5 (TASK-0206): the exports mirror the engine; with a node between Start and the first agent there
    is no start router."""
    from tests.test_agent_handoff_engine import masked_desk
    wf = masked_desk()
    assert "route_start" not in X.to_python(wf, "Masked desk", 1, None).code
    assert "routeStart" not in TS.to_typescript(wf, "Masked desk", 1).code
