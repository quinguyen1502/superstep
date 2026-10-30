"""superstep mcp (TASK-0171). The stdio unit test does not install mcp. The SDK test skips unless mcp imports."""
import io
import json
import os
import sys
from pathlib import Path

import httpx
import pytest

from superstep.cli import run
from superstep.cli.i18n import Catalog
from superstep.cli.mcp_bridge import cmd_mcp, read_message
from superstep.cli.session import SessionError, call


def gate(imported: bool, required: bool) -> str:
    """What the SDK test should do. SUPERSTEP_MCP_TEST=1 fails a missing import; otherwise it skips."""
    if imported:
        return "run"
    if required:
        return "fail"
    return "skip"


def test_sdk_import_gate_skips_or_fails():
    assert gate(False, False) == "skip"
    assert gate(False, True) == "fail"
    assert gate(True, False) == "run"
    assert gate(True, True) == "run"


def invoke(argv, client=None):
    out, err = io.StringIO(), io.StringIO()
    from contextlib import redirect_stderr, redirect_stdout
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SUPERSTEP_URL", raising=False)
    monkeypatch.delenv("SUPERSTEP_TOKEN", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)


def test_help_says_stdio_and_json_is_usage(isolated):
    code, out, err = invoke(["mcp", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep mcp invoices" in err
    assert "speaks MCP on stdio" in err
    code, out, err = invoke(["--lang", "vi", "mcp", "--help"])
    assert code == 0 and out == ""
    assert "Ví dụ: superstep mcp invoices" in err and "stdio" in err
    code, out, err = invoke(["mcp", "--json"])
    assert code == 2 and out == ""
    code, out, err = invoke(["mcp", "invoices", "--json"])
    assert code == 2 and out == "" and "pat_" not in err


def test_a_missing_token_names_login(isolated):
    code, out, err = invoke(["mcp", "invoices", "--url", "http://studio.test"])
    assert code == 1 and out == "" and "superstep login" in err


def envelope(data, status=200):
    return httpx.Response(status, json={"success": status < 400, "data": data, "error": None if status < 400 else data})


class _Stdin:
    def __init__(self): self.read_calls = 0
    def read(self, _n=-1):
        self.read_calls += 1
        raise AssertionError("stdin was read")


def test_disabled_or_unknown_exits_before_stdin(isolated, monkeypatch):
    monkeypatch.setenv("SUPERSTEP_TOKEN", "pat_secret-value")
    def handler(request: httpx.Request):
        if request.url.path == "/api/workflows":
            return envelope([{"id": "aaaaaa01", "name": "Echo"}, {"id": "bbbbbb02", "name": "Echo"}, {"id": "cccccc03", "name": "Other"}])
        if request.url.path == "/api/workflows/aaaaaa01/mcp":
            return envelope({"enabled": False, "tool": "run_echo", "path": "/mcp"})
        if request.url.path == "/api/health":
            return envelope({"version": "0.1.0"})
        return httpx.Response(404, json={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": "no"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    stdin = _Stdin()
    catalog = Catalog.load("en")

    def once(names):
        err = io.StringIO()
        args = type("A", (), {"workflows": names, "url": "http://studio.test"})()
        from contextlib import redirect_stderr
        with redirect_stderr(err):
            code = cmd_mcp(args, catalog, False, client, None, None, stdin=stdin, stdout=io.BytesIO())
        return code, err.getvalue()

    code, err = once(["aaaaaa01"])
    assert code == 1 and stdin.read_calls == 0 and "MCP is off" in err and "pat_secret-value" not in err
    code, err = once(["missing"])
    assert code == 1 and stdin.read_calls == 0 and "cannot open" in err
    code, err = once(["Echo"])
    assert code == 1 and stdin.read_calls == 0 and "Pass the id" in err
    code, err = once(["cccccc03"])
    assert code == 1 and stdin.read_calls == 0 and "0.1.0" in err


def _tools():
    return [
        {"name": "run_echo", "title": "Echo", "description": 'Run the Superstep workflow "Echo".',
         "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}}},
        {"name": "get_run", "description": "Status of Echo.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "resume_run", "description": "Answer Echo.", "inputSchema": {"type": "object", "properties": {}}},
    ]


def test_stdio_merges_matching_slugs_and_forwards_the_original_name(isolated, monkeypatch):
    monkeypatch.setenv("SUPERSTEP_TOKEN", "pat_secret-value")
    seen = []

    def handler(request: httpx.Request):
        if request.url.path == "/api/workflows":
            return envelope([{"id": "aaaaaa01", "name": "Echo"}, {"id": "bbbbbb02", "name": "Echo"}])
        if request.url.path.endswith("/mcp") and request.method == "GET":
            return envelope({"enabled": True, "tool": "run_echo", "path": "/mcp"})
        if request.url.path == "/mcp" and request.method == "POST":
            body = json.loads(request.content)
            seen.append((request.headers.get("authorization"), request.headers.get("x-superstep-workflow"), body))
            if body["method"] == "tools/list":
                return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"tools": _tools()}})
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {
                "content": [{"type": "text", "text": "ran"}], "isError": False}})
        return httpx.Response(404, json={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": "no"}})

    frames = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "run_echo_bbbbbb", "arguments": {"message": "hi"}}}),
        json.dumps({"jsonrpc": "2.0", "id": 4, "method": "resources/list"}),
    ]) + "\n"
    out = io.BytesIO()
    err = io.StringIO()
    from contextlib import redirect_stderr
    args = type("A", (), {"workflows": ["aaaaaa01", "bbbbbb02"], "url": "http://studio.test"})()
    with redirect_stderr(err):
        code = cmd_mcp(args, Catalog.load("en"), False, httpx.Client(transport=httpx.MockTransport(handler)), None, None,
                       stdin=io.BytesIO(frames.encode("utf-8")), stdout=out)
    assert code == 0
    text = out.getvalue().decode("utf-8")
    assert "pat_secret-value" not in text and "pat_secret-value" not in err.getvalue()
    messages = [json.loads(line) for line in text.splitlines() if line.strip()]
    assert [item["id"] for item in messages] == [1, 2, 3, 4]
    assert messages[0]["result"]["protocolVersion"] == "2025-03-26"
    assert messages[0]["result"]["serverInfo"]["name"] == "superstep"
    names = [tool["name"] for tool in messages[1]["result"]["tools"]]
    assert names[0] == "run_echo" and names[3] == "run_echo_bbbbbb" and names[3].endswith("_bbbbbb")
    assert 'Echo' in messages[1]["result"]["tools"][3]["description"]
    assert messages[2]["result"]["isError"] is False
    assert messages[3]["error"]["code"] == -32601
    call = next(item for item in seen if item[2]["method"] == "tools/call")
    assert call[0] == "Bearer pat_secret-value" and call[1] == "bbbbbb02"
    assert call[2]["params"]["name"] == "run_echo" and call[2]["params"]["arguments"] == {"message": "hi"}
    listed = [item[1] for item in seen if item[2]["method"] == "tools/list"]
    assert listed == ["aaaaaa01", "bbbbbb02"]


