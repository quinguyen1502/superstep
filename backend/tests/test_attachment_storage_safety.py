"""TASK-0203: the orphan sweep only touches keys the service makes, under the configured folder or prefix; a folder
that is or holds the data folder is refused; files stay readable after the folder, bucket or prefix changes, and can be
moved between two locations of the same backend."""
import os, time, uuid
import pytest
from app.models import ChatAttachment
from app.models.database import Database
from app.repositories import ChatAttachmentRepository
from app.services.attachment_files import AttachmentFiles
from app.services.attachment_migration import AttachmentMigration
from app.storage import default
from app.storage.fs import FsStore

OLD = time.time() - 7 * 24 * 3600


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = Database(f"sqlite:///{tmp_path}/safe.db"); db.migrate()
    repo = ChatAttachmentRepository(db)
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "fs"); monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp_path / "att"))
    return tmp_path, repo


def old_file(root, rel, body=b"x"):
    p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body); os.utime(p, (OLD, OLD)); return p


def add(repo, stores, data=b"hello", sid="s1"):
    aid = uuid.uuid4().hex
    AttachmentFiles(repo, stores).add(ChatAttachment(id=aid, session_id=sid, turn_id=None, name="a.txt", kind="document", mime="text/plain",
                                                     size=len(data), data=b"", text=None, text_cut=False, created=time.time()), "w1", data)
    return aid


def test_the_sweep_deletes_only_service_keys(env):
    tmp, repo = env
    root = tmp / "att"; stores = default(repo)
    foreign = [old_file(root, "studio.db"), old_file(root, "notes/readme.txt"), old_file(root, "w1/s1/not-an-id"),
               old_file(root, f"nested/w1/s1/{uuid.uuid4().hex}")]  # another install under a nested folder
    orphan = old_file(root, f"w1/s1/{uuid.uuid4().hex}")
    kept = add(repo, stores)
    os.utime(root / "w1" / "s1" / kept, (OLD, OLD))
    assert AttachmentFiles(repo, stores).sweep_orphans() == 1
    assert not orphan.exists() and all(p.exists() for p in foreign) and (root / "w1" / "s1" / kept).exists()


def test_a_folder_holding_the_data_is_refused(env, monkeypatch):
    tmp, repo = env
    db_file = tmp / "data" / "studio.db"; db_file.parent.mkdir(); db_file.write_bytes(b"db")
    monkeypatch.setenv("STUDIO_DB", str(db_file))
    for bad in (tmp / "data", tmp):
        monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(bad))
        stores = default(repo); p = stores.status()
        assert p["ok"] is False and "data" in p["reason"]
        old_file(bad, f"w1/s1/{uuid.uuid4().hex}")
        assert AttachmentFiles(repo, stores).sweep_orphans() == 0  # nothing is swept there
    monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp / "data" / "attachments"))
    assert default(repo).status()["ok"] is True  # a folder inside the data folder is fine


def test_files_stay_readable_after_the_folder_changes_and_move_between_folders(env, monkeypatch):
    tmp, repo = env
    a = add(repo, default(repo), b"first")
    monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp / "att2"))
    stores = default(repo)
    b = add(repo, stores, b"second")
    files = AttachmentFiles(repo, stores)
    assert files.read(repo.get(a)) == b"first" and files.read(repo.get(b)) == b"second"
    out = AttachmentMigration(repo, stores).run("fs")  # fs (old folder) to fs (new folder)
    assert out["moved"] == 1 and out["failed"] == []
    row = repo.get(a)
    assert row.location == str((tmp / "att2").resolve()) and (tmp / "att2" / row.key).read_bytes() == b"first"
    assert not (tmp / "att" / "w1" / "s1" / a).exists()
    assert AttachmentMigration(repo, stores).run("fs")["moved"] == 0


def test_a_visitor_upload_writes_the_file_off_the_event_loop():
    """Review finding 3: the public upload wrote to the store on the event loop thread, blocking every other request."""
    import asyncio, threading
    from app.services.chat_attachment_service import ChatAttachmentService

    class Pub:
        def published(self, slug): return object(), {}
        def visitor(self, *a): return "v"
        def own(self, *a): return "s"
        async def check_message(self, *a, **k): return None

    svc = ChatAttachmentService.__new__(ChatAttachmentService); svc.pub = Pub(); svc._allowed = lambda st: None
    seen = {}
    svc.store = lambda s, st, name, data: seen.setdefault("thread", threading.get_ident()) and {"ok": True}

    async def go():
        seen["loop"] = threading.get_ident()
        return await svc.public_upload("slug", "sid", None, None, "1.2.3.4", "a.txt", b"x")
    asyncio.run(go())
    assert seen["thread"] != seen["loop"]


def test_the_web_proxy_lets_every_allowed_upload_reach_the_api():
    """Review finding 7: nginx refused bodies above 10 MB with its own HTML page, below the 50 MB workflow zip and any
    raised chat file ceiling; it must sit above them and answer in the API's envelope."""
    import re
    from pathlib import Path
    web = Path(__file__).resolve().parents[2] / "frontend"
    if not web.exists(): pytest.skip("no frontend in this checkout")
    conf, docker = (web / "nginx.conf.template").read_text(), (web / "Dockerfile").read_text()
    assert "client_max_body_size ${WEB_MAX_BODY_SIZE};" in conf and '"code":"PAYLOAD_TOO_LARGE"' in conf
    mb = int(re.search(r"WEB_MAX_BODY_SIZE=(\d+)m", docker).group(1))
    assert mb >= 100
