"""TASK-0207: the three points of the re-review after #258..#261. Request bodies are bounded outside the upload routes
(nginx and the app), an approved CLI sign-in that is never collected leaves no usable token, and a row's recorded S3
location is enough to read it after the s3 settings are removed."""
import asyncio, os, re, time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
MB = 1024 * 1024


# ---- 1. body sizes ----
def test_unauthenticated_callbacks_refuse_a_large_body_before_reading_it():
    for path in ("/api/approvals/callback/slack", "/api/channels/events/slack"):
        r = c.post(path, content=b"x" * (2 * MB), headers={"content-type": "application/json"})
        assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE", path


def test_other_routes_are_capped_and_upload_routes_are_not():
    r = c.post("/api/auth/login", content=b"x" * (11 * MB), headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    from app.api.body_limit import limit_for
    assert limit_for("/api/import") >= 50 * MB and limit_for("/api/chat/sessions/s1/attachments") > 10 * MB
    assert limit_for("/api/public/chat/demo/sessions/s1/attachments") > 10 * MB and limit_for("/api/knowledge-bases/k/documents") > 10 * MB
    assert limit_for("/api/approvals/callback/slack") == MB and limit_for("/api/workflows") == 10 * MB


def test_nginx_keeps_10m_and_opens_only_the_upload_routes():
    web = Path(__file__).resolve().parents[2] / "frontend"
    if not web.exists(): pytest.skip("no frontend in this checkout")
    conf = (web / "nginx.conf.template").read_text()
    server = conf.split("location", 1)[0]
    assert "client_max_body_size 10m;" in server and "${WEB_MAX_BODY_SIZE}" not in server
    up = [b for b in re.findall(r"location ~ \^/api/[^{]*\{[^}]*\}", conf) if "WEB_MAX_BODY_SIZE" in b]
    assert len(up) == 1 and "attachments" in up[0] and "import" in up[0] and "documents" in up[0]


# ---- 2. an approved sign-in that is never collected ----
def test_an_approved_sign_in_never_collected_holds_no_token_and_cannot_be_collected_late(tmp_path):
    from app.core.errors import AppError
    from app.models import User
    from app.models.database import Database
    from app.repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
    from app.services.pat_service import PatService
    db = Database(f"sqlite:///{tmp_path}/p.db"); db.migrate()
    users, pats, devices = UserRepository(db), PersonalAccessTokenRepository(db), CliDeviceRepository(db)
    with db.session() as s: s.add(User(id="u1", email="u1@example.com", password="x", created=0)); s.commit()
    svc = PatService(pats, devices, users)
    started = svc.start_device("laptop")
    svc.approve("u1", started["user_code"], None)
    row = devices.by_device_hash(__import__("app.services.pat_service", fromlist=["digest"]).digest(started["device_code"]))
    assert not row.secret and not pats.list_active("u1")  # no token exists until the CLI collects it
    devices.set_fields(row.id, expires=time.time() - 1)
    with pytest.raises(AppError) as e: svc.poll(started["device_code"])
    assert e.value.code == "CLI_DEVICE_EXPIRED" and not pats.list_active("u1")
    # a fresh one is collected once and works
    again = svc.start_device(); svc.approve("u1", again["user_code"], "desk")
    assert svc.poll(again["device_code"])["token"].startswith("pat_") and len(pats.list_active("u1")) == 1
    with pytest.raises(AppError): svc.poll(again["device_code"])


def test_a_legacy_secret_is_revoked_and_cleared_when_it_expires(tmp_path):
    from app.models import CliDevice, PersonalAccessToken, User
    from app.models.database import Database
    from app.repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
    from app.services.pat_service import PatService
    db = Database(f"sqlite:///{tmp_path}/q.db"); db.migrate()
    pats, devices = PersonalAccessTokenRepository(db), CliDeviceRepository(db)
    with db.session() as s: s.add(User(id="u1", email="u1@example.com", password="x", created=0)); s.commit()
    pats.add(PersonalAccessToken(id="t1", user_id="u1", name="CLI", token_hash="h", prefix="pat_x", created=0, last_used=None, revoked=None))
    old = time.time() - 3600
    devices.add(CliDevice(id="d1", device_hash="dh", user_code_hash="uh", name="CLI", user_id="u1", token_id="t1", status="approved",
                          secret="pat_plaintext", expires=old, created=old))
    PatService(pats, devices, UserRepository(db)).start_device()
    assert devices.by_device_hash("dh") is None and pats.get("t1").revoked is not None


# ---- 3. a row's S3 location after the s3 settings are gone ----
def test_old_s3_files_stay_readable_without_the_bucket_setting(monkeypatch):
    pytest.importorskip("boto3"); moto = pytest.importorskip("moto")
    from app.storage import default
    from app.storage.s3 import S3Store
    for k, v in {"ACCESS_KEY_ID": "AKIATEST", "SECRET_ACCESS_KEY": "secret", "REGION": "us-east-1"}.items():
        monkeypatch.setenv(f"STUDIO_ATTACHMENT_S3_{k}", v)
    monkeypatch.delenv("STUDIO_ATTACHMENT_S3_BUCKET", raising=False); monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "fs")
    with moto.mock_aws():
        import boto3
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="old-bucket")
        S3Store("old-bucket", prefix="team", region="us-east-1", access_key="AKIATEST", secret_key="secret").put("w/s/" + "a" * 32, b"kept", "text/plain")
        assert default(None).get("s3", "old-bucket/team").read("w/s/" + "a" * 32) == b"kept"


def test_missing_s3_credentials_are_named():
    pytest.importorskip("boto3")
    from botocore.exceptions import NoCredentialsError
    from app.storage.s3 import S3Store
    e = S3Store._error(NoCredentialsError())
    assert "STUDIO_ATTACHMENT_S3_ACCESS_KEY_ID" in e.reason


def test_a_body_without_a_length_is_counted():
    def chunks():
        for _ in range(3): yield b"x" * (512 * 1024)
    r = c.post("/api/approvals/callback/slack", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
