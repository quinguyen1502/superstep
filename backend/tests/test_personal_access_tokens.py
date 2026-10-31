"""Personal access tokens and the CLI device sign-in (TASK-0167)."""
import os, tempfile
os.environ.setdefault("STUDIO_DB", tempfile.mktemp(suffix=".db"))
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db
from app.repositories import CliDeviceRepository
from app.services.pat_service import digest

c = TestClient(app)


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def register():
    email = f"pat{uuid.uuid4().hex[:8]}@example.com"
    response = c.post("/api/auth/register", json={"email": email, "password": "secret12"})
    assert response.status_code == 200, response.text
    return email, response.json()["data"]["token"]


def test_a_token_is_shown_once_and_then_acts_as_the_user():
    email, jwt = register()
    created = c.post("/api/me/tokens", json={"name": "laptop"}, headers=headers(jwt))
    assert created.status_code == 200, created.text
    secret = created.json()["data"]["token"]
    assert secret.startswith("pat_") and created.json()["data"]["prefix"] == secret[:10]
    listed = c.get("/api/me/tokens", headers=headers(jwt)).json()["data"]["items"]
    assert listed[0]["name"] == "laptop" and "token" not in listed[0] and secret not in str(listed)
    assert c.get("/api/me", headers=headers(secret)).json()["data"]["email"] == email
    assert c.get("/api/me", headers=headers(jwt)).json()["data"]["email"] == email
    with c.websocket_connect(f"/ws/run?token={secret}") as ws:
        ws.send_json({"workflow_id": "missing"})
        event = ws.receive_json()
    assert event["type"] == "error" and event["error"]["code"] == "WORKFLOW_NOT_FOUND"
    assert c.delete(f"/api/me/tokens/{listed[0]['id']}", headers=headers(jwt)).json()["data"] == {"ok": True}
    gone = c.get("/api/me", headers=headers(secret))
    assert gone.status_code == 401 and gone.json()["error"]["code"] == "AUTH_TOKEN_INVALID"
    again = c.post("/api/me/tokens", json={"name": "laptop"}, headers=headers(jwt))
    assert again.status_code == 200
    other, _other_jwt = register()
    assert other
    assert c.post("/api/me/tokens", json={"name": "laptop"}, headers=headers(_other_jwt)).status_code == 200


def test_an_active_name_cannot_be_reused_and_unknown_tokens_are_rejected():
    _email, jwt = register()
    assert c.post("/api/me/tokens", json={"name": "ci"}, headers=headers(jwt)).status_code == 200
    taken = c.post("/api/me/tokens", json={"name": "ci"}, headers=headers(jwt))
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "PAT_NAME_TAKEN"
    missing = c.delete("/api/me/tokens/not-a-token", headers=headers(jwt))
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "PAT_NOT_FOUND"
    unknown = c.get("/api/me", headers=headers("pat_not-issued"))
    assert unknown.status_code == 401 and unknown.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


def test_device_sign_in_returns_the_secret_once():
    email, jwt = register()
    started = c.post("/api/auth/cli/devices", json={"name": "desk"}).json()["data"]
    assert started["user_code"] and started["device_code"] and started["verification_uri"].endswith("/cli/authorize") and started["user_code"] not in started["verification_uri"]
    pending = c.get(f"/api/auth/cli/devices/{started['device_code']}")
    assert pending.status_code == 200 and pending.json()["data"]["status"] == "pending"
    refused = c.post("/api/auth/cli/devices/approve", json={"user_code": "no-such-code"}, headers=headers(jwt))
    assert refused.status_code == 400 and refused.json()["error"]["code"] == "CLI_DEVICE_INVALID"
    approved = c.post("/api/auth/cli/devices/approve", json={"user_code": started["user_code"], "name": "desk"}, headers=headers(jwt))
    assert approved.status_code == 200
    first = c.get(f"/api/auth/cli/devices/{started['device_code']}")
    assert first.status_code == 200 and first.json()["data"]["token"].startswith("pat_")
    assert c.get("/api/me", headers=headers(first.json()["data"]["token"])).json()["data"]["email"] == email
    second = c.get(f"/api/auth/cli/devices/{started['device_code']}")
    assert second.status_code == 400 and second.json()["error"]["code"] == "CLI_DEVICE_INVALID"


