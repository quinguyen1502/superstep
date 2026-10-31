"""TASK-0194 (REQ-0080, DEC-0074): moving attachment bytes between backends, and attachments in and out of a backup.

Moves go all ways between db, fs and an external stand-in (and the real s3 backend against MinIO in CI), check size and
SHA-256, resume after an interruption, and do nothing the second time."""
import hashlib, io, json, os, tarfile, time, uuid
import pytest
from app.admin_cmd import main
from app.core.errors import AppError
from app.models import ChatAttachment
from app.models.database import Database
from app.repositories import ChatAttachmentRepository
from app.services.attachment_archive import AttachmentArchive
from app.services.attachment_files import AttachmentFiles
from app.services.attachment_migration import AttachmentMigration
from app.storage import StoreError, Stores
from app.storage.db import DbStore
from app.storage.fs import FsStore
from tests.storage_contract import MemStore


class Ext(MemStore):
    name = "s3"  # an external backend in memory, standing in for a bucket


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = Database(f"sqlite:///{tmp_path}/mig.db"); db.migrate()
    repo, ext = ChatAttachmentRepository(db), Ext()
    stores = Stores({"db": lambda: DbStore(repo), "fs": lambda: FsStore(str(tmp_path / "att")), "s3": lambda: ext})
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "db")
    return db, repo, stores, ext


def blob(i): return hashlib.sha256(str(i).encode()).digest() * (40 + i)


def seed(repo, stores, n=5, on="db"):
    files = AttachmentFiles(repo, stores); out = {}
    os.environ["STUDIO_ATTACHMENT_STORAGE"] = on
    for i in range(n):
        aid = uuid.uuid4().hex; data = blob(i)
        files.add(ChatAttachment(id=aid, session_id="s1", turn_id=None, name=f"f{i}.bin", kind="document", mime="application/pdf",
                                 size=len(data), data=b"", text=None, text_cut=False, created=time.time() + i), None, data)
        out[aid] = data
    return out


def readable(repo, stores, want):
    files = AttachmentFiles(repo, stores)
    for aid, data in want.items(): assert files.read(repo.get(aid)) == data


def test_moves_all_ways_and_the_second_run_is_a_no_op(env):
    _db, repo, stores, ext = env
    want = seed(repo, stores)
    m = AttachmentMigration(repo, stores)
    for to in ("fs", "s3", "db", "s3", "fs", "db"):
        out = m.run(to, batch=2)
        assert out["moved"] == 5 and out["failed"] == [] and out["pending"] == 0 and out["bytes"] == sum(map(len, want.values()))
        assert set(repo.by_storage()) == {to}
        readable(repo, stores, want)
        assert m.run(to)["moved"] == 0  # nothing left: a no-op
        if to != "s3": assert ext.objects == {}  # the old copies are gone
        if to != "fs": assert list(stores.get("fs").iter_keys()) == []


def test_dry_run_and_resume_after_an_interruption(env):
    _db, repo, stores, ext = env
    want = seed(repo, stores, 6)
    m = AttachmentMigration(repo, stores)
    assert m.run("s3", dry_run=True) == {"to": "s3", "dry_run": True, "moved": 0, "bytes": 0, "failed": [], "pending": 6}
    assert ext.objects == {} and set(repo.by_storage()) == {"db"}
    first = m.run("s3", batch=2, limit=4)  # stopped part-way
    assert first["moved"] == 4 and first["pending"] == 2 and repo.by_storage()["db"]["files"] == 2
    readable(repo, stores, want)  # every file still reads, wherever it is
    assert m.run("s3")["moved"] == 2 and set(repo.by_storage()) == {"s3"}
    readable(repo, stores, want)


def test_a_bad_copy_or_a_missing_source_leaves_the_file_where_it_is(env, monkeypatch):
    _db, repo, stores, ext = env
    want = seed(repo, stores, 3)
    m = AttachmentMigration(repo, stores)
    real = ext.put; calls = []
    def corrupt(key, data, mime):
        if not key.startswith("_probe/"): calls.append(key)
        real(key, data[:-1] + b"!" if len(calls) == 1 and not key.startswith("_probe/") else data, mime)
    monkeypatch.setattr(ext, "put", corrupt)
    out = m.run("s3")
    assert out["moved"] == 2 and [f["reason"] for f in out["failed"]] == ["checksum does not match after the copy"]
    assert repo.by_storage()["db"]["files"] == 1 and len(ext.objects) == 2  # the bad copy was removed
    readable(repo, stores, want)
    gone = next(iter(ext.objects)); ext.objects.pop(gone)
    out = m.run("fs")
    assert out["moved"] == 2 and [f["reason"] for f in out["failed"]] == ["missing on its backend"]


def test_errors_use_the_envelope_codes(env):
    _db, repo, stores, _ext = env
    m = AttachmentMigration(repo, stores)
    with pytest.raises(AppError) as e: m.run("ftp")
    assert e.value.code == "ATTACHMENT_MIGRATE_TARGET" and e.value.status == 400
    with pytest.raises(AppError) as e: m.run("fs", batch=0)
    assert e.value.code == "ATTACHMENT_MIGRATE_BATCH"
    bad = Stores({"db": lambda: DbStore(repo), "fs": lambda: (_ for _ in ()).throw(StoreError("cannot write the attachment folder"))})
    with pytest.raises(AppError) as e: AttachmentMigration(repo, bad).run("fs")
    assert e.value.code == "CHAT_ATTACHMENT_STORAGE" and e.value.status == 503


