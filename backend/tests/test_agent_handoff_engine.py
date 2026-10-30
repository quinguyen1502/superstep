"""Agent hand-offs in the engine (TASK-0180, REQ-0078, DEC-0073 decisions 2 and 3): routing through `A/__handoff`, the
target's context, the run limit, a mixed round, a restart right after the hand-off, time travel and subgraphs."""
import json
from app.engine import agents
from app.engine.runtime import run_stream
from app.engine.validator import validate
from tests.test_agent_handoff_model import STATE, TOOL, desk
from tests.test_agent_node import call, final

STEPS = STATE + [{"name": "steps", "type": "list"}]


def script(monkeypatch, replies):
    """The model: each call returns the next (text, calls); records (agent's first user message, tool names, messages)."""
    seen, it = [], iter(replies)
    def fake(messages, tools, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None, **_):
        seen.append({"messages": json.loads(json.dumps(messages)), "tools": [t["name"] for t in tools or []]}); return next(it)
    monkeypatch.setattr(agents, "call_agent", fake)
    return seen


def to(name, reason="", cid="h1"): return call(name, {"reason": reason} if reason else {}, cid)
def ev(evs, node): return [e for e in evs if e["type"] == "node_finished" and e["node"] == node]


def test_triage_hands_off_and_billing_answers(monkeypatch):
    seen = script(monkeypatch, [("", [to("transfer_to_billing", "duplicate charge")]), ("Refund issued.", [])])
    evs = list(run_stream(desk(), {"message": "I was charged twice"}))
    assert final(evs)["answer"] == "Refund issued."
    assert "transfer_to_billing" in seen[0]["tools"] and "transfer_to_technical" in seen[0]["tools"]
    step = ev(evs, "triage/__handoff")[0]
    assert step["label"] == "Triage › hand-off"
    last = step["agent"]
    assert last["kind"] == "handoff" and last["to"] == "billing" and last["to_label"] == "Billing" and last["reason"] == "duplicate charge"
    # Billing gets the person's message and the note, no tool calls or results
    msgs = seen[1]["messages"]
    assert msgs[0]["role"] == "system" and "Triage" in msgs[0]["content"] and "duplicate charge" in msgs[0]["content"]
    assert all(m["role"] in ("system", "user", "assistant") and not m.get("tool_calls") for m in msgs)
    assert any(m["role"] == "user" and "charged twice" in m["content"] for m in msgs)
    assert not ev(evs, "triage/__exit") and ev(evs, "billing/__exit")   # the workflow goes on from Billing
    assert not any(k.startswith(agents.PREFIX) for k in final(evs))


def test_the_limit_removes_the_tools_and_the_run_answers(monkeypatch):
    wf = desk(max_handoffs=1)
    wf["nodes"][2]["data"]["handoffs"] = [{"target": "tech"}]
    seen = script(monkeypatch, [("", [to("transfer_to_billing")]), ("I will answer myself.", [])])
    evs = list(run_stream(wf, {"message": "charged"}))
    assert final(evs)["answer"] == "I will answer myself."
    assert "transfer_to_technical" not in seen[1]["tools"] and agents.NO_MORE in seen[1]["messages"][0]["content"]


def test_a_mixed_round_answers_the_other_calls_as_not_run(monkeypatch):
    wf = desk(); wf["nodes"][1]["data"]["steps_field"] = "steps"; wf["state"] = STEPS
    script(monkeypatch, [("", [call("lookup_order", {"message": "x"}, "a"), to("transfer_to_technical", "bug", "b")]), ("Fixed.", [])])
    looked = []
    monkeypatch.setattr("app.engine.agents.call_tool", lambda *a, **k: looked.append(1) or "found")
    evs = list(run_stream(wf, {"message": "app crashes"}))
    out = final(evs)
    assert out["answer"] == "Fixed." and looked == []
    assert [s["status"] for s in out["steps"]] == ["not_run", "handoff"] and out["steps"][0]["result"] == agents.NOT_RUN


def test_a_restart_right_after_the_hand_off_continues_at_the_target(monkeypatch):
    script(monkeypatch, [("", [to("transfer_to_billing", "charge")])])
    evs = list(run_stream(desk(), {"message": "charged"}, until="triage/__handoff"))
    paused = evs[-1]
    assert paused["type"] == "run_paused" and paused["nodes"] == ["billing"]
    seen = script(monkeypatch, [("Refund issued.", [])])   # Triage's model is not called again
    again = list(run_stream(desk(), {}, resume={"nodes": paused["nodes"], "state": paused["state"], "counts": paused.get("counts")}))
    assert final(again)["answer"] == "Refund issued." and len(seen) == 1 and not ev(again, "triage/__handoff")
    assert "charge" in seen[0]["messages"][0]["content"]


def test_time_travel_before_the_hand_off_can_lead_elsewhere(monkeypatch):
    script(monkeypatch, [("", [to("transfer_to_billing")]), ("Billing.", [])])
    evs = list(run_stream(desk(), {"message": "help"}, until="s"))   # back to the moment before Triage ran
    paused = evs[-1]
    script(monkeypatch, [("", [to("transfer_to_technical")]), ("Technical.", [])])
    again = list(run_stream(desk(), {}, resume={"nodes": paused["nodes"], "state": paused["state"], "counts": paused.get("counts")}))
    assert final(again)["answer"] == "Technical."


def test_targets_inside_a_subgraph_stay_inside(monkeypatch):
    from app.engine import subgraphs
    child = desk(); child["id"] = "child"
    parent = {"name": "p", "state": STATE, "nodes": [{"id": "s", "type": "start", "data": {}}, {"id": "sub", "type": "subgraph", "data": {"workflow_id": "child"}},
              {"id": "e", "type": "end", "data": {}}], "edges": [{"id": "1", "source": "s", "target": "sub"}, {"id": "2", "source": "sub", "target": "e"}]}
    flat = subgraphs.expand(parent, lambda ref: child if ref == "child" else None)
    tri = next(n for n in flat["nodes"] if n["id"] == "sub/triage")
    assert [h["target"] for h in tri["data"]["handoffs"]] == ["sub/billing", "sub/tech"] and validate(flat) == []
    script(monkeypatch, [("", [to("transfer_to_sub_billing")]), ("Billing in the subgraph.", [])])
    assert final(list(run_stream(flat, {"message": "x"})))["answer"] == "Billing in the subgraph."


def test_the_offline_mock_hands_off_by_the_target_description():
    wf = desk([{"target": "billing", "description": "Duplicate charges and refunds"}, {"target": "tech", "description": "Crashes and bugs"}])
    wf["nodes"][1]["data"]["tools"] = [{**TOOL, "description": "Find the status of an order"}]
    evs = list(run_stream(wf, {"message": "I want a refund for a duplicate charge"}))
    assert ev(evs, "triage/__handoff") and ev(evs, "billing/__exit") and final(evs)["answer"]
