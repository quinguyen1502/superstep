"""Executable Python browser export (TASK-0251).

The generated file is executed with ``python -I`` so it cannot import Superstep.
"""
import ast
import json
import os
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

import pytest

from app.api.deps import get_db
from app.engine.browser_export import public_policy
from app.repositories import McpServerRepository
from tests.test_browser_connections import create
from tests.test_chat_trigger_runs import H, c, user

HTML = """<html><head><title>Track</title></head><body>
<input id="order" aria-label="Order ID" placeholder="Order ID" />
<button id="go">Track shipment</button>
<p id="status" role="status">In transit</p>
<a id="next" href="/next">Next</a>
</body></html>"""
NEXT = """<html><head><title>Next</title></head><body>
<p id="status" role="status">Delivered</p>
</body></html>"""
SECRETS = {
    "browserless_token": "fixture-browserless-token",
    "proxy_username": "fixture-user",
    "proxy_password": "fixture-password",
}
PROXY = "http://proxy.example:8080"


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


def test_public_policy_omits_secrets_and_rejects_invalid_settings():
    assert public_policy({}) is None
    policy = public_policy({
        "provider": "browserless",
        "allowed_origins": ["https://example.com"],
        "proxy": {"mode": "custom", "server": PROXY, "auth": "basic"},
        "allow_upload": True,
    })
    assert policy["provider"] == "browserless"
    assert policy["proxy"]["server"] == PROXY
    assert "password" not in json.dumps(policy) and "token" not in json.dumps(policy)


def _server(c, owner, origin, **settings):
    response = create(c, owner, settings={"allowed_origins": [origin], **settings})
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def _save(c, owner, graph):
    response = c.post("/api/workflows", headers=H(owner["token"]), json=graph)
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def _code(c, owner, wid, language="python"):
    response = c.get(f"/api/workflows/{wid}/code?language={language}", headers=H(owner["token"]))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _run(tmp_path, code, driver, env=None):
    """Run the export as ``__main__``. LangGraph resolves annotations in that module."""
    folder = tmp_path / uuid.uuid4().hex
    folder.mkdir()
    guard = 'if __name__ == "__main__":\n    main()\n'
    assert guard in code
    (folder / "graph.py").write_text(code.replace(guard, "") + "\n" + driver)
    base = {k: v for k, v in os.environ.items() if k != "PYTHONPATH" and not k.startswith("SUPERSTEP_BROWSER")}
    if env:
        base.update(env)
    return subprocess.run([sys.executable, "-I", "graph.py"], cwd=folder, env=base, capture_output=True, text=True, timeout=90)


def _mcp(sid, nid, tool, arguments, output, **extra):
    return {"id": nid, "type": "mcp", "position": {"x": 0, "y": 0},
            "data": {"label": nid, "server_id": sid, "tool": tool, "arguments": arguments, "output_field": output, **extra}}


