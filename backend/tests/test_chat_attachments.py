"""TASK-0174 (REQ-0077, DEC-0072): chat attachments are stored in the database, typed by their bytes, limited, kept
to their session, served only as downloads, and removed with their session or when never sent."""
import json, time
import pytest
from app.api.deps import chat_session_service, get_db
from app.repositories import ChatAttachmentRepository, ChatTriggerRepository
from app.services.chat_attachment_service import sniff
from tests.chat_files import PNG, pdf
from tests.test_chat_sessions import H, c, chat, user
from tests.test_public_chat_api import err, publish, visitor


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


def allow(wid, **a):
    """Turns attachments on in the chat's settings (TASK-0175 adds them to the Chat settings form)."""
    triggers = ChatTriggerRepository(get_db()); t = triggers.web(wid)
    st = json.loads(t.settings or "{}"); st["attachments"] = {"enabled": True, **a}
    triggers.set_fields(t.id, settings=json.dumps(st))


def up(client, url, name, data, **kw):
    return client.post(url, files={"file": (name, data, "application/octet-stream")}, **kw)


def public_session(**a):
    tok = user(); wid, slug = publish(tok); allow(wid, **a)
    v = visitor(); sid = v.post(f"/api/public/chat/{slug}/sessions").json()["data"]["id"]
    return tok, wid, slug, v, sid, f"/api/public/chat/{slug}/sessions/{sid}/attachments"


