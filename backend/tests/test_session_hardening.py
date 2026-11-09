"""sign-in lockout, the HttpOnly session cookie (CSRF), password reset links, and no demo user in production."""
import time, uuid
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.core import config, security
from app.main import app
from app.models.database import Database
from app.repositories import UserRepository
from app.services import auth_service as auth_mod
from app.services.seed import bootstrap

c = TestClient(app)  # http: the Secure cookie is never sent (conftest), so this client tests Bearer auth
def H(t): return {"Authorization": f"Bearer {t}"}
def email(): return f"s{uuid.uuid4().hex[:8]}@example.com"
def reg(e, p="goodpass1", client=c): return client.post("/api/auth/register", json={"email": e, "password": p})
def login(e, p, client=c): return client.post("/api/auth/login", json={"email": e, "password": p})
def admin(): return login("admin@example.com", "admin123").json()["data"]["token"]
def code(r): return r.json()["error"]["code"]


def test_lockout_after_failures_even_with_the_right_password(monkeypatch):
    monkeypatch.setenv("STUDIO_LOGIN_MAX_FAILURES", "3"); monkeypatch.setenv("STUDIO_LOGIN_LOCK", "2")
    e = email(); reg(e)
    assert [code(login(e, "wrong1234")) for _ in range(2)] == ["AUTH_INVALID_CREDENTIALS"] * 2
    r = login(e, "wrong1234"); assert r.status_code == 429 and code(r) == "AUTH_LOCKED" and r.json()["error"]["details"]["minutes"] == 1
    assert code(login(e, "goodpass1")) == "AUTH_LOCKED"
    time.sleep(2.1)
    assert login(e, "goodpass1").status_code == 200


def test_unknown_emails_lock_the_same_way(monkeypatch):
    monkeypatch.setenv("STUDIO_LOGIN_MAX_FAILURES", "2")
    ghost = email()
    assert [code(login(ghost, "whatever1")) for _ in range(2)] == ["AUTH_INVALID_CREDENTIALS", "AUTH_LOCKED"]


def test_success_resets_the_failure_count(monkeypatch):
    monkeypatch.setenv("STUDIO_LOGIN_MAX_FAILURES", "2")
    e = email(); reg(e)
    assert code(login(e, "wrong1234")) == "AUTH_INVALID_CREDENTIALS"
    assert login(e, "goodpass1").status_code == 200
    assert code(login(e, "wrong1234")) == "AUTH_INVALID_CREDENTIALS"  # counting started again


def test_session_cookie_is_httponly_and_writes_need_the_csrf_header():
    b = TestClient(app, base_url="https://testserver"); e = email()
    r = reg(e, client=b); assert r.status_code == 200 and r.json()["data"]["expires_at"] > time.time()
    cookie = r.headers["set-cookie"].lower()
    assert security.SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=lax" in cookie and "secure" in cookie
    assert b.get("/api/me").json()["data"]["email"] == e  # cookie alone
    wf = {"name": f"c{uuid.uuid4().hex[:6]}", "state": [], "nodes": [], "edges": []}
    r = b.post("/api/workflows", json=wf); assert r.status_code == 403 and code(r) == "AUTH_CSRF"
    assert b.post("/api/workflows", json=wf, headers={"X-Requested-With": "studio"}).status_code == 200
    assert b.post("/api/auth/logout").status_code == 200
    assert b.get("/api/me").status_code == 401


def test_websocket_takes_the_cookie_only_from_the_same_origin():
    b = TestClient(app, base_url="https://testserver"); reg(email(), client=b)
    jar = {"cookie": f"{security.SESSION_COOKIE}={b.cookies[security.SESSION_COOKIE]}"}  # the test client leaves Secure cookies off sockets
    for origin in ("https://testserver", "https://testserver:8443"):  # nginx forwards $host without the port
        with b.websocket_connect("/ws/notifications", headers={**jar, "origin": origin}) as ws:
            assert ws.receive_json()["type"] == "ready"
    with pytest.raises(WebSocketDisconnect) as e:
        with b.websocket_connect("/ws/notifications", headers={**jar, "origin": "https://evil.example"}) as ws: ws.receive_json()
    assert e.value.code == 4401


