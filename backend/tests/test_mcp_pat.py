"""TASK-0171: a personal access token plus X-Superstep-Workflow on /mcp. Workflow tokens stay scoped to themselves."""
import os, tempfile
os.environ.setdefault("STUDIO_DB", tempfile.mktemp(suffix=".db"))
import asyncio, json, socket, threading, time, uuid
import httpx, pytest, uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from app.api.deps import get_db
from app.main import app
from app.repositories import RunRepository
from app.services.trigger_service import TriggerService
from test_agent_server_api import SIMPLE


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


def H(token, wid=None):
    headers = {"Authorization": f"Bearer {token}"}
    if wid: headers["X-Superstep-Workflow"] = wid
    return headers


def setup(base, enable=True):
    """Owner jwt, workflow id, workflow token, PAT secret, user id. A second user is not created here."""
    with httpx.Client(base_url=base) as c:
        jwt = c.post("/api/auth/register", json={"email": f"patmcp{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
        uid = c.get("/api/me", headers=H(jwt)).json()["data"]["id"]
        wid = c.post("/api/workflows", json={**SIMPLE, "name": f"{SIMPLE['name']} {uuid.uuid4().hex[:4]}"}, headers=H(jwt)).json()["data"]["id"]
        wft = c.post(f"/api/workflows/{wid}/tokens", json={"name": "mcp"}, headers=H(jwt)).json()["data"]["token"]
        pat = c.post("/api/me/tokens", json={"name": f"cli-{uuid.uuid4().hex[:6]}"}, headers=H(jwt)).json()["data"]["token"]
        if enable: assert c.put(f"/api/workflows/{wid}/mcp", json={"enabled": True}, headers=H(jwt)).json()["data"]["enabled"]
    return jwt, wid, wft, pat, uid


def init_body():
    return {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}


def session(base, headers, fn):
    async def go():
        async with httpx.AsyncClient(headers=headers, timeout=60) as http:
            async with streamable_http_client(f"{base}/mcp", http_client=http) as (reader, writer, _):
                async with ClientSession(reader, writer) as s:
                    await s.initialize()
                    return await fn(s)
    return asyncio.run(go())


def body(res): return json.loads(res.content[0].text)


def test_rate_key_keeps_the_workflow_token_and_adds_the_pat_key():
    class Tok:
        id = "abc"

    class Limiter:
        def __init__(self): self.keys = []
        async def hit(self, key, limit, window):
            self.keys.append(key); return True, 0

    assert TriggerService.rate_key(Tok()) == "token:abc"
    assert TriggerService.rate_key(pat_id="p1", workflow_id="w1") == "pat:p1:w1"
    limiter = Limiter()
    asyncio.run(TriggerService(None, None, None, None, limiter=limiter).check_rate(key="pat:p1:w1"))
    assert limiter.keys == ["pat:p1:w1"]


def test_pat_without_a_header_or_access_is_rejected(base):
    jwt, wid, _wft, pat, _uid = setup(base, enable=False)
    with httpx.Client(base_url=base) as c:
        missing = c.post("/mcp", json=init_body(), headers=H(pat))
        assert missing.status_code == 401 and missing.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
        off = c.post("/mcp", json=init_body(), headers=H(pat, wid))
        assert off.status_code == 403 and off.json()["error"]["code"] == "MCP_SERVER_DISABLED"
        c.put(f"/api/workflows/{wid}/mcp", json={"enabled": True}, headers=H(jwt))
        unknown = c.post("/mcp", json=init_body(), headers=H("pat_not-a-real-token", wid))
        assert unknown.status_code == 401 and unknown.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
        assert "AUTH_TOKEN_INVALID" not in unknown.text
        other = c.post("/api/auth/register", json={"email": f"no{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
        other_pat = c.post("/api/me/tokens", json={"name": "other"}, headers=H(other)).json()["data"]["token"]
        denied = c.post("/mcp", json=init_body(), headers=H(other_pat, wid))
        assert denied.status_code == 401 and denied.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
        listed = c.get("/api/me/tokens", headers=H(jwt)).json()["data"]["items"]
        assert c.delete(f"/api/me/tokens/{listed[0]['id']}", headers=H(jwt)).status_code == 200
        revoked = c.post("/mcp", json=init_body(), headers=H(pat, wid))
        assert revoked.status_code == 401 and revoked.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"


def test_a_workflow_token_still_sees_only_its_workflow(base):
    _jwt, wid, wft, _pat, _uid = setup(base, enable=True)
    with httpx.Client(base_url=base) as c:
        other = c.post("/api/workflows", json={**SIMPLE, "name": f"Other {uuid.uuid4().hex[:4]}"}, headers=H(_jwt)).json()["data"]["id"]
        assert c.put(f"/api/workflows/{other}/mcp", json={"enabled": True}, headers=H(_jwt)).json()["data"]["enabled"]

    async def names(s):
        return [t.name for t in (await s.list_tools()).tools]

    got = session(base, H(wft, other), names)
    assert got[0].startswith("run_echo_") and "run_other" not in got[0]
    assert got[1:] == ["get_run", "resume_run"]


def test_pat_lists_the_same_tools_and_owns_the_run(base):
    jwt, wid, wft, pat, uid = setup(base, enable=True)

    async def names(s):
        tools = (await s.list_tools()).tools
        return [t.name for t in tools]

    assert session(base, H(wft), names) == session(base, H(pat, wid), names)

    async def run(s):
        tool = (await s.list_tools()).tools[0]
        return body(await s.call_tool(tool.name, {"message": "hi"}))

    out = session(base, H(pat, wid), run)
    assert out["status"] == "ok" and out["source"] == "api" and out["workflow_id"] == wid
    stored = RunRepository(get_db()).get(out["run_id"])
    assert stored.owner == uid and stored.source == "api" and stored.workflow_id == wid