def test_types_are_read_from_the_bytes():
    assert sniff("a.pdf", pdf()) == ("document", "application/pdf")
    assert sniff("shot.PNG", PNG) == ("image", "image/png")
    assert sniff("a.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ("image", "image/webp")
    assert sniff("notes.md", "# Hi đây".encode()) == ("document", "text/markdown")
    assert sniff("a.pdf", b"just text") is None  # renamed
    assert sniff("a.png", pdf()) is None  # the name must agree with the bytes
    assert sniff("a.txt", b"\x00\x01binary") is None
    assert sniff("a.exe", b"MZ\x90\x00") is None


def test_a_visitor_uploads_downloads_and_removes_files():
    _tok, _wid, slug, v, sid, url = public_session()
    a = up(v, url, "invoice.pdf", pdf()).json()
    assert a["success"], a
    a = a["data"]; assert (a["name"], a["kind"], a["mime"]) == ("invoice.pdf", "document", "application/pdf")
    b = up(v, url, "shot.png", PNG).json()["data"]; assert b["kind"] == "image"
    r = v.get(f"{url}/{a['id']}")
    assert r.status_code == 200 and r.content == pdf()
    assert r.headers["content-disposition"].startswith("attachment;") and r.headers["x-content-type-options"] == "nosniff"
    assert v.delete(f"{url}/{b['id']}").json()["data"] == {"ok": True}
    assert err(v.get(f"{url}/{b['id']}")) == "CHAT_ATTACHMENT_NOT_FOUND"


def test_bad_types_sizes_and_counts_are_refused(monkeypatch):
    _tok, _wid, _slug, v, _sid, url = public_session(max_files=2, max_mb=1)
    r = up(v, url, "fake.pdf", b"not a pdf at all"); assert (err(r), r.status_code) == ("CHAT_ATTACHMENT_TYPE", 400)
    r = up(v, url, "big.txt", b"a" * (1024 * 1024 + 1)); assert (err(r), r.status_code) == ("CHAT_ATTACHMENT_TOO_LARGE", 413)
    assert r.json()["error"]["details"]["max_mb"] == 1
    for i in range(2): assert up(v, url, f"n{i}.txt", b"hello").json()["success"]
    assert err(up(v, url, "n3.txt", b"hello")) == "CHAT_ATTACHMENT_TOO_MANY"
    _tok, _wid, _slug, v, _sid, url = public_session(kinds=["document"])
    assert err(up(v, url, "shot.png", PNG)) == "CHAT_ATTACHMENT_TYPE"


def test_the_operator_ceiling_refuses_an_11_mb_file_before_reading_it(monkeypatch):
    _tok, _wid, _slug, v, _sid, url = public_session(max_mb=50)  # a chat cannot raise the ceiling (10 MB)
    r = up(v, url, "big.txt", b"a" * (11 * 1024 * 1024)); assert err(r) == "CHAT_ATTACHMENT_TOO_LARGE"
    assert r.json()["error"]["details"]["max_mb"] == 10
    monkeypatch.setenv("STUDIO_CHAT_ATTACHMENT_MAX_FILES", "1")
    assert up(v, url, "a.txt", b"x").json()["success"] and err(up(v, url, "b.txt", b"x")) == "CHAT_ATTACHMENT_TOO_MANY"


def test_another_visitor_and_a_guessed_id_find_nothing():
    _tok, _wid, slug, v, sid, url = public_session()
    a = up(v, url, "invoice.pdf", pdf()).json()["data"]
    other = visitor(); other.post(f"/api/public/chat/{slug}/sessions")
    assert err(other.get(f"{url}/{a['id']}")) == "CHAT_SESSION_NOT_FOUND"  # not their session
    osid = other.post(f"/api/public/chat/{slug}/sessions").json()["data"]["id"]
    assert err(other.get(f"/api/public/chat/{slug}/sessions/{osid}/attachments/{a['id']}")) == "CHAT_ATTACHMENT_NOT_FOUND"
    assert err(v.get(f"{url}/{'0' * 32}")) == "CHAT_ATTACHMENT_NOT_FOUND"


def test_attachments_off_and_demo_mode_refuse_uploads(monkeypatch):
    tok = user(); _wid, slug = publish(tok); v = visitor()
    sid = v.post(f"/api/public/chat/{slug}/sessions").json()["data"]["id"]
    r = up(v, f"/api/public/chat/{slug}/sessions/{sid}/attachments", "a.txt", b"x"); assert (err(r), r.status_code) == ("CHAT_ATTACHMENTS_OFF", 403)
    wid, sid = chat(tok); allow(wid)
    monkeypatch.setenv("STUDIO_DEMO_MODE", "1")
    assert err(up(c, f"/api/chat/sessions/{sid}/attachments", "a.txt", b"x", headers=H(tok))) == "CHAT_ATTACHMENT_DEMO"


def test_uploads_count_against_the_visitor_rate_limit(monkeypatch):
    monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_VISITOR", "2")
    _tok, _wid, _slug, v, _sid, url = public_session()
    assert up(v, url, "a.txt", b"x").json()["success"] and up(v, url, "b.txt", b"x").json()["success"]
    assert err(up(v, url, "c.txt", b"x")) == "RATE_LIMITED"


def test_studio_chat_and_the_builder_from_the_visitors_list():
    tok = user(); wid, sid = chat(tok); allow(wid)
    a = up(c, f"/api/chat/sessions/{sid}/attachments", "notes.md", b"# Plan", headers=H(tok)).json()["data"]
    assert c.get(f"/api/chat/sessions/{sid}/attachments/{a['id']}", headers=H(tok)).content == b"# Plan"
    assert err(c.get(f"/api/chat/sessions/{sid}/attachments/{a['id']}", headers=H(user()))) == "CHAT_SESSION_NOT_FOUND"
    _tok, pwid, _slug, v, psid, url = public_session()
    b = up(v, url, "shot.png", PNG).json()["data"]
    builder = f"/api/workflows/{pwid}/chat/visitors/{psid}/attachments/{b['id']}"
    r = c.get(builder, headers=H(_tok)); assert r.content == PNG and r.headers["x-content-type-options"] == "nosniff"
    assert err(c.get(builder, headers=H(tok))) in ("WORKFLOW_NOT_FOUND", "FORBIDDEN")  # not their workflow
    assert err(c.get(f"/api/workflows/{wid}/chat/visitors/{sid}/attachments/{a['id']}", headers=H(tok))) == "CHAT_ATTACHMENT_NOT_FOUND"  # a studio chat


def test_retention_removes_files_and_stale_uploads():
    repo = ChatAttachmentRepository(get_db())
    tok, wid, slug, v, sid, url = public_session()
    a = up(v, url, "a.txt", b"x").json()["data"]
    _t2, _w2, _s2, v2, sid2, url2 = public_session()
    stale = up(v2, url2, "old.txt", b"x").json()["data"]
    with get_db().session() as s:
        from app.models import ChatAttachment
        s.get(ChatAttachment, stale["id"]).created = time.time() - 7200; s.commit()
    svc = chat_session_service(); svc.sessions.delete(sid)
    assert repo.get(a["id"]) is None
    svc.cleanup()
    assert repo.get(stale["id"]) is None
    fresh = up(v2, url2, "new.txt", b"x").json()["data"]; svc.cleanup(); assert repo.get(fresh["id"]) is not None
