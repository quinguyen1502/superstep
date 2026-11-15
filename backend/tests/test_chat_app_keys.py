"""copy-once credentials, permissions, rotation, concurrency, and access compatibility."""
import base64, concurrent.futures, os, time, uuid
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from app.api.deps import get_db
from app.core import crypto
from app.core.errors import AppError
from app.models import AuditEvent, ChatAppKey, WorkflowChatTrigger
from app.models.database import Database, MIGRATIONS_DIR
from app.repositories.chat_app_keys import ChatAppKeyRepository
from tests.test_chat_sessions import H, c, user
from tests.test_public_chat_api import publish, visitor, err


def test_key_secret_copy_once_rotation_and_audit():
    token = user(); wid, _ = publish(token)
    path = f"/api/workflows/{wid}/chat/app-keys"
    first = c.post(path, headers=H(token), json={"label": "Production", "origins": ["https://Shop.example.com/"]})
    assert first.status_code == 200 and first.headers["cache-control"] == "no-store"
    key = first.json()["data"]
    assert len(base64.urlsafe_b64decode(key["secret"] + "=")) == 32
    assert key["origins"] == ["https://shop.example.com"] and key["last_used_at"] is None
    with get_db().session() as s:
        stored = s.scalar(select(ChatAppKey).where(ChatAppKey.key_id == key["key_id"]))
        assert stored.secret_enc != key["secret"] and crypto.decrypt(stored.secret_enc) == key["secret"]
    second = c.post(path, headers=H(token), json={"label": "Rotation"}).json()["data"]
    limited = c.post(path, headers=H(token), json={"label": "Too many"})
    assert limited.status_code == 409 and err(limited) == "CHAT_APP_KEY_LIMIT"
    listed = c.get(path, headers=H(token))
    assert key["secret"] not in listed.text and second["secret"] not in listed.text and "secret_enc" not in listed.text
    assert c.delete(path + "/" + key["key_id"], headers=H(token)).status_code == 200
    assert c.delete(path + "/" + key["key_id"], headers=H(token)).status_code == 200  # idempotent
    assert c.post(path, headers=H(token), json={"label": "Replacement"}).status_code == 200
    with get_db().session() as s:
        events = list(s.scalars(select(AuditEvent).where(AuditEvent.target_id == wid)))
        assert [e.action for e in events] == ["chat_app_key.create", "chat_app_key.create", "chat_app_key.revoke", "chat_app_key.create"]
        assert key["secret"] not in str([e.details for e in events])


def test_non_owner_is_forbidden_and_keys_are_chat_scoped():
    owner, other = user(), user(); wid, _ = publish(owner); wid2, _ = publish(owner)
    path = f"/api/workflows/{wid}/chat/app-keys"
    key = c.post(path, headers=H(owner), json={"label": "One"}).json()["data"]
    for method, suffix, kwargs in [("get", "", {}), ("post", "", {"json": {"label": "No"}}), ("delete", "/" + key["key_id"], {})]:
        response = getattr(c, method)(path + suffix, headers=H(other), **kwargs)
        assert response.status_code == 403
    assert err(c.delete(f"/api/workflows/{wid2}/chat/app-keys/{key['key_id']}", headers=H(owner))) == "CHAT_APP_KEY_NOT_FOUND"
    assert c.get(path).status_code == 401
    assert err(c.post(path, headers=H(owner), json={"label": "  "})) == "CHAT_SETTINGS_INVALID"
    assert err(c.post(path, headers=H(owner), json={"label": "Bad", "origins": ["https://example.com/path"]})) == "CHAT_EMBED_ORIGIN_INVALID"