def test_content_length_initialize_is_answered_in_kind(isolated, monkeypatch):
    monkeypatch.setenv("SUPERSTEP_TOKEN", "pat_secret-value")

    def handler(request: httpx.Request):
        if request.url.path == "/api/workflows":
            return envelope([{"id": "aaaaaa01", "name": "Echo"}])
        if request.url.path.endswith("/mcp") and request.method == "GET":
            return envelope({"enabled": True, "tool": "run_echo", "path": "/mcp"})
        return httpx.Response(500, json={"success": False, "error": {"code": "NO", "message": "no"}})

    body = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}).encode("utf-8")
    frame = ("Content-Length: %d\r\n\r\n" % len(body)).encode("ascii") + body
    out = io.BytesIO()
    args = type("A", (), {"workflows": ["Echo"], "url": "http://studio.test"})()
    code = cmd_mcp(args, Catalog.load("en"), False, httpx.Client(transport=httpx.MockTransport(handler)), None, None,
                   stdin=io.BytesIO(frame), stdout=out)
    assert code == 0
    raw = out.getvalue()
    assert raw.startswith(b"Content-Length:")
    message, framed = read_message(io.BytesIO(raw))
    assert framed is True and message["id"] == 7 and message["result"]["protocolVersion"] == "2025-06-18"