def _chain(sid, nodes):
    state = [
        {"name": "url", "type": "string"}, {"name": "order_id", "type": "string"},
        {"name": "page", "type": "object"}, {"name": "fill_result", "type": "object"},
        {"name": "shipment", "type": "object"}, {"name": "shot", "type": "object"},
    ]
    built = [{"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}}]
    built += nodes
    built.append({"id": "end", "type": "end", "position": {"x": 0, "y": 0}, "data": {}})
    edges = [{"id": f"e{i}", "source": built[i]["id"], "target": built[i + 1]["id"]} for i in range(len(built) - 1)]
    return {"name": "Browser export", "state": state, "nodes": built, "edges": edges}


def _recipe(sid):
    graph = _chain(sid, [
        _mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page"),
        _mcp(sid, "fill", "fill", {"value": "{{state.order_id}}"}, "fill_result",
             target={"observation_field": "page", "role": "textbox", "text": "Order ID"}),
        _mcp(sid, "read", "extract", {}, "shipment",
             targets={"status": {"observation_field": "page", "role": "status", "text": "In transit"}}),
    ])
    graph["browser_recipe"] = {"version": 1, "connection_id": sid, "inputs": ["url", "order_id"], "outputs": ["shipment"]}
    return graph


def test_recipe_runs_outside_superstep_without_secrets_or_a_fixed_url(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    wid = _save(c, owner, _recipe(sid))
    data = _code(c, owner, wid)
    assert data["managed_placeholders"] is False
    assert "def browser_call(" in data["code"]
    assert "call_mcp_tool(" not in data["code"] and "managed_operation(" not in data["code"]
    assert sid not in data["code"]
    assert "https://example.com" not in data["code"]
    assert all(secret not in data["code"] for secret in SECRETS.values())
    tree = ast.parse(data["code"])
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert "app" not in imported and "playwright" not in imported
    saved = c.get(f"/api/workflows/{wid}", headers=H(owner["token"])).json()["data"]
    assert "_browser_export" not in json.dumps(saved) and "_managed_export" not in json.dumps(saved)
    typescript = _code(c, owner, wid, "typescript")
    assert "function browserCall(" in typescript["code"] or "async function browserCall(" in typescript["code"]
    assert "callMcpTool(" not in typescript["code"] and "managedOperation(" not in typescript["code"]
    driver = (
        "import json\n"
        f"final = build_graph().invoke({{'url': {site['url']!r}, 'order_id': 'SO-1'}})\n"
        "print(json.dumps(final))\n"
    )
    done = _run(tmp_path, data["code"], driver)
    assert done.returncode == 0, done.stderr[-3000:]
    final = json.loads(done.stdout)
    assert final["shipment"]["fields"]["status"] == "In transit"
    assert final["fill_result"] == {"status": "confirmed", "operation": "fill", "sequence": final["fill_result"]["sequence"], "filled": True}
    assert "SO-1" not in json.dumps(final["fill_result"])
    assert site["handler"].hits and all(auth is None for _, auth in site["handler"].hits)
    project = c.get(f"/api/workflows/{wid}/export/python/project", headers=H(owner["token"]))
    assert project.status_code == 200, project.text
    with zipfile.ZipFile(BytesIO(project.content)) as archive:
        files = {name.split("/", 1)[1]: archive.read(name).decode() for name in archive.namelist()}
    assert "def browser_call(" in files["README.md"] or "memory" in files["README.md"]
    assert "refused outside Studio" in files["README.md"] or "Upload and download are refused" in files["README.md"]
    example = files[".env.example"]
    assert "SUPERSTEP_BROWSER_DRIVER=" in example
    assert "SUPERSTEP_BROWSER_TOKEN_BROWSER_1=" in example
    assert "SUPERSTEP_BROWSER_FAULT=" in example
    assert all(not line.startswith("SUPERSTEP_BROWSER_") or line.endswith("=") for line in example.splitlines())
    assert "playwright" not in files["requirements.txt"]
    assert "langgraph" in files["requirements.txt"]
    assert all(secret not in project.content.decode(errors="ignore") for secret in SECRETS.values())


def test_child_recipe_export_calls_the_helper(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    child = _save(c, owner, _recipe(sid))
    parent = _chain(sid, [])
    parent["name"] = "Parent"
    parent["nodes"] = [
        {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
        {"id": "child", "type": "subgraph", "position": {"x": 0, "y": 0}, "data": {"workflow_id": child}},
        {"id": "end", "type": "end", "position": {"x": 0, "y": 0}, "data": {}},
    ]
    parent["edges"] = [
        {"id": "e1", "source": "start", "target": "child"},
        {"id": "e2", "source": "child", "target": "end"},
    ]
    wid = _save(c, owner, parent)
    data = _code(c, owner, wid)
    assert data["managed_placeholders"] is False
    assert "browser_call(" in data["code"] and sid not in data["code"]
    driver = (
        "import json\n"
        f"final = build_graph().invoke({{'url': {site['url']!r}, 'order_id': 'SO-9'}})\n"
        "print(json.dumps(final))\n"
    )
    done = _run(tmp_path, data["code"], driver)
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout)["shipment"]["fields"]["status"] == "In transit"


def test_fixed_binding_is_used_and_model_binding_is_not_replaced(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    fixed = _chain(sid, [_mcp(sid, "open", "navigate", {}, "page", url_binding={"source": "fixed", "value": site["url"]})])
    model = _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page", url_binding={"source": "model"})])
    fixed_code = _code(c, owner, _save(c, owner, fixed))["code"]
    model_code = _code(c, owner, _save(c, owner, model))["code"]
    assert site["url"] in fixed_code
    assert "https://fixed.example/should-not-be-used" not in model_code
    driver = (
        "import json\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        f"opened = browser_call(alias, 'navigate', {{'url': {site['url']!r}}}, {{}})\n"
        "try:\n"
        "    browser_call(alias, 'navigate', {}, {})\n"
        "    missing = None\n"
        "except BrowserError as error:\n"
        "    missing = error.code\n"
        "print(json.dumps({'opened': opened['url'], 'missing': missing}))\n"
    )
    done = _run(tmp_path, model_code, driver)
    assert done.returncode == 0, done.stderr[-3000:]
    body = json.loads(done.stdout)
    assert body["opened"] == site["url"] and body["missing"] == "missing_url"
    fixed_driver = (
        "import json\n"
        "final = build_graph().invoke({})\n"
        "print(json.dumps(final['page']['url']))\n"
    )
    fixed_done = _run(tmp_path, fixed_code, fixed_driver)
    assert fixed_done.returncode == 0, fixed_done.stderr[-3000:]
    assert json.loads(fixed_done.stdout) == site["url"]


def test_secrets_stay_in_the_environment_and_failures_do_not_open_a_page(c, site, tmp_path):
    owner = user(c)
    settings = {
        "provider": "browserless",
        "allowed_origins": [site["origin"]],
        "proxy": {"mode": "custom", "server": PROXY, "auth": "basic"},
    }
    response = create(c, owner, settings=settings, secrets=SECRETS)
    assert response.status_code == 200, response.text
    sid = response.json()["data"]["id"]
    wid = _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")]))
    data = _code(c, owner, wid)
    assert all(secret not in data["code"] for secret in SECRETS.values())
    assert PROXY in data["code"] and sid not in data["code"]
    driver = (
        "import json, os\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        "env = BROWSER_POLICY[alias]['env']\n"
        f"url = {site['url']!r}\n"
        "def call():\n"
        "    try:\n"
        "        browser_call(alias, 'navigate', {'url': url}, {})\n"
        "        return None\n"
        "    except BrowserError as error:\n"
        "        return error.code\n"
        "missing = call()\n"
        "os.environ[env['token']] = 'runtime-token'\n"
        "os.environ[env['endpoint']] = 'https://browserless.example/'\n"
        "proxy = call()\n"
        "print(json.dumps({'missing': missing, 'proxy': proxy}))\n"
    )
    done = _run(tmp_path, data["code"], driver)
    assert done.returncode == 0, done.stderr[-3000:]
    body = json.loads(done.stdout)
    assert body["missing"] == "token_missing" and body["proxy"] == "proxy_credentials_missing"
    assert not site["handler"].hits


def test_approval_stale_lost_unknown_and_whitelist(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"], require_mutating_approval=True, allow_upload=True, allow_evaluate_js=True, max_actions=8)
    wid = _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")]))
    code = _code(c, owner, wid)["code"]
    driver = r'''
import json, os
alias = next(iter(BROWSER_POLICY))
url = os.environ["FIXTURE_URL"]
nxt = os.environ["FIXTURE_NEXT"]
out = {}
opened = browser_call(alias, "navigate", {"url": url}, {})
obs = opened["observation"]["observation_id"]
browser_decide = lambda *args: False
try:
    browser_call(alias, "click", {"observation_id": obs, "element_id": "go"}, {})
    out["reject"] = None
except BrowserError as error:
    out["reject"] = error.code
browser_decide = lambda *args: {"text": "yes"}
try:
    browser_call(alias, "click", {"observation_id": obs, "element_id": "go"}, {})
    out["model"] = None
except BrowserError as error:
    out["model"] = error.code
out["url_after_reject"] = _sessions[alias].page.url
browser_decide = lambda *args: {"approved": True}
clicked = browser_call(alias, "click", {"observation_id": obs, "element_id": "go"}, {})
out["clicked"] = clicked["status"]
again = browser_call(alias, "navigate", {"url": nxt}, {})
try:
    browser_call(alias, "click", {"observation_id": obs, "element_id": "go"}, {})
    out["stale"] = None
except BrowserError as error:
    out["stale"] = error.code
out["url_after_stale"] = _sessions[alias].page.url
os.environ["SUPERSTEP_BROWSER_FAULT"] = "unknown"
try:
    browser_call(alias, "click", {"observation_id": again["observation"]["observation_id"], "element_id": "status"}, {})
    out["unknown"] = None
except BrowserError as error:
    out["unknown"] = error.code
out["fault_cleared"] = os.environ.get("SUPERSTEP_BROWSER_FAULT")
out["url_after_unknown"] = _sessions[alias].page.url
os.environ["SUPERSTEP_BROWSER_FAULT"] = "lost"
try:
    browser_call(alias, "navigate", {"url": url}, {})
    out["lost"] = None
except BrowserError as error:
    out["lost"] = error.code
out["lost_cleared"] = os.environ.get("SUPERSTEP_BROWSER_FAULT")
recovered = browser_call(alias, "navigate", {"url": url}, {})
out["recovered"] = recovered["status"]
try:
    browser_call(alias, "navigate", {"url": "https://example.com/"}, {})
    out["denied"] = None
except BrowserError as error:
    out["denied"] = error.code
shot = browser_call(alias, "screenshot", {}, {})
out["shot"] = shot
title = browser_call(alias, "evaluate", {"observation_id": recovered["observation"]["observation_id"], "expression": "document.title"}, {})
out["title"] = title["value"]
try:
    browser_call(alias, "evaluate", {"observation_id": recovered["observation"]["observation_id"], "expression": "alert(1)"}, {})
    out["js"] = None
except BrowserError as error:
    out["js"] = error.code
try:
    browser_call(alias, "upload", {"observation_id": recovered["observation"]["observation_id"], "element_id": "order", "source_kind": "attachment", "source_id": "file-1"}, {})
    out["upload"] = None
except BrowserError as error:
    out["upload"] = error.code
    out["upload_message"] = str(error)
print(json.dumps(out))
'''
    done = _run(tmp_path, code, driver, {"FIXTURE_URL": site["url"], "FIXTURE_NEXT": site["next"]})
    assert done.returncode == 0, done.stderr[-3000:]
    body = json.loads(done.stdout)
    assert body["reject"] == "approval_rejected" and body["model"] == "approval_rejected"
    assert body["url_after_reject"].rstrip("/").endswith(str(site["url"]).split("/")[-2] or site["url"]) or body["url_after_reject"] == site["url"]
    assert body["clicked"] == "confirmed" and body["stale"] == "stale_observation"
    assert body["url_after_stale"] == site["next"]
    assert body["unknown"] == "unknown_effect" and body["fault_cleared"] is None
    assert body["url_after_unknown"] == site["next"]
    assert body["lost"] == "session_lost" and body["lost_cleared"] is None and body["recovered"] == "confirmed"
    assert body["denied"] == "whitelist_denied"
    assert body["shot"]["captured"] is True and body["shot"]["inline_bytes"] is False
    assert body["title"] == "Track" and body["js"] == "capability_refused"
    assert body["upload"] == "capability_refused" and "refused outside Studio" in body["upload_message"] and "True" in body["upload_message"]


def test_same_session_commands_do_not_overlap(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {}, "page")])))["code"]
    driver = (
        "import json, threading\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        f"url = {site['slow']!r}\n"
        "results, errors = [], []\n"
        "def one():\n"
        "    try: results.append(browser_call(alias, 'navigate', {'url': url}, {}))\n"
        "    except Exception as error: errors.append(str(error))\n"
        "threads = [threading.Thread(target=one) for _ in range(2)]\n"
        "[item.start() for item in threads]\n"
        "[item.join() for item in threads]\n"
        "print(json.dumps({'errors': errors, 'sequences': sorted(item['sequence'] for item in results), 'peak': _sessions[alias].peak}))\n"
    )
    done = _run(tmp_path, code, driver)
    assert done.returncode == 0, done.stderr[-3000:]
    body = json.loads(done.stdout)
    assert body["errors"] == [] and body["sequences"] == [1, 2] and body["peak"] == 1
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
                     "label": "Browser", "prompt": "{{state.message}}", "output_field": "answer", "tools": [tool("navigate_a"), tool("navigate_b")]}},
                 {"id": "end", "type": "end", "position": {"x": 2, "y": 0}, "data": {}},
             ],
             "edges": [{"id": "e1", "source": "start", "target": "ag"}, {"id": "e2", "source": "ag", "target": "end"}]}
    code = _code(c, owner, _save(c, owner, graph))["code"]
    assert "browser_call(" in code and site["slow"] in code and sid not in code
    typescript = _code(c, owner, _save(c, owner, graph), "typescript")["code"]
    assert "browserCall(" in typescript and "callMcpTool(" not in typescript
    driver = (
        "import json\n"
        "final = build_graph().invoke({'message': 'navigate_a navigate_b'})\n"
        "print(json.dumps(final['answer']))\n"
    )
    done = _run(tmp_path, code, driver)
    assert done.returncode == 0, done.stderr[-3000:]
    assert "confirmed" in done.stdout
    assert site["handler"].peak == 1 and len(site["handler"].hits) >= 2


