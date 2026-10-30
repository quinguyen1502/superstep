"""TASK-0175 (REQ-0077, DEC-0072 decision 2): Chat settings turn attachments on, and a message's files reach the run
as a list field of records without bytes."""
import json
import pytest
from app.api.deps import get_db
from app.repositories import RunRepository
from tests.chat_files import PNG, pdf
from tests.test_chat_sessions import ECHO, H, STATE, c, say, turns, user
from tests.test_public_chat_api import err, visitor

FILES_WF = {**ECHO, "name": "Files chat", "state": STATE + [{"name": "files", "type": "list"}]}


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


def files_chat(tok, **a):
    wid = c.post("/api/workflows", json=FILES_WF, headers=H(tok)).json()["data"]["id"]
    r = c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "attachments": {"enabled": True, "field": "files", **a}}, headers=H(tok)).json()
    assert r["success"], r
    sid = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    return wid, sid


def up(tok, sid, name, data):
    return c.post(f"/api/chat/sessions/{sid}/attachments", files={"file": (name, data)}, headers=H(tok)).json()


def run_input(evs):
    rid = next(e["run_id"] for e in evs if e.get("run_id"))
    return json.loads(RunRepository(get_db()).get(rid).input)


def test_settings_are_off_by_default_and_checked():
    tok = user(); wid = c.post("/api/workflows", json=FILES_WF, headers=H(tok)).json()["data"]["id"]
    d = c.get(f"/api/workflows/{wid}/chat", headers=H(tok)).json()["data"]
    assert d["attachments"] == {"enabled": False, "kinds": ["document", "image"], "max_files": 5, "max_mb": 10, "field": "files"}
    assert d["attachment_ceiling"] == {"max_mb": 10, "max_files": 5}
    put = lambda a: c.put(f"/api/workflows/{wid}/chat", json={"attachments": a}, headers=H(tok))  # noqa: E731
    r = put({"enabled": True, "max_mb": 11}); assert (err(r), r.json()["error"]["details"]) == ("CHAT_ATTACHMENT_LIMIT", {"field": "attachments.max_mb", "max_files": 5, "max_mb": 10})
    assert "MB" in r.json()["error"]["message"]
    for a, field in [({"kinds": []}, "kinds"), ({"kinds": ["audio"]}, "kinds"), ({"max_files": 0}, "max_files"),
                     ({"enabled": True, "field": "message"}, "field"), ({"enabled": True, "field": "nope"}, "field")]:
        assert put(a).json()["error"]["details"]["field"] == f"attachments.{field}", a
    ok = put({"enabled": True, "kinds": ["image"], "max_files": 2, "max_mb": 3}).json()["data"]["attachments"]
    assert ok == {"enabled": True, "kinds": ["image"], "max_files": 2, "max_mb": 3, "field": "files"}
    assert put({"max_files": 1}).json()["data"]["attachments"]["kinds"] == ["image"]  # a partial change keeps the rest


def test_a_message_with_a_pdf_and_an_image_gives_the_run_both():
    tok = user(); _wid, sid = files_chat(tok)
    a = up(tok, sid, "invoice.pdf", pdf())["data"]; b = up(tok, sid, "shot.png", PNG)["data"]
    evs = say(tok, {"chat_session_id": sid, "message": "Summarise this", "attachment_ids": [a["id"], b["id"]]})
    files = run_input(evs)["files"]
    assert files == [{"id": a["id"], "name": "invoice.pdf", "type": "application/pdf", "size": len(pdf()), "text": "Invoice 42 total 99 USD", "text_cut": False},
                     {"id": b["id"], "name": "shot.png", "type": "image/png", "size": len(PNG)}]
    t = turns(tok, sid)["turns"]
    assert [x["name"] for x in t[0]["attachments"]] == ["invoice.pdf", "shot.png"] and t[1]["attachments"] == []
    # sent files cannot be sent again or removed
    e = say(tok, {"chat_session_id": sid, "message": "again", "attachment_ids": [a["id"]]})[-1]
    assert e["error"]["code"] == "CHAT_ATTACHMENT_NOT_FOUND"
    assert err(c.delete(f"/api/chat/sessions/{sid}/attachments/{a['id']}", headers=H(tok))) == "CHAT_ATTACHMENT_NOT_FOUND"
    # a message without files gets an empty list, and files alone are a message
    assert run_input(say(tok, {"chat_session_id": sid, "message": "hi"}))["files"] == []
    c2 = up(tok, sid, "n.txt", b"note")["data"]
    assert run_input(say(tok, {"chat_session_id": sid, "attachment_ids": [c2["id"]]}))["files"][0]["text"] == "note"


def test_ids_of_another_session_are_refused_and_off_refuses_ids():
    tok = user(); wid, sid = files_chat(tok)
    other = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    a = up(tok, other, "n.txt", b"x")["data"]
    assert say(tok, {"chat_session_id": sid, "message": "hi", "attachment_ids": [a["id"]]})[-1]["error"]["code"] == "CHAT_ATTACHMENT_NOT_FOUND"
    c.put(f"/api/workflows/{wid}/chat", json={"attachments": {"enabled": False}}, headers=H(tok))
    assert say(tok, {"chat_session_id": other, "message": "hi", "attachment_ids": [a["id"]]})[-1]["error"]["code"] == "CHAT_ATTACHMENTS_OFF"
    assert up(tok, other, "n.txt", b"x")["error"]["code"] == "CHAT_ATTACHMENTS_OFF"


def test_the_public_page_sends_files_and_answers_stay_text_only():
    tok = user(); wid, _sid = files_chat(tok)
    c.put(f"/api/workflows/{wid}/chat", json={"access": "anonymous", "slug": f"files-{wid.lower()}"[:40]}, headers=H(tok))
    slug = c.get(f"/api/workflows/{wid}/chat", headers=H(tok)).json()["data"]["slug"]
    v = visitor(); sid = v.post(f"/api/public/chat/{slug}/sessions").json()["data"]["id"]
    a = v.post(f"/api/public/chat/{slug}/sessions/{sid}/attachments", files={"file": ("invoice.pdf", pdf())}).json()["data"]
    token = next(x.value for x in v.cookies.jar)
    with v.websocket_connect(f"/ws/public/chat/{slug}?visitor={token}", headers={"origin": "https://testserver"}) as w:
        w.send_json({"chat_session_id": sid, "message": "Read it", "attachment_ids": [a["id"]]})
        while (e := w.receive_json())["type"] not in ("run_summary", "error"): pass
    assert e["type"] == "run_summary", e
    turn = v.get(f"/api/public/chat/{slug}/sessions/{sid}").json()["data"]["turns"][0]
    assert turn["attachments"] == [{"id": a["id"], "name": "invoice.pdf", "kind": "document", "mime": "application/pdf", "size": len(pdf())}]
    with v.websocket_connect(f"/ws/public/chat/{slug}?visitor={token}", headers={"origin": "https://testserver"}) as w:
        w.send_json({"chat_session_id": sid, "response": "yes", "attachment_ids": [a["id"]]})
        assert w.receive_json()["error"]["code"] == "RUN_REQUEST_INVALID"