def test_access_sets_keep_legacy_behavior_and_app_fails_closed():
    token = user(); wid, slug = publish(token); v = visitor()
    path = f"/api/workflows/{wid}/chat"
    for modes in (["anonymous", "app"], ["anonymous", "signed_in", "app"], "anonymous"):
        r = c.put(path, headers=H(token), json={"access": modes})
        assert r.status_code == 200 and r.json()["data"]["access"] == modes
        assert v.post(f"/api/public/v1/chat/{slug}/sessions").status_code == 200
    assert c.put(path, headers=H(token), json={"access": ["app"]}).status_code == 200
    assert err(v.post(f"/api/public/v1/chat/{slug}/sessions")) == "CHAT_TOKEN_REQUIRED"
    for bad in ([], ["studio", "app"], ["unknown"], "unknown"):
        assert err(c.put(path, headers=H(token), json={"access": bad})) == "CHAT_SETTINGS_INVALID"
    c.put(path, headers=H(token), json={"access": ["signed_in"]})
    assert err(v.post(f"/api/public/v1/chat/{slug}/sessions")) == "CHAT_SIGN_IN_REQUIRED"
    assert c.post(f"/api/public/v1/chat/{slug}/sessions", headers=H(token)).status_code == 200


def test_admin_can_manage_keys_and_workflow_delete_removes_secrets():
    owner = user(); wid, _ = publish(owner)
    admin = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    path = f"/api/workflows/{wid}/chat/app-keys"
    key = c.post(path, headers=H(admin), json={"label": "Admin-created"}).json()["data"]
    assert c.get(path, headers=H(admin)).json()["data"][0]["key_id"] == key["key_id"]
    assert c.delete(path + "/" + key["key_id"], headers=H(admin)).status_code == 200
    assert c.delete(f"/api/workflows/{wid}", headers=H(owner)).status_code == 200
    with get_db().session() as s:
        assert s.scalar(select(ChatAppKey).where(ChatAppKey.key_id == key["key_id"])) is None


def test_simultaneous_creation_cannot_exceed_two(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'keys.db'}"); db.migrate()
    tid = uuid.uuid4().hex
    with db.session() as s:
        s.add(WorkflowChatTrigger(id=tid, workflow_id="w", owner="u", name="Web", channel_id="web", place="web", command=tid,
                                  input_field="message", reply_field="reply", enabled=True, created=time.time())); s.commit()
    repo = ChatAppKeyRepository(db)
    def create(i):
        try:
            repo.create(ChatAppKey(id=str(i), trigger_id=tid, key_id=f"ck_{i}", secret_enc="encrypted", label=str(i),
                origins="[]", created_by="u", created_at=time.time()))
            return "ok"
        except AppError as e: return e.code
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(create, range(4)))
    assert sorted(results) == ["CHAT_APP_KEY_LIMIT", "CHAT_APP_KEY_LIMIT", "ok", "ok"]
    assert len(repo.list(tid)) == 2


@pytest.mark.parametrize("dialect", ["sqlite", "postgres"])
def test_migration_upgrade_downgrade(tmp_path, dialect):
    url = f"sqlite:///{tmp_path / 'migration.db'}" if dialect == "sqlite" else os.environ.get("TEST_DATABASE_URL")
    if not url or (dialect == "postgres" and not url.startswith("postgres")): pytest.skip("Postgres TEST_DATABASE_URL is not set")
    db = Database(url)
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    # A dedicated Postgres schema avoids downgrading any shared test database.
    schema = "keys_" + uuid.uuid4().hex[:12]
    with db.engine.begin() as conn:
        if dialect == "postgres":
            from sqlalchemy.schema import CreateSchema
            conn.execute(CreateSchema(schema)); conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        assert "chat_app_keys" in inspect(conn).get_table_names()
        assert {"external_user", "app_key_id"} <= {x["name"] for x in inspect(conn).get_columns("chat_sessions")}
        command.downgrade(cfg, "0050_pat_name_unique")
        assert "chat_app_keys" not in inspect(conn).get_table_names()
        assert "external_user" not in {x["name"] for x in inspect(conn).get_columns("chat_sessions")}
        command.upgrade(cfg, "head")
        if dialect == "postgres":
            from sqlalchemy.schema import DropSchema
            conn.execute(DropSchema(schema, cascade=True))
    db.engine.dispose()
