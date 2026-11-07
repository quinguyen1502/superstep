"""Executable TypeScript browser export (TASK-0252).

The generated file is executed with Node's type stripper after the LangGraph
import is pointed at a local stub. The driver calls the embedded helper and the
generated node functions. The unmodified file keeps ``npm:`` specifiers for Deno.
"""
import json
import os
import subprocess
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import threading
import time

import pytest

from app.api.deps import get_db
from app.repositories import McpServerRepository
from tests.test_browser_connections import create
from tests.test_browser_python_export import HTML, NEXT, PROXY, SECRETS, _chain, _code, _mcp, _recipe, _save, _server
from tests.test_chat_trigger_runs import H, c, user

STUB = '''
export function Annotation(_spec) { return {}; }
Annotation.Root = function Root(_fields) { return { State: {}, Update: {} }; };
export const START = "__start__";
export const END = "__end__";
export class StateGraph {
  constructor(_state) {}
  addNode() { return this; }
  addEdge() { return this; }
  addConditionalEdges() { return this; }
  compile() { return {}; }
}
export class MemorySaver {}
export class Command { constructor(value) { this.value = value; } }
export class InMemoryCache {}
export function interrupt(value) {
  const error = new Error("interrupt");
  error.name = "GraphInterrupt";
  error.value = value;
  return Promise.reject(error);
}
'''
GUARD = 'if ((import.meta as { main?: boolean }).main !== false) await main();\n'


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "1")


@pytest.fixture()
def site():
    class Handler(BaseHTTPRequestHandler):
        inflight = 0
        peak = 0
        hits = []
        guard = threading.Lock()

        def do_GET(self):
            with self.guard:
                type(self).inflight += 1
                type(self).peak = max(type(self).peak, type(self).inflight)
            if self.path.startswith("/slow"):
                time.sleep(0.3)
            body = (NEXT if self.path.startswith("/next") else HTML).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            with self.guard:
                type(self).hits.append((self.path, self.headers.get("Authorization")))
                type(self).inflight -= 1

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    origin = f"http://{host}:{port}"
    try:
        yield {"origin": origin, "url": origin + "/", "slow": origin + "/slow", "next": origin + "/next", "handler": Handler}
    finally:
        server.shutdown()


def _run(tmp_path, code, driver, env=None):
    folder = tmp_path / uuid.uuid4().hex
    folder.mkdir()
    assert GUARD in code
    (folder / "package.json").write_text('{"type":"module"}\n')
    (folder / "langgraph-stub.ts").write_text(STUB)
    source = code.replace(GUARD, "")
    source = source.replace('from "npm:@langchain/langgraph@^1.5"', 'from "./langgraph-stub.ts"')
    source = source.replace('from "npm:@langchain/langgraph-checkpoint@^1"', 'from "./langgraph-stub.ts"')
    (folder / "graph.ts").write_text(source + "\n" + driver)
    base = {k: v for k, v in os.environ.items() if not k.startswith("SUPERSTEP_BROWSER")}
    if env:
        base.update(env)
    return subprocess.run(
        ["node", "--experimental-strip-types", "--disable-warning=ExperimentalWarning", "graph.ts"],
        cwd=folder, env=base, capture_output=True, text=True, timeout=90,
    )


def _body(done):
    assert done.returncode == 0, done.stderr[-4000:] + done.stdout[-2000:]
    line = [item for item in done.stdout.splitlines() if item.startswith("{") or item.startswith("[")][-1]
    return json.loads(line)


