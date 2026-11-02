"""Configured HTTP tools: no runtime target/auth override, no unsafe replay or credential disclosure."""
import copy, json, threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import httpx, pytest
from app.api.deps import mcp_service, get_db
from app.core.errors import AppError
from app.repositories import McpServerRepository
from app.services.managed_tools import http_api, base
from tests.test_chat_trigger_runs import c, api, user, H

SECRET = "fixture-http-key-never-return"
TOOL = {"name": "create_record", "method": "POST", "path": "/records", "input_schema": {
    "type": "object", "additionalProperties": False, "required": ["text"], "properties": {"text": {"type": "string", "maxLength": 100}}},
    "response_schema": {"type": "object", "required": ["ok"], "properties": {"ok": {"const": True}}}}


@contextmanager
def error(code):
    with pytest.raises(AppError) as caught: yield
    assert caught.value.code == code


def create(c, owner, tools=None, settings=None, headers=None):
    return c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "HTTP fixture", "transport": "managed", "adapter": "http_api",
        "settings": settings or {"base_url": "https://fixture.example.test/v1", "tools_json": json.dumps(tools if tools is not None else [TOOL])},
        "secrets": {"headers": json.dumps(headers if headers is not None else {"Authorization": "Bearer " + SECRET})}})


@pytest.fixture
def remote(monkeypatch):
    state = {"calls": [], "status": 200, "data": {"ok": True, "id": "fixture-1"}, "mode": "ok", "entered": threading.Event(), "release": threading.Event()}
    def request(method, url, **kwargs):
        state["calls"].append((method, url, kwargs))
        if state["mode"] == "timeout": raise httpx.ReadTimeout(SECRET)
        if state["mode"] == "block": state["entered"].set(); state["release"].wait(5)
        if state["mode"] == "malformed": return httpx.Response(200, content=b"not JSON " + SECRET.encode())
        if state["mode"] == "oversized": return httpx.Response(200, content=b"x" * (http_api.MAX_RESPONSE + 1))
        if state["status"] == 204: return httpx.Response(204)
        return httpx.Response(state["status"], json=state["data"])
    monkeypatch.setattr(http_api, "request", request)
    return state


def test_discovery_encryption_fixed_target_redaction_and_replay(c, remote):
    owner = user(c); response = create(c, owner); assert response.status_code == 200, response.text
    server = response.json()["data"]; sid = server["id"]; svc = mcp_service()
    assert SECRET not in json.dumps(server)
    assert SECRET not in McpServerRepository(get_db()).get(sid).secrets
    assert svc.discover(sid, owner["id"])["tools"][0]["name"] == "create_record" and not remote["calls"]
    remote["data"] = {"ok": True, "echo": "Bearer " + SECRET, SECRET: SECRET, "nested": [SECRET], "$ref": "ordinary API data"}
    result = svc.call(owner["id"], sid, "create_record", {"text": "hello"}, operation_key="fixed-key")
    assert result["outcome"] == "confirmed" and SECRET not in json.dumps(result)
    assert result["data"]["$ref"] == "ordinary API data"
    method, url, options = remote["calls"][0]
    assert (method, url, options["json"]) == ("POST", "https://fixture.example.test/v1/records", {"text": "hello"})
    assert options["headers"]["Authorization"] == "Bearer " + SECRET and options["headers"]["Idempotency-Key"] == "fixed-key"
    assert svc.call(owner["id"], sid, "create_record", {"text": "hello"}, operation_key="fixed-key") == result
    assert len(remote["calls"]) == 1 and SECRET not in json.dumps(svc.operations(owner["id"], sid))
    with error("MANAGED_OPERATION_CONFLICT"):
        svc.call(owner["id"], sid, "create_record", {"text": "different"}, operation_key="fixed-key")
    with error("MCP_ARGUMENT_INVALID"):
        svc.call(owner["id"], sid, "create_record", {"text": "hello", "url": "https://another.test"}, operation_key="bad-input")
    assert len(remote["calls"]) == 1


def test_get_query_multiple_tools_edit_schema_and_empty_204(c, remote):
    owner = user(c); lookup = {"name": "lookup", "method": "GET", "path": "/records/search", "input_schema": {
        "type": "object", "additionalProperties": False, "properties": {"limit": {"type": "integer"}, "text": {"type": "string"}}}}
    server = create(c, owner, [TOOL, lookup]).json()["data"]; svc = mcp_service()
    result = svc.call(owner["id"], server["id"], "lookup", {"limit": "3", "text": "a & b"}, operation_key="query")
    assert result["http_status"] == 200
    assert remote["calls"][0][2]["params"] == {"limit": 3, "text": "a & b"} and "json" not in remote["calls"][0][2]
    changed = {**TOOL, "method": "PATCH", "path": "/records/fixed", "success_statuses": [204]}; changed.pop("response_schema")
    update = c.put(f"/api/mcp/servers/{server['id']}", headers=H(owner["token"]), json={"name": "Edited HTTP", "settings": {
        "base_url": "https://fixture.example.test/v1", "tools_json": json.dumps([changed])}, "secrets": {"headers": None}})
    assert update.status_code == 200, update.text
    remote["data"] = None; remote["status"] = 204
    result = svc.call(owner["id"], server["id"], "create_record", {"text": "changed"}, operation_key="patch")
    assert result["data"] is None and remote["calls"][-1][0] == "PATCH"
    assert remote["calls"][-1][2]["headers"]["Authorization"] == "Bearer " + SECRET
    with error("MANAGED_OPERATION_CONFLICT"):
        svc.call(owner["id"], server["id"], "create_record", {"text": "changed"}, operation_key="query")