def test_archive_round_trip_writes_only_known_keys(env, monkeypatch):
    _db, repo, stores, ext = env
    want = seed(repo, stores, 3, on="fs")
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "fs")
    seed(repo, stores, 2, on="s3")
    assert AttachmentArchive(repo, stores).export(io.BytesIO(), ("fs", "s3")) == 5  # a bucket only when asked
    buf = io.BytesIO(); assert AttachmentArchive(repo, stores).export(buf) == 3
    names = tarfile.open(fileobj=io.BytesIO(buf.getvalue())).getnames()
    assert all(n.startswith("attachments/adhoc/s1/") for n in names)
    fs = stores.get("fs")
    for k, _t in list(fs.iter_keys()): fs.delete(k)  # a new host: the folder is empty
    planted = io.BytesIO()  # the archive plus a member no row names
    with tarfile.open(fileobj=planted, mode="w") as t:
        for m_ in tarfile.open(fileobj=io.BytesIO(buf.getvalue())).getmembers():
            t.addfile(m_, tarfile.open(fileobj=io.BytesIO(buf.getvalue())).extractfile(m_.name))
        info = tarfile.TarInfo("attachments/evil/x"); info.size = 3; t.addfile(info, io.BytesIO(b"bad"))
    assert AttachmentArchive(repo, stores).restore(io.BytesIO(planted.getvalue())) == 3
    assert not fs.exists("evil/x")
    readable(repo, stores, want)
    seed(repo, stores, 2, on="db")
    out = io.BytesIO(); assert AttachmentArchive(repo, stores).export(out, ("db",)) == 0  # db files travel in the database dump


def test_admin_cmd_prints_json(tmp_path, monkeypatch, capsys):
    db = Database(f"sqlite:///{tmp_path}/cmd.db")
    monkeypatch.setattr("app.admin_cmd.get_db", lambda: db)
    monkeypatch.setattr("app.api.deps.get_db", lambda: db)
    monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp_path / "att"))
    from app.api import deps; deps._attachment_stores.cache_clear()
    try:
        assert main(["attachments-summary"]) == 0
        assert json.loads(capsys.readouterr().out) == {"current": os.environ.get("STUDIO_ATTACHMENT_STORAGE", "db"), "by_storage": {}}
        assert main(["attachments-migrate", "--to", "fs", "--dry-run"]) == 0
        assert json.loads(capsys.readouterr().out)["pending"] == 0
        assert main(["attachments-migrate", "--to", "nowhere"]) == 1
        assert json.loads(capsys.readouterr().err)["code"] == "ATTACHMENT_MIGRATE_TARGET"
    finally: deps._attachment_stores.cache_clear()


def test_the_admin_route_is_for_admins():
    from test_rbac import H, admin_token, c, code, register
    adm, ed = admin_token(), register("mig")
    assert code(c.get("/api/admin/attachments", headers=H(ed.token))) == "PERMISSION_DENIED"
    assert code(c.post("/api/admin/attachments/migrate", json={"to": "db"}, headers=H(ed.token))) == "PERMISSION_DENIED"
    s = c.get("/api/admin/attachments", headers=H(adm)).json()["data"]
    assert s["current"] == "db" and set(s["by_storage"]) <= {"db", "mem", "fs", "s3"}
    assert code(c.post("/api/admin/attachments/migrate", json={"to": "ftp"}, headers=H(adm))) == "ATTACHMENT_MIGRATE_TARGET"
    r = c.post("/api/admin/attachments/migrate", json={"to": "db", "dry_run": True}, headers=H(adm)).json()["data"]
    assert r["dry_run"] is True and r["moved"] == 0


S3 = {k: os.environ.get(f"STUDIO_TEST_S3_{k}", "") for k in ("ENDPOINT", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")}


@pytest.mark.skipif(not (S3["ENDPOINT"] and S3["BUCKET"]), reason="no S3-compatible test endpoint (STUDIO_TEST_S3_ENDPOINT)")
def test_moves_through_a_real_bucket(tmp_path, monkeypatch):
    from app.storage.s3 import S3Store
    db = Database(f"sqlite:///{tmp_path}/s3.db"); db.migrate(); repo = ChatAttachmentRepository(db)
    s3 = S3Store(S3["BUCKET"], prefix=f"mig-{uuid.uuid4().hex[:8]}", endpoint=S3["ENDPOINT"], region="us-east-1",
                 access_key=S3["ACCESS_KEY_ID"], secret_key=S3["SECRET_ACCESS_KEY"], path_style=True)
    stores = Stores({"db": lambda: DbStore(repo), "fs": lambda: FsStore(str(tmp_path / "att")), "s3": lambda: s3})
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "db")
    want = seed(repo, stores, 4); m = AttachmentMigration(repo, stores)
    for to in ("s3", "fs", "s3", "db"):
        assert m.run(to, batch=3)["moved"] == 4 and set(repo.by_storage()) == {to}
        readable(repo, stores, want)
    assert list(s3.iter_keys()) == []