def test_recipe_runs_on_node_without_secrets_or_a_fixed_url(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    wid = _save(c, owner, _recipe(sid))
    data = _code(c, owner, wid, "typescript")
    assert data["managed_placeholders"] is False
    assert "async function browserCall(" in data["code"]
    assert "callMcpTool(" not in data["code"] and "managedOperation(" not in data["code"]
    assert sid not in data["code"] and "https://example.com" not in data["code"]
    assert all(secret not in data["code"] for secret in SECRETS.values())
    saved = c.get(f"/api/workflows/{wid}", headers=H(owner["token"])).json()["data"]
    assert "_browser_export" not in json.dumps(saved) and "_managed_export" not in json.dumps(saved)
    driver = (
        "const state0 = { url: " + json.dumps(site["url"]) + ", order_id: 'SO-1' };\n"
        "const page = await open(state0);\n"
        "const filled = await fill({ ...state0, ...page });\n"
        "const readResult = await read({ ...state0, ...page, ...filled });\n"
        "console.log(JSON.stringify({ page, filled, readResult }));\n"
    )
    body = _body(_run(tmp_path, data["code"], driver))
    assert body["readResult"]["shipment"]["fields"]["status"] == "In transit"
    assert "SO-1" not in json.dumps(body["filled"]["fill_result"])
    assert site["handler"].hits and all(auth is None for _, auth in site["handler"].hits)
    project = c.get(f"/api/workflows/{wid}/export/typescript/project", headers=H(owner["token"]))
    assert project.status_code == 200, project.text
    with zipfile.ZipFile(BytesIO(project.content)) as archive:
        files = {name.split("/", 1)[1]: archive.read(name).decode() for name in archive.namelist()}
    assert "browserCall" in files["README.md"]
    assert "refused outside Studio" in files["README.md"] or "Upload and download are refused" in files["README.md"]
    assert "SUPERSTEP_BROWSER_DRIVER=" in files[".env.example"]
    assert "playwright" not in files["package.json"]


def test_secrets_and_private_drivers_do_not_open_a_page(c, site, tmp_path):
    owner = user(c)
    response = create(c, owner, settings={
        "provider": "browserless", "allowed_origins": ["https://example.com"],
        "proxy": {"mode": "custom", "server": PROXY, "auth": "basic"},
    }, secrets=SECRETS)
    assert response.status_code == 200, response.text
    sid = response.json()["data"]["id"]
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "https://example.com/"}, "page")])), "typescript")["code"]
    assert all(secret not in code for secret in SECRETS.values())
    assert PROXY in code and sid not in code
    driver = '''
const alias = Object.keys(BROWSER_POLICY)[0];
const names = BROWSER_POLICY[alias].env;
async function call() {
  try { await browserCall(alias, "navigate", { url: "https://example.com/" }, {}); return null; }
  catch (error) { return error.code; }
}
const token = await call();
process.env[names.token] = "runtime-token";
process.env[names.endpoint] = "https://browserless.example/";
const proxy = await call();
console.log(JSON.stringify({ token, proxy }));
'''
    body = _body(_run(tmp_path, code, driver))
    assert body == {"token": "token_missing", "proxy": "proxy_credentials_missing"}
    assert not site["handler"].hits


