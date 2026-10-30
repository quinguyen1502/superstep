"""Agent node (TASK-0116, REQ-0072, DEC-0063): expansion into model and tool steps, the four tool sources, the round
limit, the offline mock, the side-effect ledger per tool call, and tool calling through the providers."""
import http.server, json, threading
import pytest, respx
from app.engine import agents, llm
from app.engine.effects import Effects
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.validator import validate

STATE = [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"},
         {"name": "steps", "type": "list"}, {"name": "messages", "type": "list"}]
BUILTIN = {"name": "lookup_order", "description": "Find the status of an order", "source": "builtin", "function": "lookup_order"}
KB = {"name": "search_policy", "description": "Search the refund policy", "source": "knowledge", "knowledge_base_id": "kb1", "top_k": 2}
MCP = {"name": "add", "description": "Add two numbers", "source": "mcp", "server_id": "s1", "tool": "add",
       "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}


def wf(**d):
    data = {"label": "Helper", "prompt": "Help the customer: {{state.message}}", "output_field": "answer", "tools": [BUILTIN], **d}
    return {"name": "a", "state": STATE,
            "nodes": [{"id": "start", "type": "start", "data": {}}, {"id": "ag", "type": "agent", "data": data},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "ag"}, {"id": "2", "source": "ag", "target": "end"}]}


def final(evs): return next(e for e in evs if e["type"] == "run_finished")["state"]


def script(monkeypatch, replies):
    """Replace the model: each call returns the next (text, calls) and records (messages, tools)."""
    seen, it = [], iter(replies)
    def fake(messages, tools, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None):
        seen.append((json.loads(json.dumps(messages)), tools)); return next(it)
    monkeypatch.setattr(agents, "call_agent", fake)
    return seen


def call(name, args, cid="c1"): return {"id": cid, "name": name, "args": args}


# ---- validation and expansion -----------------------------------------------------------------

def test_validation():
    assert validate(wf()) == []
    bad = lambda **d: " | ".join(validate(wf(**d)))
    assert "task prompt is missing" in bad(prompt="")
    assert "at least one tool" in bad(tools=[])
    assert "two tools are named" in bad(tools=[BUILTIN, BUILTIN])
    assert "letters, digits" in bad(tools=[{**BUILTIN, "name": "has space"}])
    assert "max rounds must be 1-25" in bad(max_rounds=26) and "max rounds" in bad(max_rounds=0)
    assert "not registered" in bad(tools=[{**BUILTIN, "function": "nope"}])
    assert "choose an MCP server and tool" in bad(tools=[{**MCP, "tool": ""}])
    assert "choose a knowledge base" in bad(tools=[{**KB, "knowledge_base_id": ""}]) and "top_k" in bad(tools=[{**KB, "top_k": 50}])
    assert "URL is missing" in bad(tools=[{"name": "h", "source": "http", "url": ""}])
    assert "unknown source" in bad(tools=[{"name": "x", "source": "ftp"}])
    assert "must be a list field" in bad(steps_field="answer") and "not in the state" in bad(history_field="nope")
    assert "output_field is missing" in bad(output_field="")
    assert "state.zz" in bad(prompt="{{state.zz}}")
    # an HTTP tool's templates may read the model's arguments
    assert validate(wf(tools=[{"name": "h", "source": "http", "method": "GET", "url": "https://x.test/{{state.args.id}}"}])) == []


def test_steps_are_never_cached():
    """The node's cache applies to the entry step only: a cached tool step would skip the call on a run with the same
    state (TASK-0116 review fix)."""
    x = agents.expand(wf(cache_ttl=60, timeout=30, retry={"max_attempts": 2, "initial_interval": 1}))
    data = {n["id"]: n["data"] for n in x["nodes"]}
    slots = [k for k in data if k.startswith("ag/__tool/")]
    assert data["ag"]["cache_ttl"] == 60 and all("cache_ttl" not in data[k] for k in data if k != "ag")
    assert data["ag/__tool/1"]["timeout"] == 30 and data["ag/__model"]["retry"]["max_attempts"] == 2 and len(slots) == 8