def test_admin_reset_link_sets_a_new_password_and_ends_old_sessions():
    e = email(); user = reg(e).json()["data"]; old = user["token"]
    assert code(c.post(f"/api/admin/users/{user['user']['id']}/password-reset", headers=H(old))) == "PERMISSION_DENIED"
    r = c.post(f"/api/admin/users/{user['user']['id']}/password-reset", headers=H(admin())).json()["data"]
    token = r["path"].split("token=")[1]; assert r["path"].startswith("/reset-password?token=") and r["url"] is None and r["expires_in"] == 3600
    assert code(c.post("/api/auth/password-reset/confirm", json={"token": token, "password": "short"})) == "AUTH_PASSWORD_TOO_SHORT"
    time.sleep(1.05)  # tokens carry whole seconds
    assert c.post("/api/auth/password-reset/confirm", json={"token": token, "password": "newpass12"}).json()["data"] == {"email": e}
    r = c.get("/api/me", headers=H(old)); assert r.status_code == 401 and code(r) == "AUTH_TOKEN_EXPIRED"
    assert code(c.post("/api/auth/password-reset/confirm", json={"token": token, "password": "other123"})) == "PASSWORD_RESET_INVALID"  # one use
    assert code(login(e, "goodpass1")) == "AUTH_INVALID_CREDENTIALS" and login(e, "newpass12").status_code == 200
    audit = c.get("/api/admin/audit", headers=H(admin())).json()["data"]
    assert {"user.password_reset_link", "user.password_reset"} <= {x["action"] for x in audit["items"]}


def test_reset_clears_a_lockout(monkeypatch):
    monkeypatch.setenv("STUDIO_LOGIN_MAX_FAILURES", "1")
    e = email(); uid = reg(e).json()["data"]["user"]["id"]
    assert code(login(e, "wrong1234")) == "AUTH_LOCKED"
    token = c.post(f"/api/admin/users/{uid}/password-reset", headers=H(admin())).json()["data"]["path"].split("token=")[1]
    c.post("/api/auth/password-reset/confirm", json={"token": token, "password": "newpass12"})
    assert login(e, "newpass12").status_code == 200


def test_expired_or_unknown_links_are_refused(monkeypatch):
    assert code(c.post("/api/auth/password-reset/confirm", json={"token": "nope", "password": "newpass12"})) == "PASSWORD_RESET_INVALID"
    uid = reg(email()).json()["data"]["user"]["id"]
    token = c.post(f"/api/admin/users/{uid}/password-reset", headers=H(admin())).json()["data"]["path"].split("token=")[1]
    monkeypatch.setattr(auth_mod.time, "time", lambda: 10 ** 11)
    assert code(c.post("/api/auth/password-reset/confirm", json={"token": token, "password": "newpass12"})) == "PASSWORD_RESET_INVALID"


def test_forgot_password_answers_the_same_and_mails_only_with_smtp(monkeypatch):
    assert c.get("/api/auth/options").json()["data"] == {"demo": True, "reset": "admin"}
    assert c.post("/api/auth/password-reset", json={"email": email()}).json()["data"] == {"reset": "admin"}
    sent = []
    monkeypatch.setenv("SMTP_HOST", "smtp.test"); monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.test")
    monkeypatch.setattr(auth_mod.mailer, "send", lambda smtp, to, subject, text, html=None: sent.append((to, text)) or True)
    e = email(); reg(e)
    for who in (e, email()):  # a real account and an unknown one get the same answer
        assert c.post("/api/auth/password-reset", json={"email": who}).json()["data"] == {"reset": "email"}
    for _ in range(50):
        if sent: break
        time.sleep(0.05)
    assert [to for to, _ in sent] == [e] and "https://studio.test/reset-password?token=" in sent[0][1]


def test_production_has_no_demo_user(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IS_PROD", True)
    db = Database(f"sqlite:///{tmp_path / 'prod.db'}"); bootstrap(db)
    assert UserRepository(db).get_by_email(config.DEMO_EMAIL) is None


def test_production_deactivates_a_demo_user_that_kept_its_password(tmp_path, monkeypatch):
    db = Database(f"sqlite:///{tmp_path / 'old.db'}"); bootstrap(db)  # dev start: the demo user exists
    monkeypatch.setattr(config, "IS_PROD", True); monkeypatch.setenv("STUDIO_ADMIN_EMAILS", "")
    bootstrap(db)
    assert UserRepository(db).get_by_email(config.DEMO_EMAIL).active is False
