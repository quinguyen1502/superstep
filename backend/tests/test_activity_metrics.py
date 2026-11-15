"""Integration activity metrics: channels, MCP, browser, sandbox, product limits; bounded labels only."""
import asyncio, sys, types, uuid
import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.core.errors import AppError
from app.engine import activity, code_runtime as cr, mcp_client
from app.engine.code_languages import LANGUAGES
from app.engine.sandbox import container
from app.services import email_quota, rate_limit
from app.services.approval_channels import ADAPTERS
from app.services.browser_session_service import BrowserRunScope, BrowserSessionService
from app.services.chat_run_service import ChatRunService
from app.services.mcp_service import TRANSPORTS, McpService
from app.services.rate_limit import SCOPES, InMemoryCounter, InMemoryRateLimiter
from app.services.telemetry import ENUMS, LABELS, Telemetry, labels

FORBIDDEN = {"user_id", "run_id", "user", "owner", "server", "server_id", "url", "name", "key", "ip", "connection"}
SECRET = "srv-secret-name"


@pytest.fixture
def events():
    got = []; fn = lambda e, f: got.append((e, dict(f)))
    activity.observe(fn); yield got; activity.unobserve(fn)


@pytest.fixture
def metered():
    reader = InMemoryMetricReader(); t = Telemetry(exporters=[], metric_readers=[reader])
    activity.observe(t.activity_event); yield reader; activity.unobserve(t.activity_event)


def points(reader) -> dict:
    out = {}
    data = reader.get_metrics_data()
    for rm in (data.resource_metrics if data else []):
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                for p in m.data.data_points:
                    out.setdefault(m.name, []).append((getattr(p, "count", getattr(p, "value", None)), dict(p.attributes)))
    return out


def bounded(pts: dict):
    for name, items in pts.items():
        for _, a in items:
            assert set(a) <= LABELS and not (set(a) & FORBIDDEN), (name, a)
            assert not any(SECRET in str(v) or "user-1" in str(v) or "10.1.2.3" in str(v) for v in a.values()), (name, a)


def test_enums_match_the_product_lists():
    assert ENUMS["kind"] == set(ADAPTERS) and ENUMS["transport"] == set(TRANSPORTS)
    assert ENUMS["runtime"] == set(cr.RUNNERS) and ENUMS["language"] == set(LANGUAGES)
    assert set(SCOPES.values()) | {"login", "identity_code", "other"} == ENUMS["scope"]
    assert labels(kind="slack", transport="carrier-pigeon", scope="x:user-1") == {"kind": "slack", "transport": "other", "scope": "other"}


# ---- MCP ----

def mcp_service(monkeypatch, transport="http"):
    svc = McpService.__new__(McpService)
    row = types.SimpleNamespace(id="s1", name=SECRET, scope="user", transport=transport, url=f"https://{SECRET}.example.com",
                                tools='[{"name": "add", "input_schema": {}}]')
    monkeypatch.setattr(svc, "_visible", lambda sid, uid: row, raising=False)
    monkeypatch.setattr(svc, "_spec", lambda r: {"transport": "http", "url": r.url}, raising=False)
    return svc


def test_mcp_calls_by_transport_with_codes(monkeypatch, metered):
    svc = mcp_service(monkeypatch)
    monkeypatch.setattr(mcp_client, "call_tool", lambda spec, tool, args, timeout=None: {"sum": 2})
    assert svc.call("user-1", "s1", "add", {}) == {"sum": 2}
    def boom(*a, **k): raise mcp_client.McpError("MCP_CONNECT_FAILED", f"cannot reach {SECRET}")
    monkeypatch.setattr(mcp_client, "call_tool", boom)
    with pytest.raises(AppError) as e: svc.call("user-1", "s1", "add", {})
    assert e.value.code == "MCP_CONNECT_FAILED"
    pts = points(metered); bounded(pts)
    calls = {(a["transport"], a["status"], a["code"]): v for v, a in pts["studio.mcp.calls"]}
    assert calls == {("http", "ok", ""): 1, ("http", "error", "MCP_CONNECT_FAILED"): 1}
    assert sum(c for c, _ in pts["studio.mcp.duration"]) == 2


# ---- sandbox ----

