"""TASK-0192 (REQ-0080, DEC-0074): the `fs` backend passes the shared contract, keeps keys inside its folder, writes
atomically, and serves files of a chat end to end; the worker's heartbeat tells whether api and worker share it."""
import os, stat
import pytest
from app.api import deps
from app.storage import StoreError
from app.storage.fs import FsStore
from tests.storage_contract import check
from tests.test_chat_attachments import public_session, up
from tests.chat_files import pdf


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


@pytest.fixture
def fs(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", "fs"); monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp_path / "att"))
    deps._attachment_stores.cache_clear(); yield tmp_path / "att"; deps._attachment_stores.cache_clear()


def test_fs_backend_contract(tmp_path):
    check(FsStore(str(tmp_path / "root")))


def test_keys_cannot_leave_the_folder(tmp_path):
    s = FsStore(str(tmp_path / "root"))
    for bad in ("../x", "a/../../x", "/etc/passwd", "a//b", "a/./b", "", "a\\b", "a/b c"):
        with pytest.raises(StoreError): s.put(bad, b"x", "text/plain")
    assert not (tmp_path / "x").exists()


def test_no_partial_files_and_empty_folders_go(tmp_path):
    s = FsStore(str(tmp_path / "root")); s.put("w/s/a", b"data", "text/plain")
    assert [p.name for p in (tmp_path / "root" / "w" / "s").iterdir()] == ["a"]  # the temporary file was renamed
    s.delete("w/s/a"); assert not (tmp_path / "root" / "w").exists() and (tmp_path / "root").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
def test_a_read_only_folder_is_reported(tmp_path):
    root = tmp_path / "ro"; root.mkdir(); root.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        p = FsStore(str(root)).probe()
        assert p["ok"] is False and p["reason"].startswith("cannot write to the attachment folder") and str(root) not in p["reason"]
    finally: root.chmod(stat.S_IRWXU)


def test_a_chat_file_on_fs_end_to_end(fs):
    _tok, wid, _slug, v, sid, url = public_session()
    a = up(v, url, "invoice.pdf", pdf()).json()["data"]
    f = fs / wid / sid / a["id"]
    assert f.read_bytes() == pdf()
    d = v.get(f"{url}/{a['id']}")
    assert d.content == pdf() and d.headers["content-security-policy"] == "sandbox" and str(fs) not in str(d.headers)
    v.delete(f"{url}/{a['id']}"); assert not f.exists()


def test_health_and_the_worker_heartbeat(fs):
    from tests.test_chat_sessions import c
    h = c.get("/api/health").json()["data"]
    assert h["attachment_storage"] == "fs" and h["attachment_storage_ok"] is True and h["attachment_storage_worker_seen"] is None
    deps.chat_session_service().cleanup()  # the worker's retention loop writes its heartbeat
    seen = c.get("/api/health").json()["data"]["attachment_storage_worker_seen"]
    assert seen is not None and seen < 60
    assert deps.attachment_files().sweep_orphans(now=10**12) == 0  # the heartbeat is never swept as an orphan