def test_session_call_errors_map_is_optional():
    def handler(request: httpx.Request):
        return httpx.Response(403, json={"success": False, "data": None, "error": {"code": "WORKFLOW_FORBIDDEN", "message": "no"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(SessionError) as plain:
        call("GET", "http://studio.test", "/api/workflows/x/mcp", client=client, token="pat_x")
    assert plain.value.code == "BAD_RESPONSE"
    with pytest.raises(SessionError) as mapped:
        call("GET", "http://studio.test", "/api/workflows/x/mcp", client=client, token="pat_x",
             errors={"WORKFLOW_FORBIDDEN": "error.mcp_disabled"})
    assert mapped.value.code == "WORKFLOW_FORBIDDEN" and mapped.value.key == "error.mcp_disabled"


def _mcp_imported() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        return False
    return True


def test_mcp_sdk_client_lists_and_calls_the_tool(tmp_path, monkeypatch):
    decision = gate(_mcp_imported(), os.environ.get("SUPERSTEP_MCP_TEST") == "1")
    if decision == "fail":
        pytest.fail("mcp is required when SUPERSTEP_MCP_TEST=1")
    if decision == "skip":
        pytest.skip("mcp is not installed")
    import asyncio
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    wid = "abc12345"
    secret = "pat_sdk-secret"
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def do_GET(self):
            if self.path == "/api/workflows":
                self._send(200, {"success": True, "data": [{"id": wid, "name": "Echo"}], "error": None})
                return
            if self.path == f"/api/workflows/{wid}/mcp":
                self._send(200, {"success": True, "data": {"enabled": True, "tool": "run_echo", "path": "/mcp"}, "error": None})
                return
            self._send(404, {"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": "no"}})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            seen.append((self.headers.get("Authorization"), self.headers.get("X-Superstep-Workflow"), body.get("method"),
                         (body.get("params") or {}).get("name")))
            if body.get("method") == "tools/list":
                result = {"tools": [{"name": "run_echo", "description": 'Run the Superstep workflow "Echo".',
                                     "inputSchema": {"type": "object", "properties": {}}},
                                    {"name": "get_run", "description": "Status.", "inputSchema": {"type": "object"}},
                                    {"name": "resume_run", "description": "Answer.", "inputSchema": {"type": "object"}}]}
            else:
                result = {"content": [{"type": "text", "text": "called"}], "isError": False}
            self._send(200, {"jsonrpc": "2.0", "id": body.get("id"), "result": result})

        def _send(self, status, payload):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = os.environ.copy()
        env["SUPERSTEP_TOKEN"] = secret
        env.pop("SUPERSTEP_URL", None)
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"
        src = str(Path(__file__).resolve().parents[1] / "src")
        env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "superstep.cli", "mcp", wid, "--url", f"http://127.0.0.1:{port}"],
            env=env,
            cwd=str(Path(__file__).resolve().parents[1]),
        )

        async def roundtrip():
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert [tool.name for tool in tools.tools] == ["run_echo", "get_run", "resume_run"]
                    result = await session.call_tool("run_echo", {})
                    assert result.isError is False and result.content[0].text == "called"

        asyncio.run(roundtrip())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
    assert any(item[0] == "Bearer " + secret and item[1] == wid and item[2] == "tools/call" and item[3] == "run_echo" for item in seen)
    assert secret not in json.dumps([item[2:] for item in seen])