@pytest.fixture
def local(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    monkeypatch.setattr(cr, "unavailable", lambda *_: None)
    monkeypatch.setattr(container, "build_code", lambda **kw: [sys.executable, *kw["command"][1:]])


def test_sandbox_executions_by_runtime_language_and_status(local, metered):
    assert cr.run_code("def main(state):\n    return 1\n", {}).value == 1
    with pytest.raises(AppError) as e: cr.run_code("def main(state):\n    raise ValueError('x')\n", {})
    assert e.value.code == "CODE_FAILED"
    with pytest.raises(AppError): cr.run_code("def nope(:\n", {})  # invalid before any execution: not counted
    pts = points(metered); bounded(pts)
    runs = {(a["runtime"], a["language"], a["status"]): v for v, a in pts["studio.sandbox.executions"]}
    assert runs == {("subprocess", "python", "ok"): 1, ("subprocess", "python", "CODE_FAILED"): 1}
    assert sum(c for c, _ in pts["studio.sandbox.duration"]) == 2


# ---- browser ----

def test_browser_sessions_and_actions(monkeypatch, metered):
    svc = BrowserSessionService.__new__(BrowserSessionService)
    row = types.SimpleNamespace(id="b1", status="ready", cleanup_pending=False, worker_id="w1")
    svc.repo = types.SimpleNamespace(transition=lambda *a, **k: True, get=lambda sid: row)
    svc.approvals = None; svc._cleanup = lambda r: True
    svc.close(row, "lost"); svc.close(row); svc.close(row, "weird")
    scope = BrowserRunScope.__new__(BrowserRunScope)
    scope._call = lambda *a: {"status": "confirmed"}
    assert scope.call("g", "t", "click", {})["status"] == "confirmed"
    def fail(*a): raise AppError("BROWSER_RUNTIME_UNAVAILABLE")
    scope._call = fail
    with pytest.raises(AppError): scope.call("g", "t", "click", {})
    pts = points(metered); bounded(pts)
    assert {a["status"]: v for v, a in pts["studio.browser.sessions"]} == {"lost": 1, "closed": 2}
    assert {(a["status"], a["code"]): v for v, a in pts["studio.browser.actions"]} == {("confirmed", ""): 1, ("error", "BROWSER_RUNTIME_UNAVAILABLE"): 1}


# ---- channels ----

def test_channel_messages_in_and_out(monkeypatch, metered):
    svc = ChatRunService.__new__(ChatRunService)
    monkeypatch.setattr(svc, "_receive", lambda rows, m: {"outcome": "queued"}, raising=False)
    conn = types.SimpleNamespace(kind="telegram", id="c1", name=SECRET)
    assert svc.receive([(conn, {})], types.SimpleNamespace(text="/run x")) == {"outcome": "queued"}
    ok = types.SimpleNamespace(reply=lambda *a: None)
    def refused(*a): raise AppError("CHANNEL_API_FAILED", kind="Slack", reason="no")
    bad = types.SimpleNamespace(reply=refused)
    msg = types.SimpleNamespace(kind="slack", ref="{}")
    svc._say(ok, {}, msg, "hi"); svc._say(bad, {}, msg, "hi")
    pts = points(metered); bounded(pts)
    got = {(a["kind"], a["direction"], a["status"]): v for v, a in pts["studio.channel.messages"]}
    assert got == {("telegram", "in", "queued"): 1, ("slack", "out", "ok"): 1, ("slack", "out", "CHANNEL_API_FAILED"): 1}


# ---- product limits ----

@pytest.mark.parametrize("key", [f"{prefix}:user-1:10.1.2.3" for prefix in SCOPES])
def test_each_limiter_scope_counts_only_refusals(key, events):
    lim = InMemoryRateLimiter()
    assert asyncio.run(lim.hit(key, 1, 60))[0] and events == []
    ok, retry = asyncio.run(lim.hit(key, 1, 60))
    assert not ok and retry >= 1
    assert events == [("rate_limit", {"scope": SCOPES[key.split(":")[0]]})]


def test_limiter_keys_never_reach_metric_attributes(metered):
    lim = InMemoryRateLimiter()
    for _ in range(3): asyncio.run(lim.hit("pubchat-ip:10.1.2.3", 1, 60))
    asyncio.run(lim.hit("unknown-prefix:user-1", 0, 60))
    pts = points(metered); bounded(pts)
    assert {a["scope"]: v for v, a in pts["studio.rate_limit.hits"]} == {"public_chat": 2, "other": 1}


def test_email_quota_counts_the_refusal(monkeypatch, events):
    monkeypatch.setenv("STUDIO_EMAIL_NODE_HOURLY_LIMIT", "2")
    c = InMemoryCounter()
    email_quota.take_email_quota(c, "user-1", 2); assert events == []
    with pytest.raises(AppError) as e: email_quota.take_email_quota(c, "user-1", 1)
    assert e.value.code == "EMAIL_RATE_LIMITED" and events == [("rate_limit", {"scope": "email_node"})]


def test_login_lock_counts_with_the_same_response(events):
    from app.main import app
    c = TestClient(app); email = f"lock{uuid.uuid4().hex[:6]}@example.com"
    c.post("/api/auth/register", json={"email": email, "password": "goodpass1"})
    codes = [c.post("/api/auth/login", json={"email": email, "password": "wrongpass"}) for _ in range(6)]
    assert codes[-1].status_code == 429 and codes[-1].json()["error"]["code"] == "AUTH_LOCKED"
    assert ("rate_limit", {"scope": "login"}) in events
    assert all(f == {"scope": "login"} for e, f in events if e == "rate_limit")