def test_idle_timeout_drops_the_page_and_does_not_replay(c, site, tmp_path):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")])))["code"]
    driver = (
        "import json\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        f"first = browser_call(alias, 'navigate', {{'url': {site['url']!r}}}, {{}})\n"
        "session = _sessions[alias]\n"
        "session.touched = time.monotonic() - 100000\n"
        "try:\n"
        "    browser_call(alias, 'snapshot', {}, {})\n"
        "    idle = None\n"
        "except SessionLost as error:\n"
        "    idle = error.code\n"
        "page_after = _sessions[alias].page.url\n"
        f"again = browser_call(alias, 'navigate', {{'url': {site['url']!r}}}, {{}})\n"
        "print(json.dumps({'idle': idle, 'page_after': page_after, 'again': again['status'], 'hits': None}))\n"
    )
    done = _run(tmp_path, code, driver)
    assert done.returncode == 0, done.stderr[-3000:]
    body = json.loads(done.stdout)
    assert body["idle"] == "session_lost"
    assert body["page_after"] == ""
    assert body["again"] == "confirmed"
    assert len(site["handler"].hits) == 2


def test_invalid_browser_settings_stay_a_placeholder(c, site):
    owner = user(c)
    sid = _server(c, owner, site["origin"])
    row = McpServerRepository(get_db()).get(sid)
    row.settings = "{}"
    McpServerRepository(get_db()).save(row)
    data = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "{{state.url}}"}, "page")])))
    assert data["managed_placeholders"] is True
    assert "browser_call(" not in data["code"]
    assert "Managed connection placeholder" in data["code"]


