"""the exported MCP adapter, executed in Python and TypeScript (Deno) against a local
Streamable HTTP MCP server (no external call). Configured by <PREFIX>_URL / <PREFIX>_HEADERS only; unconfigured it
is an announced offline mock, or an error in a live run."""
import json, os, subprocess, sys, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

LOG: list = []


class Mcp(BaseHTTPRequestHandler):
    def reply(self, status, body=b"", ctype="application/json", session=None):
        self.send_response(status); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        if session: self.send_header("Mcp-Session-Id", session)
        self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LOG.append({"method": msg.get("method"), "session": self.headers.get("Mcp-Session-Id"), "auth": self.headers.get("Authorization"),
                    "params": msg.get("params")})
        if msg["method"] == "initialize":
            return self.reply(200, json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"protocolVersion": "2025-06-18",
                              "capabilities": {"tools": {}}, "serverInfo": {"name": "t", "version": "1"}}}).encode(), session="sess-1")
        if "id" not in msg: return self.reply(202)
        if self.headers.get("Mcp-Session-Id") != "sess-1": return self.reply(400)
        name, args = msg["params"]["name"], msg["params"]["arguments"]
        if name == "add":
            res = {"content": [{"type": "text", "text": "5"}], "structuredContent": {"sum": args["a"] + args["b"]}}
        elif name == "sse":
            body = f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': msg['id'], 'result': {'content': [{'type': 'text', 'text': json.dumps({'echo': args})}]}})}\n\n"
            return self.reply(200, body.encode(), "text/event-stream")
        else:
            res = {"content": [{"type": "text", "text": "it broke"}], "isError": True}
        self.reply(200, json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": res}).encode())

    def do_DELETE(self):
        LOG.append({"method": "DELETE", "session": self.headers.get("Mcp-Session-Id")}); self.reply(200)

    def log_message(self, *a): pass


@pytest.fixture(scope="module")
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Mcp)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}/mcp"
    s.shutdown()


def wf(tool):
    return {"name": "Mcp", "state": [F("message"), F("res", "object")],
            "nodes": [N("start", "start"), N("m", "mcp", server_id="srv-a", tool=tool, arguments={"a": 2, "b": 3}, output_field="res"),
                      N("end", "end")],
            "edges": [E("start", "m"), E("m", "end")]}


def run_py(tmp_path, graph, env_extra):
    code = X.to_python(graph, "Mcp", 1, {}, {"input": {"message": "x"}}).code
    assert 'call_mcp_tool("MCP_SERVER_1", ' in code and "srv-a" not in code and "127.0.0.1" not in code
    f = tmp_path / f"m_{uuid.uuid4().hex[:6]}.py"; f.write_text(code)
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH" and not k.startswith("MCP_SERVER")}
    env.update(env_extra)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def run_ts(tmp_path, base, graph, env_extra):
    code = T.to_typescript(graph, "Mcp", 1, {}, {"input": {"message": "x"}}).code
    assert 'callMcpTool("MCP_SERVER_1", ' in code and "srv-a" not in code and "127.0.0.1" not in code
    f = tmp_path / f"m_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code)
    env = {k: v for k, v in base.items() if k != "LLM_PROVIDER" and not k.startswith("MCP_SERVER")}
    env.update(env_extra)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys", "--allow-net", str(f)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


@pytest.fixture(params=["python", "typescript"])
def run(request):
    if request.param == "typescript":
        base = request.getfixturevalue("deno_env")
        return lambda tp, g, **e: run_ts(tp, base, g, e)
    return lambda tp, g, **e: run_py(tp, g, e)


def test_configured_server_is_called_with_its_headers(tmp_path, server, run):
    LOG.clear()
    p = run(tmp_path, wf("add"), MCP_SERVER_1_URL=server, MCP_SERVER_1_HEADERS=json.dumps({"Authorization": "Bearer t0k"}))
    assert p.returncode == 0, p.stderr
    assert '"sum": 5' in p.stdout.replace('"sum":5', '"sum": 5')
    assert [x["method"] for x in LOG] == ["initialize", "notifications/initialized", "tools/call", "DELETE"]
    assert {x.get("auth") for x in LOG if x["method"] != "DELETE"} == {"Bearer t0k"}
    assert LOG[2]["session"] == "sess-1" and LOG[2]["params"] == {"name": "add", "arguments": {"a": 2, "b": 3}}


def test_event_stream_replies_and_json_text(tmp_path, server, run):
    p = run(tmp_path, wf("sse"), MCP_SERVER_1_URL=server, LLM_PROVIDER="openai")
    assert p.returncode == 0, p.stderr
    assert '"echo"' in p.stdout


def test_a_tool_error_stops_the_run(tmp_path, server, run):
    p = run(tmp_path, wf("boom"), MCP_SERVER_1_URL=server)
    assert p.returncode != 0 and "it broke" in p.stderr


def test_unconfigured_offline_is_an_announced_mock(tmp_path, run):
    p = run(tmp_path, wf("add"))
    assert p.returncode == 0 and "(offline mock)" in p.stderr and "MCP_SERVER_1_URL" in p.stderr


def test_unconfigured_live_run_is_refused(tmp_path, run):
    p = run(tmp_path, wf("add"), LLM_PROVIDER="openai")
    assert p.returncode != 0 and "set MCP_SERVER_1_URL" in p.stderr


def test_nodes_on_one_server_share_a_prefix_and_ids_stay_out():
    g = {"name": "Two", "state": [F("message"), F("a", "object"), F("b", "object"), F("c", "object")],
         "nodes": [N("start", "start"),
                   N("x", "mcp", server_id="srv-a", tool="t1", arguments={}, output_field="a"),
                   N("y", "mcp", server_id="srv-b", tool="t2", arguments={}, output_field="b"),
                   N("z", "mcp", server_id="srv-a", tool="t3", arguments={}, output_field="c"), N("end", "end")],
         "edges": [E("start", "x"), E("x", "y"), E("y", "z"), E("z", "end")]}
    py, ts = X.to_python(g, "Two", 1, {}, {}).code, T.to_typescript(g, "Two", 1, {}, {}).code
    for code, call in ((py, "call_mcp_tool"), (ts, "callMcpTool")):
        assert f'{call}("MCP_SERVER_1", "t1"' in code and f'{call}("MCP_SERVER_2", "t2"' in code and f'{call}("MCP_SERVER_1", "t3"' in code
        assert "srv-a" not in code and "srv-b" not in code and "MCP_SERVER_1, MCP_SERVER_2" in code
