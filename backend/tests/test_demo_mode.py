"""Public demo mode (STUDIO_DEMO_MODE): the read-only visitor, the seeded samples, and the engine's demo limits."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.demo import install_demo_guard
from app.api.error_handlers import register_error_handlers
from app.core import config, security
from app.core.errors import AppError
from app.engine import code_runtime, nodes
from app.models.database import Database
from app.repositories import UserRepository, WorkflowRepository, WorkflowShareRepository
from app.services import demo_service, seed
from app.services.auth_service import AuthService


@pytest.fixture
def demo(monkeypatch): monkeypatch.setenv("STUDIO_DEMO_MODE", "true")


def test_flag_parsing(monkeypatch):
    for v, on in (("true", True), ("1", True), ("TRUE", True), ("", False), ("no", False)):
        monkeypatch.setenv("STUDIO_DEMO_MODE", v); assert config.demo_mode() is on


def test_policy_lets_the_visitor_read_and_run_but_not_write():
    v = demo_service.VISITOR_ID
    assert not demo_service.refuses("GET", "/api/credentials", v)
    for path in ("/api/auth/login", "/api/auth/logout", "/api/runs/r1/cancel", "/api/notifications/read-all", "/api/approvals/inbox/r1"):
        assert not demo_service.refuses("POST", path, v), path
    assert not demo_service.refuses("POST", "/api/workflows/demo-chatbot/chat/sessions", v)  # the Chat panel
    assert not demo_service.refuses("DELETE", "/api/chat/sessions/s1", v)
    assert demo_service.refuses("PUT", "/api/workflows/demo-chatbot/chat", v)  # but not the Chat settings
    for m, path in (("PUT", "/api/workflows/example"), ("POST", "/api/credentials"), ("POST", "/api/me/password"),
                    ("PUT", "/api/notifications/preferences"), ("PUT", "/api/workflows/example/shares"), ("POST", "/api/workflows")):
        assert demo_service.refuses(m, path, v), path
        assert not demo_service.refuses(m, path, "admin-id")  # the admin is a normal account
    assert demo_service.refuses("POST", "/api/auth/register", None) and demo_service.refuses("POST", "/api/auth/password-reset", None)


def test_guard_answers_with_the_envelope():
    app = FastAPI(); register_error_handlers(app); install_demo_guard(app)
    @app.put("/api/workflows/x")
    def save(): return {"ok": True}
    c = TestClient(app)
    tok = security.make_token(demo_service.VISITOR_ID, demo_service.VISITOR_EMAIL)
    r = c.put("/api/workflows/x", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "DEMO_READ_ONLY"
    assert c.put("/api/workflows/x", headers={"Authorization": f"Bearer {security.make_token('someone', 'a@b.c')}"}).status_code == 200


def test_seed_is_idempotent_and_shares_samples_read_only(tmp_path, demo):
    d = Database(f"sqlite:///{tmp_path}/demo.db")
    seed.bootstrap(d); seed.bootstrap(d)  # every boot
    users, wfs, shares = UserRepository(d), WorkflowRepository(d), WorkflowShareRepository(d)
    v = users.get_by_email(demo_service.VISITOR_EMAIL)
    assert v.role == "viewer" and v.active and security.verify_password(demo_service.VISITOR_PASSWORD, v.password)
    for wid in ("example", "demo-chatbot", "demo-router", "demo-approval"):
        assert wfs.exists(wid) and wfs.get(wid).owner != v.id and shares.role_of(wid, v.id) == "viewer", wid
    from app.repositories import ChatTriggerRepository
    web = ChatTriggerRepository(d).web("demo-chatbot")
    assert web is not None and web.enabled  # the Chat panel works for the visitor
    opts = AuthService(users).options()["demo_mode"]
    assert opts == {"email": demo_service.VISITOR_EMAIL, "password": demo_service.VISITOR_PASSWORD}


def test_visitor_is_read_only_and_sees_only_owner_and_self_in_shares(tmp_path, monkeypatch):
    from app.repositories import TeamRepository
    from app.services.access import AccessService
    from app.services.auth_service import public_user
    from app.services.share_service import ShareService
    monkeypatch.setenv("STUDIO_DEMO_MODE", "true")
    d = Database(f"sqlite:///{tmp_path}/demo.db"); seed.bootstrap(d)
    users, wfs, shares = UserRepository(d), WorkflowRepository(d), WorkflowShareRepository(d)
    a, b = demo_service.start_visit(d), demo_service.start_visit(d)
    svc = ShareService(shares, users, AccessService(users, wfs, shares, TeamRepository(d)), TeamRepository(d))
    listed = svc.list("demo-approval", a)
    assert [s["user_id"] for s in listed["shares"]] == [a] and listed["owner"]["email"]  # not b, not the template account
    owner = wfs.get("demo-approval").owner
    assert {s["user_id"] for s in svc.list("demo-approval", owner)["shares"]} >= {a, b, demo_service.VISITOR_ID}  # the admin sees all
    assert public_user(users.get_by_id(a))["read_only"] is True and public_user(users.get_by_id(owner))["read_only"] is False
    monkeypatch.setenv("STUDIO_DEMO_MODE", "")  # outside demo mode nobody is read-only and every collaborator is listed
    assert public_user(users.get_by_id(a))["read_only"] is False and len(svc.list("demo-approval", a)["shares"]) >= 3


def test_code_nodes_are_refused_with_an_error_code(demo, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    assert config.code_runtime() == "off" and code_runtime.unavailable() == "demo"
    assert code_runtime.runtime_error().code == "DEMO_CODE_DISABLED"


def test_http_and_email_nodes_are_refused_and_llm_runs_offline(demo, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    http = nodes.node_fn({"id": "h", "type": "tool", "data": {"mode": "http", "url": "https://example.com", "output_field": "r"}})
    with pytest.raises(AppError) as e: http({})
    assert e.value.code == "DEMO_NODE_DISABLED"
    mail = nodes.node_fn({"id": "m", "type": "email", "data": {"to": "a@b.c", "subject": "s", "body": "b"}})
    with pytest.raises(AppError) as e: mail({})
    assert e.value.code == "DEMO_NODE_DISABLED"
    llm = nodes.node_fn({"id": "l", "type": "llm", "data": {"prompt": "hi", "output_field": "a", "credential_id": "c1"}})
    assert isinstance(llm({})["a"], str)  # the mock answers; no provider, no credential lookup


def test_a_run_with_a_code_node_is_refused_with_the_demo_code(demo):
    from app.api.deps import get_db, run_service
    seed.bootstrap(get_db())  # the visitor and the samples in the shared test database
    wf = {"state": [{"name": "x", "type": "string"}], "nodes": [{"id": "s", "type": "start", "data": {}},
          {"id": "c", "type": "tool", "data": {"mode": "code", "code": "def main(state):\n    return 1", "output_field": "x"}}], "edges": []}
    with pytest.raises(AppError) as e: run_service().plan(demo_service.VISITOR_ID, {"workflow_id": "example", "workflow": wf, "input": {}})
    assert e.value.code == "DEMO_CODE_DISABLED"


def test_demo_run_rate_limit_per_ip(demo, monkeypatch):
    import asyncio
    from app.services.rate_limit import InMemoryRateLimiter
    monkeypatch.setenv("STUDIO_DEMO_RUN_RATE_LIMIT", "2")
    svc = demo_service.DemoService(InMemoryRateLimiter())
    async def go():
        await svc.check_run("1.2.3.4"); await svc.check_run("1.2.3.4")
        with pytest.raises(AppError) as e: await svc.check_run("1.2.3.4")
        assert e.value.code == "RATE_LIMITED" and int(e.value.headers["Retry-After"]) >= 1
        await svc.check_run("5.6.7.8")  # per client IP
        monkeypatch.setenv("STUDIO_DEMO_RUN_RATE_LIMIT", "0")
        for _ in range(5): await svc.check_run("1.2.3.4")  # 0 turns it off
    asyncio.run(go())


def test_demo_node_errors_have_no_class_prefix():
    from app.engine.limits import safe_error
    msg = safe_error(AppError("DEMO_NODE_DISABLED", node="HTTP Tool"))
    assert not msg.startswith("AppError") and "HTTP Tool" in msg
    assert safe_error(ValueError("boom")) == "ValueError: boom"