def test_profile_and_private_drivers_fail_closed(c, site, tmp_path):
    owner = user(c)
    origin = "https://allowed.test:8443"
    seed = {"cookies": [{"name": "login", "value": "synthetic-cookie", "domain": "allowed.test", "path": "/", "expires": -1,
                         "httpOnly": True, "secure": True, "sameSite": "Lax"}],
            "origins": [{"origin": origin, "localStorage": [{"name": "login", "value": "synthetic-storage"}]}]}
    response = create(c, owner, settings={"allowed_origins": [origin], "profile": {"name": "fixture-profile", "origins": [origin]}},
                      secrets={"profile_state": json.dumps(seed)})
    assert response.status_code == 200, response.text
    sid = response.json()["data"]["id"]
    code = _code(c, owner, _save(c, owner, _chain(sid, [_mcp(sid, "open", "navigate", {"url": "https://allowed.test:8443/"}, "page")])))["code"]
    assert "synthetic-cookie" not in code and "synthetic-storage" not in code
    assert "SUPERSTEP_BROWSER_PROFILE_BROWSER_1" in code
    profile_driver = (
        "import json, os\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        "os.environ['SUPERSTEP_BROWSER_DRIVER'] = 'memory'\n"
        "try:\n"
        "    browser_call(alias, 'navigate', {'url': 'https://allowed.test:8443/'}, {})\n"
        "    print('opened')\n"
        "except BrowserError as error:\n"
        "    print(error.code)\n"
    )
    profile = _run(tmp_path, code, profile_driver)
    assert profile.returncode == 0, profile.stderr[-3000:]
    assert profile.stdout.strip() == "profile_missing"
    local = _server(c, owner, site["origin"])
    private_code = _code(c, owner, _save(c, owner, _chain(local, [_mcp(local, "open", "navigate", {"url": site["url"]}, "page")])))["code"]
    private_driver = (
        "import os\n"
        "alias = next(iter(BROWSER_POLICY))\n"
        "os.environ['SUPERSTEP_BROWSER_DRIVER'] = 'playwright'\n"
        "try:\n"
        "    browser_call(alias, 'navigate', {'url': " + repr(site["url"]) + "}, {})\n"
        "    print('opened')\n"
        "except BrowserError as error:\n"
        "    print(error.code)\n"
    )
    private = _run(tmp_path, private_code, private_driver)
    assert private.returncode == 0, private.stderr[-3000:]
    assert private.stdout.strip() == "private_address"
    assert not site["handler"].hits