@pytest.mark.parametrize("url", ["file:///tmp/test", "http://api.example.test", "https://user:secret@api.example.test", "https://api.example.test?token=secret", "https://api.example.test/#fragment", "https://api.example.test:99999", "https://api.example.test/\\other", "https://api.example.test/\n"])
def test_unsafe_base_urls_are_rejected(c, monkeypatch, url):
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "0")
    response = create(c, user(c), settings={"base_url": url, "tools_json": json.dumps([TOOL])})
    assert response.status_code == 400 and response.json()["error"]["code"] == "MCP_CONFIG_INVALID"


@pytest.mark.parametrize("change", [
    {"path": "//another.test/records"}, {"path": "/../records"}, {"path": "/%2e%2e/records"}, {"path": "/{target}"},
    {"path": "/records?token=value"}, {"method": "CONNECT"}, {"success_statuses": [202]},
    {"input_schema": {"type": "object", "additionalProperties": False, "properties": {"text": {"$ref": "https://another.test/schema"}}}},
    {"input_schema": {"type": "object"}}, {"response_schema": {"$dynamicRef": "https://another.test/schema"}},
])
def test_unsafe_tool_definitions_are_rejected(c, change):
    response = create(c, user(c), tools=[{**TOOL, **change}])
    assert response.status_code == 400 and response.json()["error"]["code"] == "MCP_CONFIG_INVALID"


@pytest.mark.parametrize("headers", [{"Host": "another.test"}, {"Authorization": "bad\r\nHost: other"}, {"Idempotency-Key": "replace-key"},
    {"Proxy-Authorization": "secret"}, {"Cookie": "session=secret"}, {"authorization": "a", "Authorization": "b"}, {"X-Key": 42}])
def test_unsafe_headers_are_rejected(c, headers):
    response = create(c, user(c), headers=headers)
    assert response.status_code == 400 and response.json()["error"]["code"] == "MCP_CONFIG_INVALID"


@pytest.mark.parametrize("mode,status,data", [("timeout", 200, {}), ("malformed", 200, {}), ("oversized", 200, {}),
    ("ok", 202, {"ok": True}), ("ok", 503, {"ok": True}), ("ok", 408, {}), ("ok", 200, {"ok": False})])
def test_uncertain_outcomes_never_repeat_or_leak(c, remote, mode, status, data):
    owner = user(c); server = create(c, owner).json()["data"]; svc = mcp_service()
    remote.update(mode=mode, status=status, data=data)
    for _ in range(2):
        with pytest.raises(AppError) as caught:
            svc.call(owner["id"], server["id"], "create_record", {"text": "hello"}, operation_key="uncertain")
        assert caught.value.code == "MANAGED_OUTCOME_UNKNOWN" and SECRET not in str(caught.value)
    [operation] = svc.operations(owner["id"], server["id"])
    with error("MANAGED_OUTCOME_UNKNOWN"): svc.reconcile(owner["id"], server["id"], operation["operation_id"])
    assert len(remote["calls"]) == 1


def test_rejection_permissions_mock_and_concurrency(c, remote):
    owner, stranger = user(c), user(c); server = create(c, owner).json()["data"]; svc = mcp_service(); sid = server["id"]
    with error("MCP_SERVER_NOT_FOUND"): svc.call(stranger["id"], sid, "create_record", {"text": "hello"}, operation_key="forbidden")
    assert svc.call(owner["id"], sid, "create_record", {"text": "hello"}, dry_run=True)["outcome"] == "dry_run"
    assert not remote["calls"] and not svc.operations(owner["id"], sid)
    remote["status"] = 403
    for _ in range(2):
        with error("MCP_TOOL_FAILED"): svc.call(owner["id"], sid, "create_record", {"text": "hello"}, operation_key="rejected")
    assert len(remote["calls"]) == 1
    remote.update(status=200, mode="block")
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(svc.call, owner["id"], sid, "create_record", {"text": "hello"}, operation_key="concurrent")
        assert remote["entered"].wait(5)
        try:
            with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], sid, "create_record", {"text": "hello"}, operation_key="concurrent")
        finally: remote["release"].set()
        assert future.result()["outcome"] == "confirmed"
    assert len(remote["calls"]) == 2


def test_configuration_and_response_bounds_and_real_pinned_stream(c, monkeypatch):
    adapter = http_api.HttpApiTools()
    definitions = [{**copy.deepcopy(TOOL), "name": "operation_" + str(index), "description": "x" * 900} for index in range(6)]
    settings = {"base_url": "https://fixture.example.test", "tools_json": json.dumps(definitions)}
    adapter.validate("owner", settings, {})  # deliberately larger than the old 4 KiB settings ceiling
    assert create(c, user(c), settings=settings).status_code == 200
    for definitions in ([], [TOOL] * 21, [TOOL, TOOL]):
        with error("MCP_CONFIG_INVALID"): adapter.validate("owner", {**settings, "tools_json": json.dumps(definitions)}, {})
    too_deep = None
    for _ in range(18): too_deep = [too_deep]
    with pytest.raises(ValueError): http_api.bounded(too_deep)
    monkeypatch.setattr(base, "public_address", lambda url, *a: (url, "93.184.216.34"))
    seen = []
    def transport(request):
        seen.append(request)
        return httpx.Response(200, content=b"x" * 1000)
    monkeypatch.setattr(base, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(transport), follow_redirects=False))
    with pytest.raises(httpx.DecodingError): base.request("GET", settings["base_url"], max_bytes=100)
    assert str(seen[0].url) == "https://93.184.216.34" and seen[0].headers["host"] == "fixture.example.test"
    assert seen[0].extensions["sni_hostname"] == "fixture.example.test"
