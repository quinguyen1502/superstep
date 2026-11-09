"""MCP client (stdio + Streamable HTTP), server registry with encrypted secrets, discovery, MCP tool node."""
import os, socket, subprocess, sys, time, uuid
os.environ.pop("OPENAI_API_KEY", None)
import pytest
from fastapi.testclient import TestClient
from app.core import crypto
from app.engine import mcp_client
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.templating import render_args
from app.engine.validator import validate
from app.main import app

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "mcp_demo_server.py")
STDIO = {"transport": "stdio", "command": sys.executable, "args": [FIX]}
H = lambda t: {"Authorization": f"Bearer {t}"}


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="module")
def http_server():
    port = free_port()
    p = subprocess.Popen([sys.executable, FIX, "http", str(port)], env={**os.environ, "MCP_REQUIRE_TOKEN": "t0ken"})
    for _ in range(50):
        try: socket.create_connection(("127.0.0.1", port), 0.1).close(); break
        except OSError: time.sleep(0.1)
    yield f"http://127.0.0.1:{port}/mcp"
    p.terminate(); p.wait()


def test_stdio_client_lists_and_calls_tools_in_a_clean_environment(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "must-not-leak")
    assert [t["name"] for t in mcp_client.list_tools(STDIO)] == ["add", "echo", "env", "fail", "slow"]
    assert mcp_client.call_tool(STDIO, "add", {"a": 2, "b": 3}) == {"sum": 5}
    assert mcp_client.call_tool(STDIO, "echo", {"text": "hi"}) == "hi"
    spec = {**STDIO, "env": {"API_TOKEN": "s3cret"}}
    assert mcp_client.call_tool(spec, "env", {"name": "API_TOKEN"}) == "s3cret"
    assert mcp_client.call_tool(spec, "env", {"name": "JWT_SECRET"}) is None  # the API's environment is not inherited
    assert mcp_client.call_tool(spec, "env", {"name": "HOME"}).startswith(os.path.join(os.environ.get("TMPDIR", "/tmp"), "lgs-mcp-"))
    with pytest.raises(mcp_client.McpError) as e: mcp_client.call_tool(STDIO, "fail", {})
    assert e.value.code == "MCP_TOOL_FAILED" and "boom" in str(e.value)
    with pytest.raises(mcp_client.McpError, match="no response within"): mcp_client.call_tool(STDIO, "slow", {"seconds": 5}, timeout=1)
    with pytest.raises(mcp_client.McpError, match="cannot start"): mcp_client.list_tools({"transport": "stdio", "command": "/nonexistent/mcp"})


def test_http_client_json_and_sse(http_server):
    spec = {"transport": "http", "url": http_server, "headers": {"Authorization": "Bearer t0ken"}}
    assert len(mcp_client.list_tools(spec)) == 5
    assert mcp_client.call_tool(spec, "add", {"a": 1, "b": 1}) == {"sum": 2}  # answered as SSE
    with pytest.raises(mcp_client.McpError, match="HTTP 401"): mcp_client.list_tools({**spec, "headers": {}})


def test_render_args_keeps_types():
    st = {"n": 3, "s": "x"}
    assert render_args({"a": "{{state.n}}", "b": "v={{state.s}}", "c": ["{{state.s}}"], "d": 1}, st) == {"a": 3, "b": "v=x", "c": ["x"], "d": 1}


def mcp_wf(**d):
    return {"name": "m", "state": [{"name": "n", "type": "integer"}, {"name": "out", "type": "object"}],
            "nodes": [{"id": "start", "type": "start", "data": {}},
                      {"id": "m", "type": "mcp", "data": {"label": "Add", "server_id": "s1", "tool": "add", "arguments": {"a": "{{state.n}}", "b": "2"}, "output_field": "out", **d}},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "m"}, {"id": "2", "source": "m", "target": "end"}]}


def test_mcp_node_validation_and_engine():
    assert validate(mcp_wf()) == []
    assert any("choose a server" in x for x in validate(mcp_wf(server_id="")))
    assert any("choose a tool" in x for x in validate(mcp_wf(tool="")))
    assert any("state.zz" in x for x in validate(mcp_wf(arguments={"a": "{{state.zz}}"})))
    seen = []
    evs = list(run_stream(mcp_wf(), {"n": 5}, ports=Ports(mcp_call=lambda s, t, a: seen.append((s, t, a)) or {"ok": 1})))
    assert evs[-1]["state"]["out"] == {"ok": 1} and seen == [("s1", "add", {"a": 5, "b": "2"})]


def login(c, email=None, admin=False):
    email = email or f"mcp{uuid.uuid4().hex[:6]}@example.com"
    c.post("/api/auth/register", json={"email": email, "password": "secret123"})
    tok = c.post("/api/auth/login", json={"email": email, "password": "secret123"}).json()["data"]
    if admin:
        from app.api.deps import get_db
        from app.repositories import UserRepository
        UserRepository(get_db()).set_admin(tok["user"]["id"])
    return tok["token"]


