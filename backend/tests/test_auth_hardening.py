import time, uuid, jwt, pytest
from fastapi.testclient import TestClient
from app.core import security as auth
from app.main import app
from app.services.naming import unique_name

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def email(): return f"h{uuid.uuid4().hex[:8]}@Example.com"
def reg(e, p="goodpass1"): return c.post("/api/auth/register", json={"email": e, "password": p})
def user():
    r = reg(email()); assert r.status_code == 200; return r.json()["data"]["token"]

@pytest.mark.parametrize("pw,code", [("short1", "AUTH_PASSWORD_TOO_SHORT"), ("allletters", "AUTH_PASSWORD_WEAK"), ("12345678", "AUTH_PASSWORD_WEAK"), ("a1" * 70, "AUTH_PASSWORD_TOO_LONG")])
def test_weak_passwords_rejected(pw, code):
    r = reg(email(), pw); assert r.status_code == 400 and r.json()["error"]["code"] == code

def test_email_normalised_and_bad_email():
    e = email(); r = reg("  " + e + " ")
    assert r.status_code == 200 and r.json()["data"]["user"]["email"] == e.lower()
    assert c.post("/api/auth/login", json={"email": e.upper(), "password": "goodpass1"}).status_code == 200
    assert reg("not-an-email").status_code == 400

def test_demo_user_exempt_from_rules():
    assert c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).status_code == 200

def test_login_error_is_generic():
    e = email(); reg(e)
    a = c.post("/api/auth/login", json={"email": e, "password": "wrongpass1"})
    b = c.post("/api/auth/login", json={"email": "nobody-" + e, "password": "wrongpass1"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json() and a.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

def test_expired_token_is_flagged():
    tok = auth.make_token("x", "x@example.com", ttl=-10)
    r = c.get("/api/workflows", headers=H(tok))
    assert r.status_code == 401 and r.headers.get("X-Auth-Error") == "expired"
    forged = jwt.encode({"sub": "x", "email": "x", "exp": int(time.time()) + 60}, "other", algorithm="HS256")
    r = c.get("/api/workflows", headers=H(forged)); assert r.status_code == 401 and "X-Auth-Error" not in r.headers

def test_secret_check(monkeypatch, caplog):
    monkeypatch.setattr(auth, "SECRET", auth.PLACEHOLDER_SECRET); monkeypatch.setattr(auth, "IS_PROD", False)
    assert auth.check_secret() is False and "JWT_SECRET" in caplog.text
    monkeypatch.setattr(auth, "IS_PROD", True)
    with pytest.raises(RuntimeError): auth.check_secret()
    monkeypatch.setattr(auth, "SECRET", "real-secret"); assert auth.check_secret() is True

def test_rename_rules_and_duplicate_naming():
    t = user(); wid = c.get("/api/workflows", headers=H(t)).json()["data"][0]["id"]
    assert c.patch(f"/api/workflows/{wid}", json={"name": "   "}, headers=H(t)).status_code == 400
    assert c.patch(f"/api/workflows/{wid}", json={"name": "x" * 121}, headers=H(t)).status_code == 400
    assert c.patch(f"/api/workflows/{wid}", json={"name": "  Base   flow "}, headers=H(t)).json()["data"]["name"] == "Base flow"
    names = [c.post(f"/api/workflows/{wid}/duplicate", headers=H(t)).json()["data"]["name"] for _ in range(3)]
    assert names == ["Base flow (copy)", "Base flow (copy 2)", "Base flow (copy 3)"]
    c.patch(f"/api/workflows/{wid}", json={"name": "L" * 120}, headers=H(t))
    long_copy = c.post(f"/api/workflows/{wid}/duplicate", headers=H(t)).json()["data"]["name"]
    assert len(long_copy) == 120 and long_copy.endswith(" (copy)")
    c.patch(f"/api/workflows/{wid}", json={"name": "Base flow"}, headers=H(t))
    assert c.patch(f"/api/workflows/{wid}", json={"name": "Base flow (copy)"}, headers=H(t)).status_code == 409
    a = c.post("/api/workflows", json={"name": "Untitled workflow", "nodes": [], "edges": []}, headers=H(t)).json()["data"]["id"]
    b = c.post("/api/workflows", json={"name": "Untitled workflow", "nodes": [], "edges": []}, headers=H(t)).json()["data"]["id"]
    by = {w["id"]: w["name"] for w in c.get("/api/workflows", headers=H(t)).json()["data"]}
    assert by[a] == "Untitled workflow" and by[b] == "Untitled workflow (copy)"

def test_delete_last_and_foreign_or_deleted_404():
    t = user(); other = user()
    for w in c.get("/api/workflows", headers=H(t)).json()["data"]: assert c.delete(f"/api/workflows/{w['id']}", headers=H(t)).status_code == 200
    assert c.get("/api/workflows", headers=H(t)).json()["data"] == []
    wid = c.get("/api/workflows", headers=H(other)).json()["data"][0]["id"]
    assert c.get(f"/api/workflows/{wid}", headers=H(t)).status_code == 404
    c.delete(f"/api/workflows/{wid}", headers=H(other))
    assert c.get(f"/api/workflows/{wid}", headers=H(other)).status_code == 404

def test_many_workflows_list_fast():
    t = user()
    for i in range(120): c.post("/api/workflows", json={"name": f"Flow {i:03d}", "nodes": [], "edges": []}, headers=H(t))
    t0 = time.time(); r = c.get("/api/workflows", headers=H(t)); dt = time.time() - t0
    # Correctness first; bound stays tight enough to catch N+1 but tolerant of
    # loaded Postgres+Redis CI runners (observed ~1.7s flakes under 1.5s).
    assert len(r.json()["data"]) == 121 and dt < 3.0, dt

def test_unique_name_helper():
    names = {"A", "A (copy)"}
    assert unique_name(names, "B") == "B" and unique_name(names, "A") == "A (copy 2)"