def test_expansion_is_idempotent_and_leaves_the_input_alone():
    w = wf(); x = agents.expand(w)
    assert [n["id"] for n in w["nodes"]] == ["start", "ag", "end"]
    kinds = {n["id"]: n["type"] for n in x["nodes"]}
    assert kinds["ag/__tool/1"] == "agent_tool" and kinds["ag/__join"] == "agent_join" and agents.expand(x) == x
    assert {(e["source"], e["target"]) for e in x["edges"]} >= {("ag", "ag/__model"), ("ag/__tool/1", "ag/__join"), ("ag/__join", "ag/__model"), ("ag/__exit", "end")}
    assert validate(x) == []


# ---- runs -------------------------------------------------------------------------------------

def test_mock_calls_a_tool_then_answers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evs = list(run_stream(wf(steps_field="steps"), {"message": "Where is order B200?"}))
    st = final(evs)
    assert "In transit" in st["answer"] and st["answer"].startswith("[mock:")
    assert st["steps"][0]["tool"] == "lookup_order" and st["steps"][0]["status"] == "ok"
    assert not any(k.startswith(agents.PREFIX) for k in st)
    done = [e for e in evs if e["type"] == "node_finished"]
    assert [e["node"] for e in done] == ["start", "ag", "ag/__model", "ag/__tool/1", "ag/__join", "ag/__model", "ag/__exit", "end"]
    tool = next(e for e in done if e["node"] == "ag/__tool/1")
    assert tool["agent"]["kind"] == "tool" and tool["label"] == "Helper › tool" and agents.PREFIX + "ag" not in tool["delta"]
    assert any(e["type"] == "node_token" and e["node"] == "ag/__model" for e in evs)  # the answer streams


def test_history_and_system_prompt_come_first(monkeypatch):
    seen = script(monkeypatch, [("Hi again", [])])
    hist = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}, {"role": "tool", "content": "x"}]
    list(run_stream(wf(system_prompt="Be brief", history_field="messages"), {"message": "Thanks", "messages": hist}))
    assert [m["role"] for m in seen[0][0]] == ["system", "user", "assistant", "user"] and seen[0][0][-1]["content"].endswith("Thanks")


