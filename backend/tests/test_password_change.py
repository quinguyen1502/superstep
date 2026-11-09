"""the profile (GET /api/me) and a self-service password change (POST /api/me/password)."""
import time, uuid
from fastapi.testclient import TestClient
from app.core import security
from app.main import app

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def email(): return f"p{uuid.uuid4().hex[:8]}@example.com"
def reg(e, p="goodpass1"): return c.post("/api/auth/register", json={"email": e, "password": p}).json()["data"]
def login(e, p): return c.post("/api/auth/login", json={"email": e, "password": p})
def change(tok, cur, new): return c.post("/api/me/password", json={"current_password": cur, "new_password": new}, headers=H(tok))
def code(r): return r.json()["error"]["code"]


def test_profile_shows_the_account():
    e = email(); s = reg(e)
    me = c.get("/api/me", headers=H(s["token"])).json()["data"]
    assert me["email"] == e and me["role"] == "editor" and abs(me["created"] - time.time()) < 60 and "password" not in me


def test_change_signs_out_other_sessions_and_keeps_this_one():
    e = email(); old = reg(e)["token"]; other = login(e, "goodpass1").json()["data"]["token"]
    time.sleep(1.05)  # tokens carry whole seconds
    r = change(old, "goodpass1", "newpass22")
    assert r.status_code == 200 and r.json()["data"]["user"]["email"] == e
    assert security.SESSION_COOKIE in r.headers["set-cookie"]
    new = r.json()["data"]["token"]
    assert c.get("/api/me", headers=H(new)).status_code == 200
    for t in (old, other): assert code(c.get("/api/me", headers=H(t))) == "AUTH_TOKEN_EXPIRED"
    assert code(login(e, "goodpass1")) == "AUTH_INVALID_CREDENTIALS" and login(e, "newpass22").status_code == 200


def test_wrong_weak_and_same_passwords_are_refused():
    e = email(); t = reg(e)["token"]
    r = change(t, "wrongpass1", "newpass22"); assert r.status_code == 400 and code(r) == "AUTH_PASSWORD_WRONG"
    assert code(change(t, "goodpass1", "short1")) == "AUTH_PASSWORD_TOO_SHORT"
    assert code(change(t, "goodpass1", "lettersonly")) == "AUTH_PASSWORD_WEAK"
    assert code(change(t, "goodpass1", "goodpass1")) == "AUTH_PASSWORD_SAME"
    assert c.get("/api/me", headers=H(t)).status_code == 200 and login(e, "goodpass1").status_code == 200  # nothing changed


def test_wrong_current_passwords_count_toward_the_sign_in_lockout(monkeypatch):
    monkeypatch.setenv("STUDIO_LOGIN_MAX_FAILURES", "3")
    e = email(); t = reg(e)["token"]
    assert [code(change(t, "wrongpass1", "newpass22")) for _ in range(2)] == ["AUTH_PASSWORD_WRONG"] * 2
    r = change(t, "wrongpass1", "newpass22"); assert r.status_code == 429 and code(r) == "AUTH_LOCKED"
    assert code(change(t, "goodpass1", "newpass22")) == "AUTH_LOCKED"  # even the right one, until the lock ends
    assert code(login(e, "goodpass1")) == "AUTH_LOCKED"
    assert c.get("/api/me", headers=H(t)).status_code == 200  # this session stays signed in


def test_the_change_is_in_the_audit_log_and_needs_a_session():
    e = email(); t = reg(e)["token"]
    assert change(t, "goodpass1", "newpass22").status_code == 200
    admin = login("admin@example.com", "admin123").json()["data"]["token"]
    items = c.get("/api/admin/audit", params={"q": e}, headers=H(admin)).json()["data"]["items"]
    assert any(x["action"] == "user.password_changed" and x["actor"] == e for x in items)
    assert c.post("/api/me/password", json={"current_password": "x", "new_password": "y"}).status_code == 401
