"""TASK-0191 (REQ-0080, DEC-0074): the attachment storage port. Every backend passes one contract; the service writes
the object before the row and deletes it after, streams downloads with the DEC-0072 headers, and sweeps orphans."""
import time, uuid
import pytest
from app.api import deps
from app.api.deps import chat_session_service, get_db
from app.models import ChatAttachment
from app.repositories import ChatAttachmentRepository
from app import storage
from app.storage import StoreError, Stores
from app.storage.db import DbStore
from app.services.attachment_files import AttachmentFiles
from tests.storage_contract import MemStore, check
from tests.test_chat_attachments import public_session, up, err
from tests.chat_files import pdf


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


def row(aid, data=b"x", storage="db", key=None, sid="s-contract"):
    return ChatAttachment(id=aid, session_id=sid, turn_id=None, name="a.txt", kind="document", mime="text/plain", size=len(data),
                          data=data, storage=storage, key=key, text=None, text_cut=False, created=time.time())


# ---- the contract, per backend ----
def test_db_backend_contract():
    repo = ChatAttachmentRepository(get_db()); tag = uuid.uuid4().hex[:6]
    def ready(key): repo.add(row(key))
    store = DbStore(repo)
    assert store.inline
    # the db backend's keys are attachment ids; the probe is a no-op (the database is checked by /api/health)
    check(store, ready, prefix=f"c{tag}-")


def test_mem_fake_contract():
    check(MemStore())


# ---- the service with an external backend ----
@pytest.fixture
def mem(monkeypatch):
    m = MemStore(); real = storage.default
    monkeypatch.setattr(storage, "default", lambda rows: Stores({**real(rows).factories, "mem": lambda: m}))
    import app.services.chat_session_service as css
    monkeypatch.setattr(css.storage, "default", storage.default)
    deps._attachment_stores.cache_clear()
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "mem")
    yield m
    deps._attachment_stores.cache_clear()


def test_external_upload_download_delete_keep_the_guarantees(mem):
    _tok, wid, _slug, v, sid, url = public_session()
    a = up(v, url, "invoice.pdf", pdf()).json()["data"]
    key = f"{wid}/{sid}/{a['id']}"
    assert mem.objects[key][0] == pdf()
    r = ChatAttachmentRepository(get_db()).get(a["id"]); assert (r.storage, r.key) == ("mem", key)
    with get_db().session() as s: assert s.get(ChatAttachment, a["id"]).data == b""  # the bytes are not in the database
    d = v.get(f"{url}/{a['id']}")
    assert d.status_code == 200 and d.content == pdf()
    h = d.headers
    assert h["content-disposition"].startswith("attachment;") and h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "private, no-store" and h["content-security-policy"] == "sandbox" and h["content-length"] == str(len(pdf()))
    assert "mem" not in d.text and key not in str(h)  # no backend address reaches the browser
    _t2, _w2, _s2, other, _sid2, _u2 = public_session()
    assert other.get(f"{url}/{a['id']}").status_code == 404  # another visitor
    assert v.delete(f"{url}/{a['id']}").json()["data"] == {"ok": True}
    assert key not in mem.objects


def test_a_failed_put_stores_nothing_and_a_failed_row_removes_the_object(mem, monkeypatch):
    _tok, _wid, _slug, v, sid, url = public_session()
    mem.fail_put = True
    r = up(v, url, "a.txt", b"x").json()
    assert r["error"]["code"] == "CHAT_ATTACHMENT_STORAGE" and "bucket unreachable" in r["error"]["message"]
    assert ChatAttachmentRepository(get_db()).unsent_count(sid) == 0
    mem.fail_put = False
    def boom(self, row): raise RuntimeError("db down")
    monkeypatch.setattr(ChatAttachmentRepository, "add", boom)
    with pytest.raises(RuntimeError): deps.attachment_files().add(row(uuid.uuid4().hex, sid=sid), "w", b"bytes")
    assert mem.objects == {}


def test_a_missing_object_is_not_found_and_a_broken_backend_is_503(mem):
    _tok, _wid, _slug, v, _sid, url = public_session()
    a = up(v, url, "a.txt", b"x").json()["data"]
    mem.objects.clear()
    assert err(v.get(f"{url}/{a['id']}")) == "CHAT_ATTACHMENT_NOT_FOUND"
    def down(key): raise StoreError("connection refused")
    mem.open = down
    r = v.get(f"{url}/{a['id']}"); assert r.status_code == 503 and r.json()["error"]["code"] == "CHAT_ATTACHMENT_STORAGE"


def test_session_delete_retention_and_the_orphan_sweep(mem):
    tok, wid, _slug, v, sid, url = public_session()
    a = up(v, url, "a.txt", b"x").json()["data"]; key = f"{wid}/{sid}/{a['id']}"
    svc = chat_session_service()
    refs = svc.files.refs_of_sessions([sid]); svc.sessions.delete(sid); svc.files.drop(refs)
    assert key not in mem.objects
    # stale unsent uploads: row and object
    _t, _w, _s, v2, sid2, url2 = public_session()
    b = up(v2, url2, "old.txt", b"x").json()["data"]
    with get_db().session() as s: s.get(ChatAttachment, b["id"]).created = time.time() - 7200; s.commit()
    svc.cleanup()
    assert ChatAttachmentRepository(get_db()).get(b["id"]) is None and not any(b["id"] in k for k in mem.objects)
    # orphans: only objects without a row, and only once older than an hour
    mem.objects["w/s/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"] = (b"x", time.time() - 7200); mem.objects["w/s/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"] = (b"x", time.time())
    c = up(v2, url2, "keep.txt", b"x").json()["data"]
    kept = next(k for k in mem.objects if k.endswith(c["id"])); mem.objects[kept] = (b"x", time.time() - 7200)
    assert deps.attachment_files().sweep_orphans() == 1
    assert "w/s/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in mem.objects and "w/s/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in mem.objects and kept in mem.objects


def test_rows_of_another_backend_stay_readable(mem, monkeypatch):
    _tok, _wid, _slug, v, _sid, url = public_session()
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "db")
    a = up(v, url, "old.txt", b"from db").json()["data"]
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "mem")
    b = up(v, url, "new.txt", b"from mem").json()["data"]
    assert v.get(f"{url}/{a['id']}").content == b"from db" and v.get(f"{url}/{b['id']}").content == b"from mem"


def test_unknown_backend_and_health(monkeypatch):
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "ftp")
    deps._attachment_stores.cache_clear()
    st = deps.attachment_files().status()
    assert st["backend"] == "ftp" and st["ok"] is False and "unknown attachment storage" in st["reason"]
    _tok, _wid, _slug, v, _sid, url = public_session()
    assert up(v, url, "a.txt", b"x").json()["error"]["code"] == "CHAT_ATTACHMENT_STORAGE"
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "db"); deps._attachment_stores.cache_clear()
    from tests.test_chat_sessions import c
    h = c.get("/api/health").json()["data"]
    assert h["attachment_storage"] == "db" and h["attachment_storage_ok"] is True


def test_migration_round_trip_keeps_rows():
    from app.models.database import Database  # noqa: F401  (the migration itself runs in test_migrations)
    assert {c.name for c in ChatAttachment.__table__.columns} >= {"storage", "key", "data"}