def test_approval_stale_lost_unknown_and_whitelist(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"], require_mutating_approval=True, allow_upload=True, allow_evaluate_js=True, max_actions=8)
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")])), "typescript")["code"]
    driver = (
        "const alias = Object.keys(BROWSER_POLICY)[0];\n"
        f"const url = {json.dumps(site['url'])};\n"
        f"const next = {json.dumps(site['next'])};\n"
        "async function codeOf(fn) { try { return await fn(); } catch (error) { return error.code; } }\n"
        "const opened = await browserCall(alias, 'navigate', { url }, {});\n"
        "browserDecide = async () => false;\n"
        "const reject = await codeOf(() => browserCall(alias, 'click', { observation_id: opened.observation.observation_id, element_id: 'go' }, {}));\n"
        "browserDecide = async () => ({ text: 'yes' });\n"
        "const model = await codeOf(() => browserCall(alias, 'click', { observation_id: opened.observation.observation_id, element_id: 'go' }, {}));\n"
        "const urlAfterReject = sessions.get(alias).page.url;\n"
        "browserDecide = async () => ({ approved: true });\n"
        "const clicked = await browserCall(alias, 'click', { observation_id: opened.observation.observation_id, element_id: 'go' }, {});\n"
        "const moved = await browserCall(alias, 'navigate', { url: next }, {});\n"
        "const stale = await codeOf(() => browserCall(alias, 'click', { observation_id: opened.observation.observation_id, element_id: 'go' }, {}));\n"
        "const urlAfterStale = sessions.get(alias).page.url;\n"
        "process.env.SUPERSTEP_BROWSER_FAULT = 'unknown';\n"
        "const unknown = await codeOf(() => browserCall(alias, 'click', { observation_id: moved.observation.observation_id, element_id: 'status' }, {}));\n"
        "const faultCleared = process.env.SUPERSTEP_BROWSER_FAULT || null;\n"
        "process.env.SUPERSTEP_BROWSER_FAULT = 'lost';\n"
        "const lost = await codeOf(() => browserCall(alias, 'navigate', { url }, {}));\n"
        "const lostCleared = process.env.SUPERSTEP_BROWSER_FAULT || null;\n"
        "const recovered = await browserCall(alias, 'navigate', { url }, {});\n"
        "const denied = await codeOf(() => browserCall(alias, 'navigate', { url: 'https://example.com/' }, {}));\n"
        "const shot = await browserCall(alias, 'screenshot', {}, {});\n"
        "const title = await browserCall(alias, 'evaluate', { observation_id: recovered.observation.observation_id, expression: 'document.title' }, {});\n"
        "const js = await codeOf(() => browserCall(alias, 'evaluate', { observation_id: recovered.observation.observation_id, expression: 'alert(1)' }, {}));\n"
        "let uploadMessage = '';\n"
        "const upload = await codeOf(() => browserCall(alias, 'upload', { observation_id: recovered.observation.observation_id }, {}).catch((error) => { uploadMessage = error.message; throw error; }));\n"
        "console.log(JSON.stringify({ reject, model, urlAfterReject, clicked: clicked.status, stale, urlAfterStale, unknown, faultCleared, lost, lostCleared, recovered: recovered.status, denied, shot, title: title.value, js, upload, uploadMessage }));\n"
    )
    body = _body(_run(tmp_path, code, driver))
    assert body["reject"] == "approval_rejected" and body["model"] == "approval_rejected"
    assert body["urlAfterReject"] == site["url"]
    assert body["clicked"] == "confirmed" and body["stale"] == "stale_observation"
    assert body["urlAfterStale"] == site["next"]
    assert body["unknown"] == "unknown_effect" and body["faultCleared"] is None
    assert body["lost"] == "session_lost" and body["lostCleared"] is None and body["recovered"] == "confirmed"
    assert body["denied"] == "whitelist_denied"
    assert body["shot"]["captured"] is True and body["shot"]["inline_bytes"] is False
    assert body["title"] == "Track" and body["js"] == "capability_refused"
    assert body["upload"] == "capability_refused" and "refused outside Studio" in body["uploadMessage"]


def test_same_session_commands_do_not_overlap(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {}, "page")])), "typescript")["code"]
    driver = (
        f"const url = {json.dumps(site['slow'])};\n"
        "const alias = Object.keys(BROWSER_POLICY)[0];\n"
        "const results = await Promise.all([browserCall(alias, 'navigate', { url }, {}), browserCall(alias, 'navigate', { url }, {})]);\n"
        "console.log(JSON.stringify({ sequences: results.map((item) => item.sequence).sort((a, b) => a - b), peak: sessions.get(alias).peak }));\n"
    )
    body = _body(_run(tmp_path, code, driver))
    assert body["sequences"] == [1, 2] and body["peak"] == 1
    assert site["handler"].peak == 1