def test_four_tool_sources(monkeypatch):
    got = {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); got["key"] = self.headers.get("Idempotency-Key")
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"refund": "sent"}')
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("STUDIO_HTTP_TOOL_ALLOW_PRIVATE", "1")
    http_tool = {"name": "send_refund", "source": "http", "method": "POST", "url": f"http://127.0.0.1:{srv.server_port}/refund",
                 "parameters": {"type": "object", "properties": {"order": {"type": "string"}}, "required": ["order"]}}
    seen = script(monkeypatch, [("", [call("lookup_order", {"message": "A100"}, "1"), call("search_policy", {"query": "refund"}, "2"),
                                      call("add", {"a": 2, "b": 3}, "3"), call("send_refund", {"order": "A100"}, "4")]), ("Done", [])])
    ports = Ports(mcp_call=lambda s, t, a: {"sum": a["a"] + a["b"]}, retrieve=lambda kb, q, k: [{"text": f"{kb}:{q}:{k}"}])
    evs = list(run_stream(wf(tools=[BUILTIN, KB, MCP, http_tool], steps_field="steps"), {"message": "x"}, ports=ports, effects=Effects("r1")))
    srv.shutdown()
    st = final(evs); results = [s["result"] for s in st["steps"]]
    assert st["answer"] == "Done" and [s["status"] for s in st["steps"]] == ["ok"] * 4
    assert "Delivered" in results[0] and "kb1:refund:2" in results[1] and '"sum": 5' in results[2] and "sent" in results[3]
    assert got["body"] == {"order": "A100"} and got["key"].startswith("studio-")
    assert [t["name"] for t in seen[0][1]] == ["lookup_order", "search_policy", "add", "send_refund"]
    tool_msgs = [m for m in seen[1][0] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["1", "2", "3", "4"]


def test_bad_calls_are_never_executed(monkeypatch):
    ran = []
    ports = Ports(mcp_call=lambda s, t, a: ran.append(a) or 1)
    script(monkeypatch, [("", [call("nope", {}, "1"), call("add", {"a": "two", "b": 1}, "2"), call("add", {"a": 1}, "3"), call("add", "x", "4")]),
                         ("ok", [])])
    st = final(list(run_stream(wf(tools=[MCP], steps_field="steps"), {"message": "x"}, ports=ports)))
    assert ran == [] and [s["status"] for s in st["steps"]] == ["error"] * 4
    r = [s["result"] for s in st["steps"]]
    assert "Unknown tool nope" in r[0] and "argument a must be of type integer" in r[1] and "missing argument(s): b" in r[2] and "JSON object" in r[3]


def test_a_failing_tool_goes_back_to_the_model(monkeypatch):
    def boom(s, t, a): raise RuntimeError("server down")
    seen = script(monkeypatch, [("", [call("add", {"a": 1, "b": 2})]), ("Sorry, the tool is down", [])])
    st = final(list(run_stream(wf(tools=[MCP]), {"message": "x"}, ports=Ports(mcp_call=boom))))
    assert st["answer"] == "Sorry, the tool is down" and "server down" in seen[1][0][-1]["content"]


def test_too_many_calls_in_one_round_are_refused(monkeypatch):
    ran = []
    calls = [call("add", {"a": i, "b": 0}, str(i)) for i in range(agents.MAX_CALLS_PER_ROUND + 2)]
    seen = script(monkeypatch, [("", calls), ("ok", [])])
    st = final(list(run_stream(wf(tools=[MCP], steps_field="steps"), {"message": "x"}, ports=Ports(mcp_call=lambda s, t, a: ran.append(a["a"]) or 0))))
    assert sorted(ran) == list(range(agents.MAX_CALLS_PER_ROUND)) and sum(s["status"] == "refused" for s in st["steps"]) == 2
    assert len([m for m in seen[1][0] if m["role"] == "tool"]) == len(calls)  # every call has an answer


def test_round_limit_asks_for_an_answer_without_tools(monkeypatch):
    loop = [("", [call("add", {"a": 1, "b": 1}, f"c{i}")]) for i in range(25)]
    seen = script(monkeypatch, loop + [("Final answer", [])])
    evs = list(run_stream(wf(tools=[MCP], max_rounds=25), {"message": "x"}, ports=Ports(mcp_call=lambda s, t, a: 2)))
    assert final(evs)["answer"] == "Final answer"  # 25 rounds fit the step budget (more than STUDIO_RECURSION_LIMIT)
    assert all(tools for _, tools in seen[:25]) and seen[25][1] is None
    last = [e for e in evs if e["type"] == "node_finished" and e["node"] == "ag/__model"][-1]
    assert last["agent"]["limit_hit"] is True


def test_each_tool_call_is_its_own_ledger_entry(monkeypatch):
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "4")  # the wave checkpoint lists every slot
    class DictLedger:
        def __init__(self): self.rows = {}
        def get(self, nid, it): return self.rows.get((nid, it), (None,))[0]
        def put(self, nid, it, delta, key): self.rows.setdefault((nid, it), (delta, key))
    ran, led = [], DictLedger()
    replies = [("", [call("add", {"a": 1, "b": 1}, "1"), call("add", {"a": 2, "b": 2}, "2")]), ("Done", [])]
    script(monkeypatch, replies)
    evs = list(run_stream(wf(tools=[MCP]), {"message": "x"}, ports=Ports(mcp_call=lambda s, t, a: ran.append(a["a"]) or 0), effects=Effects("r2", ledger=led)))
    keys = {k for (nid, _), (_, k) in led.rows.items() if str(nid).startswith("ag/__tool/")}
    assert sorted(ran) == [1, 2] and len(keys) == 2  # one idempotency key per tool call, even in one wave
    # resumed from the checkpoint before the wave: both calls come back from the ledger
    cp = next(e for e in evs if e["type"] == "_checkpoint" and set(e["nodes"]) == {"ag/__tool/1", "ag/__tool/2"})
    script(monkeypatch, replies[1:])
    evs2 = list(run_stream(wf(tools=[MCP]), {}, resume={"node": cp["node"], "nodes": cp["nodes"], "state": cp["state"], "counts": cp["counts"]},
                           ports=Ports(mcp_call=lambda s, t, a: ran.append(a["a"]) or 0), effects=Effects("r2", ledger=led)))
    assert final(evs2)["answer"] == "Done" and sorted(ran) == [1, 2]
    assert [e.get("reused") for e in evs2 if e["type"] == "node_finished" and e.get("node_type") == "agent_tool"] == [True, True]