def test_a_denied_or_expired_device_does_not_return_a_token():
    _email, jwt = register()
    denied = c.post("/api/auth/cli/devices", json={}).json()["data"]
    assert c.post("/api/auth/cli/devices/deny", json={"user_code": denied["user_code"]}, headers=headers(jwt)).status_code == 200
    refused = c.get(f"/api/auth/cli/devices/{denied['device_code']}")
    assert refused.status_code == 400 and refused.json()["error"]["code"] == "CLI_DEVICE_DENIED"
    expired = c.post("/api/auth/cli/devices", json={}).json()["data"]
    row = CliDeviceRepository(get_db()).by_device_hash(digest(expired["device_code"]))
    CliDeviceRepository(get_db()).set_fields(row.id, expires=0)
    late = c.get(f"/api/auth/cli/devices/{expired['device_code']}")
    assert late.status_code == 400 and late.json()["error"]["code"] == "CLI_DEVICE_EXPIRED"
    still = c.post("/api/auth/cli/devices/approve", json={"user_code": expired["user_code"]}, headers=headers(jwt))
    assert still.status_code == 400 and still.json()["error"]["code"] == "CLI_DEVICE_EXPIRED"


def test_the_sign_in_link_does_not_carry_the_code_starts_are_limited_and_old_ones_are_removed(tmp_path):
    """Review finding 6 (TASK-0205, DEC-0076): the link held the code, so whoever sent it could have it approved; the
    unauthenticated start had no limit and the table was never cleaned."""
    import asyncio, time
    import pytest
    from app.core.errors import AppError
    from app.models import CliDevice
    from app.models.database import Database
    from app.repositories import PersonalAccessTokenRepository, UserRepository
    from app.services.pat_service import DEVICE_STARTS, DEVICE_TTL, PatService
    from app.services.rate_limit import make_rate_limiter
    db = Database(f"sqlite:///{tmp_path}/d.db"); db.migrate(); devices = CliDeviceRepository(db)
    svc = PatService(PersonalAccessTokenRepository(db), devices, UserRepository(db), limiter=make_rate_limiter(None))
    old = time.time() - 2 * DEVICE_TTL
    devices.add(CliDevice(id="old", device_hash="h", user_code_hash="u", name=None, user_id=None, token_id=None, status="pending",
                          secret=None, expires=old, created=old))
    first = asyncio.run(svc.start_device_from("203.0.113.9"))
    assert first["verification_uri"] == "/cli/authorize" and first["user_code"] not in first["verification_uri"]
    assert devices.by_device_hash("h") is None  # an old sign-in is removed
    for _ in range(DEVICE_STARTS - 1): asyncio.run(svc.start_device_from("203.0.113.9"))
    with pytest.raises(AppError) as e: asyncio.run(svc.start_device_from("203.0.113.9"))
    assert e.value.code == "RATE_LIMITED"
    assert asyncio.run(svc.start_device_from("198.51.100.4"))["user_code"]  # another client is not affected


def test_last_used_is_written_at_most_every_few_minutes(monkeypatch):
    """Review finding 12 (TASK-0205): every request with a token wrote last_used; user_for_token was unused."""
    from app.repositories import PersonalAccessTokenRepository
    from app.services.pat_service import PatService
    assert not hasattr(PatService, "user_for_token")
    _email, jwt = register()
    secret = c.post("/api/me/tokens", json={"name": "t"}, headers=headers(jwt)).json()["data"]["token"]
    writes = []
    real = PersonalAccessTokenRepository.set_fields
    monkeypatch.setattr(PersonalAccessTokenRepository, "set_fields", lambda self, tid, **v: writes.append(v) or real(self, tid, **v))
    for _ in range(3): assert c.get("/api/me", headers=headers(secret)).status_code == 200
    assert len([w for w in writes if "last_used" in w]) == 1