def test_agent_parallel_calls_keep_session_order(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    tool = lambda name: {
        "source": "mcp", "name": name, "description": "Open a page", "server_id": sid, "tool": "navigate",
        "parameters": {"type": "object", "properties": {}},
        "url_binding": {"source": "fixed", "value": site["slow"]},
    }
    graph = {"name": "Agent browser", "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}],
             "nodes": [
                 {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
                 {"id": "ag", "type": "agent", "position": {"x": 1, "y": 0}, "data": {
                     "label": "Browser", "prompt": "{{state.message}}", "output_field": "answer",
                     "tools": [tool("navigate_a"), tool("navigate_b")]}},
                 {"id": "end", "type": "end", "position": {"x": 2, "y": 0}, "data": {}},
             ],
             "edges": [{"id": "e1", "source": "start", "target": "ag"}, {"id": "e2", "source": "ag", "target": "end"}]}
    code = _code(c, owner, _save(c, owner, graph), "typescript")["code"]
    assert "browserCall(" in code and site["slow"] in code and sid not in code and "callMcpTool(" not in code
    driver = '''
const state = { message: "navigate_a navigate_b", answer: "", agent_browser: {
  messages: [], pending: [{ id: "1", name: "navigate_a", args: {} }, { id: "2", name: "navigate_b", args: {} }],
  rounds: 0, steps: [], answer: null } };
const update = await browser_tool(state);
console.log(JSON.stringify(update));
'''
    body = _body(_run(tmp_path, code, driver))
    assert "confirmed" in json.dumps(body)
    assert site["handler"].peak == 1 and len(site["handler"].hits) >= 2


def test_idle_timeout_drops_the_page_and_does_not_replay(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")])), "typescript")["code"]
    driver = (
        "const alias = Object.keys(BROWSER_POLICY)[0];\n"
        f"const first = await browserCall(alias, 'navigate', {{ url: {json.dumps(site['url'])} }}, {{}});\n"
        "sessions.get(alias).touched = Date.now() / 1000 - 100000;\n"
        "let idle = null;\n"
        "try { await browserCall(alias, 'snapshot', {}, {}); } catch (error) { idle = error.code; }\n"
        "const pageAfter = sessions.get(alias).page.url;\n"
        f"const again = await browserCall(alias, 'navigate', {{ url: {json.dumps(site['url'])} }}, {{}});\n"
        "console.log(JSON.stringify({ idle, pageAfter, again: again.status, first: first.status }));\n"
    )
    body = _body(_run(tmp_path, code, driver))
    assert body["idle"] == "session_lost" and body["pageAfter"] == "" and body["again"] == "confirmed"
    assert len(site["handler"].hits) == 2


def test_profile_missing_and_playwright_refuses_loopback(c, site, tmp_path):
    owner = user(c)
    origin = "https://allowed.test:8443"
    seed = {"cookies": [{"name": "login", "value": "synthetic-cookie", "domain": "allowed.test", "path": "/", "expires": -1,
                         "httpOnly": True, "secure": True, "sameSite": "Lax"}],
            "origins": [{"origin": origin, "localStorage": [{"name": "login", "value": "synthetic-storage"}]}]}
    response = create(c, owner, settings={"allowed_origins": [origin], "profile": {"name": "fixture-profile", "origins": [origin]}},
                      secrets={"profile_state": json.dumps(seed)})
    assert response.status_code == 200, response.text
    sid = response.json()["data"]["id"]
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": origin + "/"}, "page")])), "typescript")["code"]
    assert "synthetic-cookie" not in code and "synthetic-storage" not in code
    assert "SUPERSTEP_BROWSER_PROFILE_BROWSER_1" in code
    profile = _body(_run(tmp_path, code, '''
const alias = Object.keys(BROWSER_POLICY)[0];
process.env.SUPERSTEP_BROWSER_DRIVER = "memory";
try { await browserCall(alias, "navigate", { url: "https://allowed.test:8443/" }, {}); console.log(JSON.stringify({ code: "opened" })); }
catch (error) { console.log(JSON.stringify({ code: error.code })); }
'''))
    assert profile["code"] == "profile_missing"
    local = _server(c, owner, site["origin"])
    private_code = _code(c, owner, _save(c, owner, _chain(local, [_mcp(local, "open", "navigate", {"url": site["url"]}, "page")])), "typescript")["code"]
    private = _body(_run(tmp_path, private_code, (
        "const alias = Object.keys(BROWSER_POLICY)[0];\n"
        "process.env.SUPERSTEP_BROWSER_DRIVER = 'playwright';\n"
        f"try {{ await browserCall(alias, 'navigate', {{ url: {json.dumps(site['url'])} }}, {{}}); console.log(JSON.stringify({{ code: 'opened' }})); }}\n"
        "catch (error) { console.log(JSON.stringify({ code: error.code })); }\n"
    )))
    assert private["code"] == "private_address"
    assert not site["handler"].hits


def test_invalid_browser_settings_stay_a_placeholder(c, site):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    row = McpServerRepository(get_db()).get(sid)
    row.settings = "{}"
    McpServerRepository(get_db()).save(row)
    data = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")])), "typescript")
    assert data["managed_placeholders"] is True
    assert "browserCall(" not in data["code"]
    assert "Managed connection placeholder" in data["code"] or "managedOperation" in data["code"]
