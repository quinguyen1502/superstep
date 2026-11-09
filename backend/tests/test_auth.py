import os, tempfile
os.environ.setdefault("STUDIO_DB", tempfile.mktemp(suffix=".db"))
import uuid, pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.core.security import hash_password, verify_password

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def login(e="admin@example.com", p="admin123"): return c.post("/api/auth/login", json={"email": e, "password": p})

def test_hash():
    h = hash_password("x123456"); assert h.startswith("pbkdf2_sha256$") and verify_password("x123456", h) and not verify_password("no", h)

def test_login_demo_and_me():
    r = login(); assert r.status_code == 200
    assert c.get("/api/me", headers=H(r.json()["data"]["token"])).json()["data"]["email"] == "admin@example.com"

def test_bad_login():
    assert login(p="wrong").status_code == 401

def test_protected():
    assert c.get("/api/workflows").status_code == 401
    assert c.get("/api/workflows", headers=H("garbage")).status_code == 401

def test_ws_requires_token():
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/ws/run") as ws: ws.receive_json()

def test_register_ownership_crud():
    email = f"u{uuid.uuid4().hex[:6]}@example.com"
    r = c.post("/api/auth/register", json={"email": email, "password": "secret12"}); assert r.status_code == 200
    t = r.json()["data"]["token"]
    assert c.post("/api/auth/register", json={"email": email, "password": "secret12"}).status_code == 409
    wfs = c.get("/api/workflows", headers=H(t)).json()["data"]; assert len(wfs) == 1 and wfs[0]["node_count"] == 7
    assert c.get("/api/workflows/example", headers=H(t)).status_code == 404  # admin's workflow
    wid = wfs[0]["id"]
    d = c.post(f"/api/workflows/{wid}/duplicate", headers=H(t)).json()["data"]["id"]
    assert c.patch(f"/api/workflows/{d}", json={"name": "Renamed"}, headers=H(t)).status_code == 200
    assert any(w["name"] == "Renamed" for w in c.get("/api/workflows", headers=H(t)).json()["data"])
    assert c.delete(f"/api/workflows/{d}", headers=H(t)).status_code == 200
    assert len(c.get("/api/workflows", headers=H(t)).json()["data"]) == 1
    other = c.post("/api/auth/register", json={"email": f"o{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
    assert c.delete(f"/api/workflows/{wid}", headers=H(other)).status_code == 404  # another user's workflow (admins act as owner,)
