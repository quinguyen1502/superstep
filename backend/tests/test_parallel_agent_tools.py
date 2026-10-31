"""Parallel tool calls of one Agent round (TASK-0157, REQ-0076, DEC-0069)."""
import threading, time
import respx
from app.core import config
from app.engine import agents, llm
from app.engine.effects import Effects
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.services.time_travel import checkpoints
from tests.test_agent_node import MCP, call, final, wf


def tool(name, schema=None):
    return {"name": name, "description": name, "source": "mcp", "server_id": "s", "tool": name,
            "parameters": schema or {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}}


def spans_of(sleeps):
    """mcp_call that sleeps `sleeps[name]` seconds and records (name, start, end) under a lock."""
    seen, lock = [], threading.Lock()
    def mcp(server, name, args):
        t0 = time.perf_counter()
        time.sleep(sleeps.get(name, 0.05))
        t1 = time.perf_counter()
        with lock: seen.append((name, t0, t1))
        return name
    return seen, mcp


def overlap(seen):
    starts, ends = [s for _, s, _ in seen], [e for _, _, e in seen]
    return max(starts) < min(ends)


def run(monkeypatch, calls, tools, sleeps, mcp=None, **data):
    seen_model = []
    def fake(messages, tools_, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None):
        seen_model.append(parallel)
        return next(calls)
    monkeypatch.setattr(agents, "call_agent", fake)
    spans, timed = spans_of(sleeps)
    evs = list(run_stream(wf(tools=tools, steps_field="steps", **data), {"message": "x"}, ports=Ports(mcp_call=mcp or timed)))
    return evs, spans, seen_model


def test_three_calls_overlap_and_keep_the_model_order(monkeypatch):
    # The three calls must be in flight together. A barrier proves it without timing: each call waits until all three
    # have started, so a serial wave would time out here. (Comparing start and end times failed under load: a stall of
    # the test process before the second and third worker threads started let the 50 ms call b end first; TASK-0191.)
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "4")
    tools = [tool("a"), tool("b"), tool("c")]
    together, inside, lock = threading.Barrier(3, timeout=30), [], threading.Lock()
    def mcp(server, name, args):
        with lock: inside.append(name)
        together.wait()  # BrokenBarrierError (the call fails) unless all three calls are running at once
        return name
    calls = iter([("", [call("a", {"n": 1}, "1"), call("b", {"n": 2}, "2"), call("c", {"n": 3}, "3")]), ("Done", [])])
    evs, _, _ = run(monkeypatch, calls, tools, {}, mcp=mcp)
    st = final(evs)
    assert sorted(inside) == ["a", "b", "c"] and not together.broken
    assert [s["tool"] for s in st["steps"]] == ["a", "b", "c"] and st["answer"] == "Done"  # the model's order
    assert [s["status"] for s in st["steps"]] == ["ok", "ok", "ok"]
    assert [s["result"] for s in st["steps"]] == ["a", "b", "c"]
    cps = checkpoints(evs)
    slots = {"ag/__tool/1", "ag/__tool/2", "ag/__tool/3"}
    wave = [cp for cp in cps if set(cp["nodes"]) == slots]
    joins = [cp for cp in cps if cp["nodes"] == ["ag/__join"]]
    assert len(wave) == 1 and joins and joins[0]["index"] > wave[0]["index"]
    assert not any(set(cp["nodes"]) < slots and set(cp["nodes"]) & slots for cp in cps)


def test_cap_two_never_runs_three_at_once(monkeypatch):
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "2")
    assert config.agent_parallel_tools() == 2
    tools = [tool("a"), tool("b"), tool("c")]
    calls = iter([("", [call("a", {"n": 1}, "1"), call("b", {"n": 2}, "2"), call("c", {"n": 3}, "3")]), ("Done", [])])
    evs, spans, _ = run(monkeypatch, calls, tools, {"a": 0.15, "b": 0.15, "c": 0.15})
    assert [s["tool"] for s in final(evs)["steps"]] == ["a", "b", "c"]
    third = min(s for name, s, _ in spans if name == "c")
    first_ends = [e for name, _, e in spans if name in ("a", "b")]
    assert third >= min(first_ends)
    assert sum(1 for e in evs if e.get("type") == "node_finished" and e.get("node") == "ag/__join") == 2