def test_registry_permissions_secrets_and_runs(monkeypatch, http_server):
    c = TestClient(app); admin, user, other = login(c, admin=True), login(c), login(c)
    stdio = {"name": "Demo", "transport": "stdio", "command": sys.executable, "args": [FIX], "secrets": {"API_TOKEN": "s3cret-value"}}
    assert c.post("/api/mcp/servers", json=stdio, headers=H(admin)).json()["error"]["code"] == "MCP_STDIO_DISABLED"
    monkeypatch.setenv("STUDIO_MCP_STDIO", "1")
    assert c.post("/api/mcp/servers", json=stdio, headers=H(user)).json()["error"]["code"] == "MCP_ADMIN_REQUIRED"
    s = c.post("/api/mcp/servers", json={**stdio, "scope": "org"}, headers=H(admin)).json()["data"]
    assert s["secrets"] == {"API_TOKEN": "••••alue"} and "s3cret" not in str(s)
    from app.api.deps import get_db
    from app.repositories import McpServerRepository
    row = McpServerRepository(get_db()).get(s["id"])
    assert "s3cret" not in row.secrets and crypto.decrypt(row.secrets) == '{"API_TOKEN": "s3cret-value"}'  # encrypted at rest
    # org server: visible to everyone, editable by admins only
    lst = c.get("/api/mcp/servers", headers=H(user)).json()["data"]
    assert [x["id"] for x in lst["servers"]] == [s["id"]] and lst["servers"][0]["can_edit"] is False and lst["stdio_enabled"]
    assert c.delete(f"/api/mcp/servers/{s['id']}", headers=H(user)).json()["error"]["code"] == "MCP_ADMIN_REQUIRED"
    d = c.post(f"/api/mcp/servers/{s['id']}/discover", headers=H(user)).json()["data"]
    assert [t["name"] for t in d["tools"]][:2] == ["add", "echo"] and d["tools_at"]
    # update keeps a secret given as null, renames
    u = c.put(f"/api/mcp/servers/{s['id']}", json={"name": "Demo tools", "command": sys.executable, "args": [FIX], "secrets": {"API_TOKEN": None}}, headers=H(admin)).json()["data"]
    assert u["name"] == "Demo tools" and u["secrets"] == {"API_TOKEN": "••••alue"} and u["tools"] == []
    # a run: string form values coerced by the tool schema, secret visible to the server process only
    wf = mcp_wf(server_id=s["id"], arguments={"a": "{{state.n}}", "b": "2"})
    with c.websocket_connect(f"/ws/run?token={user}") as w:
        w.send_json({"workflow": wf, "input": {"n": 40}}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(w.receive_json())
    assert next(x for x in evs if x["type"] == "run_finished")["state"]["out"] == {"sum": 42}
    wf_env = mcp_wf(server_id=s["id"], tool="env", arguments={"name": "API_TOKEN"}); wf_env["state"][1]["type"] = "string"
    with c.websocket_connect(f"/ws/run?token={user}") as w:
        w.send_json({"workflow": wf_env, "input": {"n": 1}}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(w.receive_json())
    assert next(x for x in evs if x["type"] == "run_finished")["state"]["out"] == "s3cret-value"
    with c.websocket_connect(f"/ws/run?token={user}") as w:  # tool error -> node error with the code
        w.send_json({"workflow": mcp_wf(server_id=s["id"], tool="fail", arguments={}), "input": {"n": 1}}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(w.receive_json())
    assert evs[-1]["error"]["code"] == "MCP_TOOL_FAILED" and evs[-1]["node"] == "m"
    # personal HTTP server: private address refused unless allowed; owner only
    http = {"name": "Local", "transport": "http", "url": http_server, "secrets": {"Authorization": "Bearer t0ken"}}
    assert c.post("/api/mcp/servers", json=http, headers=H(user)).json()["error"]["code"] == "MCP_URL_INVALID"
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "1")
    h = c.post("/api/mcp/servers", json=http, headers=H(user)).json()["data"]
    assert h["can_edit"] and len(c.post(f"/api/mcp/servers/{h['id']}/discover", headers=H(user)).json()["data"]["tools"]) == 5
    assert c.post(f"/api/mcp/servers/{h['id']}/discover", headers=H(other)).json()["error"]["code"] == "MCP_SERVER_NOT_FOUND"
    assert c.post("/api/mcp/servers", json={**http, "scope": "org"}, headers=H(user)).json()["error"]["code"] == "MCP_ADMIN_REQUIRED"
    monkeypatch.setenv("STUDIO_MCP_STDIO", "0")  # turning stdio off also stops existing stdio servers
    assert c.post(f"/api/mcp/servers/{s['id']}/discover", headers=H(user)).json()["error"]["code"] == "MCP_STDIO_DISABLED"
    assert c.delete(f"/api/mcp/servers/{h['id']}", headers=H(user)).json()["success"]


def test_interop_with_the_official_sdk_server():
    """Our client against a server built with from the MCP Python SDK, when the SDK is installed."""
    try: from mcp.server.mcpserver import MCPServer  # noqa: F401  (SDK 2.x)
    except ImportError:
        pytest.importorskip("mcp.server.fastmcp")  # SDK 1.x
        MCPServer = None
    cls = ("from mcp.server.mcpserver import MCPServer as S" if MCPServer else "from mcp.server.fastmcp import FastMCP as S")
    code = cls + "\nm = S('sdk')\n@m.tool()\ndef mul(a: int, b: int) -> int:\n    return a * b\nm.run()\n"
    spec = {"transport": "stdio", "command": sys.executable, "args": ["-c", code]}
    tools = mcp_client.list_tools(spec, timeout=20)
    assert [t["name"] for t in tools] == ["mul"] and tools[0]["input_schema"]["properties"]["a"]["type"] == "integer"
    out = mcp_client.call_tool(spec, "mul", {"a": 6, "b": 7}, timeout=20)
    assert out in (42, {"result": 42})
