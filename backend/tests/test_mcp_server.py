"""TASK-0114: workflows as MCP tools at /mcp, driven by the official MCP Python SDK client over Streamable HTTP
against a real uvicorn server (with the in-process worker): opt-in, token auth, tool schema, run, Human-node pause,
resume, get_run, and errors."""
import asyncio, json, socket, threading, time, uuid
import httpx, pytest, uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from app.main import app
from app.services.workflow_mcp_service import tool_name
from test_agent_server_api import SIMPLE
from test_hitl import APPROVAL


@pytest.fixture(scope="module")
def base():
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True); th.start()
    for _ in range(100):
        if srv.started: break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True; th.join(10)


def H(t): return {"Authorization": f"Bearer {t}"}


def setup(base, wf, enable=True):
    """A user, a saved workflow, a token: (jwt, wid, wft token)."""
    with httpx.Client(base_url=base) as c:
        jwt = c.post("/api/auth/register", json={"email": f"mcp{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
        wid = c.post("/api/workflows", json={**wf, "name": f"{wf['name']} {uuid.uuid4().hex[:4]}"}, headers=H(jwt)).json()["data"]["id"]
        tok = c.post(f"/api/workflows/{wid}/tokens", json={"name": "mcp"}, headers=H(jwt)).json()["data"]["token"]
        if enable: assert c.put(f"/api/workflows/{wid}/mcp", json={"enabled": True}, headers=H(jwt)).json()["data"]["enabled"]
    return jwt, wid, tok


def session(base, tok, fn, header="authorization"):
    async def go():
        hdr = {"Authorization": f"Bearer {tok}"} if header == "authorization" else {"X-Workflow-Token": tok}
        async with httpx.AsyncClient(headers=hdr, timeout=60) as http:
            async with streamable_http_client(f"{base}/mcp", http_client=http) as (r, w, _):
                async with ClientSession(r, w) as s:
                    await s.initialize(); return await fn(s)
    return asyncio.run(go())


def body(res): return json.loads(res.content[0].text)


def test_tools_run_and_schema(base):
    _, wid, tok = setup(base, SIMPLE)
    async def fn(s):
        tools = (await s.list_tools()).tools
        run = tools[0]
        assert [t.name for t in tools[1:]] == ["get_run", "resume_run"] and run.name.startswith("run_echo_")
        assert run.inputSchema["properties"] == {"message": {"type": "string"}, "answer": {"type": "string"}}
        res = await s.call_tool(run.name, {"message": "hi"})
        out = body(res)
        assert not res.isError and out["status"] == "ok" and out["final_state"]["message"] == "hi" and out["workflow_id"] == wid
        again = body(await s.call_tool("get_run", {"run_id": out["run_id"]}))
        assert again["status"] == "ok" and again["run_id"] == out["run_id"]
        miss = await s.call_tool("get_run", {"run_id": "nope"})
        assert miss.isError and body(miss)["error"]["code"] == "RUN_NOT_FOUND"
        bad = await s.call_tool("run_other", {})
        assert bad.isError and body(bad)["error"]["code"] == "MCP_TOOL_NOT_FOUND"
    session(base, tok, fn, header="x-workflow-token")


def test_human_node_pause_and_resume(base):
    _, _, tok = setup(base, APPROVAL)
    async def fn(s):
        name = (await s.list_tools()).tools[0].name
        out = body(await s.call_tool(name, {"message": "order 42"}))
        assert out["status"] == "waiting" and out["waiting"]["node"] == "ask" and "order 42" in out["waiting"]["prompt"]
        done = body(await s.call_tool("resume_run", {"run_id": out["run_id"], "response": True}))
        assert done["status"] == "ok" and done["final_state"]["decision"] == "approved"
        again = await s.call_tool("resume_run", {"run_id": out["run_id"], "response": "x"})
        assert again.isError and body(again)["error"]["code"] == "RUN_NOT_WAITING"
    session(base, tok, fn)


def test_opt_in_and_auth(base):
    jwt, wid, tok = setup(base, SIMPLE, enable=False)
    with httpx.Client(base_url=base) as c:
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        r = c.post("/mcp", json=init, headers=H(tok)); assert r.status_code == 403 and r.json()["error"]["code"] == "MCP_SERVER_DISABLED"
        for bad in ({}, H("wft_nope"), H(jwt)):
            r = c.post("/mcp", json=init, headers=bad); assert r.status_code == 401 and r.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
        got = c.get(f"/api/workflows/{wid}/mcp", headers=H(jwt)).json()["data"]
        assert got["enabled"] is False and got["path"] == "/mcp" and got["tool"].startswith("run_echo_")
        other = c.post("/api/auth/register", json={"email": f"o{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
        r = c.put(f"/api/workflows/{wid}/mcp", json={"enabled": True}, headers=H(other)); assert r.json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
        c.put(f"/api/workflows/{wid}/mcp", json={"enabled": True}, headers=H(jwt))
        c.post("/api/workflows", json={**SIMPLE, "id": wid, "name": "Renamed"}, headers=H(jwt))  # saving keeps the flag
        assert c.get(f"/api/workflows/{wid}/mcp", headers=H(jwt)).json()["data"] == {"enabled": True, "tool": "run_renamed", "path": "/mcp"}


def test_tool_name():
    assert tool_name("Refund approval (v2)") == "run_refund_approval_v2" and tool_name("") == "run_workflow" and tool_name("Đơn") == "run_n"
    assert len(tool_name("x" * 200)) == 64