def test_provider_without_tool_calling(monkeypatch):
    evs = list(run_stream(wf(credential_id="c1"), {"message": "x"}, resolve=lambda cid: {"provider": "typesafe", "api_key": "k"}))
    err = next(e for e in evs if e["type"] == "error")
    assert err["code"] == "AGENT_TOOLS_UNSUPPORTED" and err["node"] == "ag/__model"


# ---- providers --------------------------------------------------------------------------------

TOOLS = [{"name": "add", "description": "Add", "parameters": MCP["parameters"]}]
MSGS = [{"role": "system", "content": "Be brief"}, {"role": "user", "content": "2+3?"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "name": "add", "args": {"a": 2, "b": 3}}]},
        {"role": "tool", "tool_call_id": "t1", "name": "add", "content": "5"}]


@respx.mock
def test_openai_compatible_tool_calls():
    route = respx.post("http://localhost:1234/v1/chat/completions").respond(json={
        "id": "x", "object": "chat.completion", "created": 1, "model": "m",
        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "t2", "type": "function", "function": {"name": "add", "arguments": "{\"a\": 5, \"b\": 1}"}}]}}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13}})
    usage = []
    out, calls = llm.call_agent(MSGS, TOOLS, "m", {"provider": "lmstudio"}, usage.append)
    body = json.loads(route.calls[0].request.content)
    assert calls == [{"id": "t2", "name": "add", "args": {"a": 5, "b": 1}}] and out == ""
    assert body["tools"][0]["function"]["name"] == "add" and [m["role"] for m in body["messages"]] == ["system", "user", "assistant", "tool"]
    assert body["messages"][3]["tool_call_id"] == "t1" and usage[0]["tokens_in"] == 9


@respx.mock
def test_openai_compatible_streams_tool_calls():
    rows = [{"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": "t3", "type": "function",
                                                                                    "function": {"name": "add", "arguments": "{\"a\": 1,"}}]}}]},
            {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": " \"b\": 2}"}}]}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]
    sse = "".join(f"data: {json.dumps({'id': 'x', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'm', **r})}\n\n" for r in rows) + "data: [DONE]\n\n"
    respx.post("http://localhost:1234/v1/chat/completions").respond(text=sse, headers={"content-type": "text/event-stream"})
    got = []
    out, calls = llm.call_agent(MSGS[:2], TOOLS, "m", {"provider": "lmstudio"}, None, got.append)
    assert calls == [{"id": "t3", "name": "add", "args": {"a": 1, "b": 2}}] and out == "" and got == []


@respx.mock
def test_anthropic_tool_use_over_http():
    route = respx.post("https://api.anthropic.com/v1/messages").respond(json={
        "model": "claude-x", "content": [{"type": "text", "text": "Adding."}, {"type": "tool_use", "id": "tu1", "name": "add", "input": {"a": 1, "b": 2}}],
        "usage": {"input_tokens": 7, "output_tokens": 3}})
    usage = []
    out, calls = llm.call_agent(MSGS, TOOLS, "claude-x", {"provider": "anthropic", "api_key": "k"}, usage.append)
    body = json.loads(route.calls[0].request.content)
    assert out == "Adding." and calls == [{"id": "tu1", "name": "add", "args": {"a": 1, "b": 2}}] and usage[0]["tokens_out"] == 3
    assert body["system"] == "Be brief" and body["tools"][0]["input_schema"]["required"] == ["a", "b"]
    assert body["messages"][1]["content"][0] == {"type": "tool_use", "id": "t1", "name": "add", "input": {"a": 2, "b": 3}}
    assert body["messages"][2] == {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "5"}]}


def test_mock_agent_picks_the_closest_tool():
    tools = [{"name": "add", "description": "Add numbers", "parameters": MCP["parameters"]},
             {"name": "search_policy", "description": "Search the refund policy", "parameters": agents.QUERY}]
    out, calls = llm.mock_agent([{"role": "user", "content": "Can I get a refund?"}], tools, "m")
    assert out == "" and calls[0]["name"] == "search_policy" and calls[0]["args"] == {"query": "Can I get a refund?"}
    out, calls = llm.mock_agent([{"role": "user", "content": "hello"}], tools, "m")
    assert calls[0]["name"] == "add" and calls[0]["args"] == {"a": 0, "b": 0}  # no shared word: the first tool
    out, calls = llm.mock_agent([{"role": "user", "content": "x"}, {"role": "tool", "content": "42"}], tools, "m", "vi")
    assert calls == [] and out == "[mock:m] Trả lời: 42"