def test_a_failed_call_leaves_the_others(monkeypatch):
    tools = [tool("a"), tool("b"), tool("c")]
    def mcp(server, name, args):
        if name == "b": raise RuntimeError("down")
        return name
    def fake(messages, tools_, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None):
        return next(replies)
    replies = iter([("", [call("a", {"n": 1}, "1"), call("b", {"n": 2}, "2"), call("c", {"n": 3}, "3")]), ("Done", [])])
    monkeypatch.setattr(agents, "call_agent", fake)
    evs = list(run_stream(wf(tools=tools, steps_field="steps"), {"message": "x"}, ports=Ports(mcp_call=mcp)))
    steps = final(evs)["steps"]
    assert [s["status"] for s in steps] == ["ok", "error", "ok"] and "down" in steps[1]["result"] and final(evs)["answer"] == "Done"


def test_the_same_tool_twice_gets_two_keys(monkeypatch):
    class Ledger:
        def __init__(self): self.rows = {}
        def get(self, nid, it): return self.rows.get((nid, it), (None,))[0]
        def put(self, nid, it, delta, key): self.rows.setdefault((nid, it), (delta, key))
    led, ran = Ledger(), []
    def fake(messages, tools_, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None):
        return next(replies)
    replies = iter([("", [call("add", {"a": 1, "b": 1}, "1"), call("add", {"a": 1, "b": 1}, "2")]), ("Done", [])])
    monkeypatch.setattr(agents, "call_agent", fake)
    evs = list(run_stream(wf(tools=[MCP], steps_field="steps"), {"message": "x"},
                          ports=Ports(mcp_call=lambda s, t, a: ran.append(a) or 0), effects=Effects("r", ledger=led)))
    keys = [k for (nid, _), (_, k) in led.rows.items() if str(nid).startswith("ag/__tool/")]
    assert ran == [{"a": 1, "b": 1}, {"a": 1, "b": 1}] and len(set(keys)) == 2
    assert [s["tool"] for s in final(evs)["steps"]] == ["add", "add"]


def test_setting_off_is_sequential_even_when_the_model_returns_three(monkeypatch):
    tools = [tool("a"), tool("b"), tool("c")]
    calls = iter([("", [call("a", {"n": 1}, "1"), call("b", {"n": 2}, "2"), call("c", {"n": 3}, "3")]), ("Done", [])])
    evs, spans, seen = run(monkeypatch, calls, tools, {"a": 0.08, "b": 0.08, "c": 0.08}, parallel_tool_calls=False)
    ordered = sorted(spans, key=lambda s: s[1])
    assert all(ordered[i][1] >= ordered[i - 1][2] for i in range(1, len(ordered)))
    assert seen[0] is False and [s["tool"] for s in final(evs)["steps"]] == ["a", "b", "c"]
    assert not overlap(spans)


def test_parallel_cap_env(monkeypatch):
    monkeypatch.delenv("STUDIO_AGENT_PARALLEL_TOOLS", raising=False)
    assert config.agent_parallel_tools() == 4
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "nope")
    assert config.agent_parallel_tools() == 1
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "0")
    assert config.agent_parallel_tools() == 1
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "9")
    assert config.agent_parallel_tools() == 8


def test_mock_names_both_desks_and_a_question_still_picks_one():
    props = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}
    tools = [{"name": "order_desk", "description": "Questions about where an order is", "parameters": props},
             {"name": "refund_desk", "description": "Refund requests for an order that arrived broken or late", "parameters": props}]
    _, one = llm.mock_agent([{"role": "user", "content": "Where is my order B200?"}], tools, "m")
    assert [c["name"] for c in one] == ["order_desk"]
    _, both = llm.mock_agent([{"role": "user", "content": "Ask order_desk about A100 and refund_desk about B200"}], tools, "m")
    assert [c["id"] for c in both] == ["mock_call_1", "mock_call_2"] and [c["name"] for c in both] == ["order_desk", "refund_desk"]


@respx.mock
def test_openai_and_anthropic_are_asked_for_one_call_when_parallel_is_off():
    openai = respx.post("http://localhost:1234/v1/chat/completions").respond(json={
        "choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": []}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    llm.call_agent([{"role": "user", "content": "hi"}], [{"name": "add", "description": "", "parameters": {"type": "object"}}],
                   "m", {"provider": "lmstudio"}, parallel=False)
    assert json_body(openai)["parallel_tool_calls"] is False
    anthropic = respx.post("https://api.anthropic.com/v1/messages").respond(json={
        "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}})
    llm.call_agent([{"role": "user", "content": "hi"}], [{"name": "add", "description": "", "parameters": {"type": "object"}}],
                   "claude", {"provider": "anthropic", "api_key": "k"}, parallel=False)
    assert json_body(anthropic)["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}


def json_body(route):
    import json
    return json.loads(route.calls[0].request.content)