def test_model_arguments_are_never_rendered_as_templates(monkeypatch):
    sent = []
    monkeypatch.setattr("app.engine.nodes.http_send", lambda nid, method, url, body, extra: sent.append((method, url, body)) or "ok")
    post = {"name": "post", "source": "http", "method": "POST", "url": "https://x.test/p"}
    get = {"name": "get", "source": "http", "method": "GET", "url": "https://x.test/g?q={{state.args.q}}&m={{state.message}}"}
    evil = "{{state.message}}"
    script(monkeypatch, [("", [call("post", {"note": evil}, "1"), call("get", {"q": evil}, "2")]), ("ok", [])])
    list(run_stream(wf(tools=[post, get]), {"message": "secret"}))
    by = {m: (u, b) for m, u, b in sent}  # the two calls of the round run together, so finish order is not the model's order
    assert by["POST"] == ("https://x.test/p", '{"note": "{{state.message}}"}')
    assert by["GET"] == ("https://x.test/g?q={{state.message}}&m=secret", "")  # the builder's template is rendered once


def test_type_lists_in_schemas_are_accepted():
    schema = {"type": "object", "properties": {"a": {"type": ["string", "null"]}, "b": {"type": "integer"}}}
    assert agents.arg_error(schema, {"a": None, "b": 1}) is None and "b must be of type integer" in agents.arg_error(schema, {"b": "x"})


def test_run_until_the_agent_runs_the_whole_agent(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evs = list(run_stream(wf(), {"message": "Where is A100?"}, until="ag"))
    assert evs[-1]["type"] == "run_paused" and evs[-1]["node"] == "end" and "Delivered" in evs[-1]["state"]["answer"]


def test_saved_workflow_run_and_fork_inside_the_loop(monkeypatch):
    """Through the run service: the stored run, its checkpoints, and a fork at the tool step that does not call the model
    again before the tool runs."""
    from tests.test_hitl import H, c, user, ws
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    tok = user(); w = wf(steps_field="steps")
    wid = c.post("/api/workflows", json=w, headers=H(tok)).json()["data"]["id"]
    evs = ws(tok, {"workflow_id": wid, "input": {"message": "Where is order B200?"}}, until=("run_summary",))
    rid = evs[0]["run_id"]
    assert next(e for e in evs if e["type"] == "run_finished")["state"]["steps"][0]["tool"] == "lookup_order"
    cps = c.get(f"/api/runs/{rid}/checkpoints", headers=H(tok)).json()["data"]["checkpoints"]
    at = next(cp for cp in cps if cp["nodes"] == ["ag/__tool/1"])
    assert at["forkable"] and at["labels"] == ["Helper › tool"]
    evs = ws(tok, {"fork": {"run_id": rid, "checkpoint": at["index"]}}, until=("run_summary",))
    ran = [e["node"] for e in evs if e["type"] == "node_finished"]
    assert ran[:3] == ["ag/__tool/1", "ag/__join", "ag/__model"] and "In transit" in next(e for e in evs if e["type"] == "run_finished")["state"]["answer"]


def test_chat_steps_show_tool_calls_by_name(monkeypatch):
    """TASK-0118: a chat lists an Agent's tool calls ("Helper › lookup_order"); model calls only in the full mode; the
    entry and exit never; the full mode shows what the step did and leaves the conversation out."""
    from app.services.chat_session_service import steps_of
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evs = list(run_stream(wf(), {"message": "Where is order B200?"}))
    labels = steps_of(evs, "labels")
    assert [(s["label"], s["type"], s["status"]) for s in labels] == [("Helper › lookup_order", "agent_tool", "ok")]
    full = steps_of(evs, "full")
    assert [s["type"] for s in full] == ["agent_model", "agent_tool", "agent_model"]
    assert full[1]["delta"]["tool"] == "lookup_order" and not any(k.startswith(agents.PREFIX) for k in full[1]["input"])
