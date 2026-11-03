"""DEC-0084: isolated branches, durable intent admission and owned file lifecycle."""
import json, os, uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.api.deps import chat_session_service
from tests.test_chat_sessions import H, c, chat, user, say, wait_turns, turns, asking
from tests.test_chat_attachments import allow, up
from tests.test_public_chat_api import publish, err
from tests.test_public_chat_runs import start
from tests.test_chat_ws_v1 import talk


@pytest.fixture(autouse=True)
def no_transport_limits(monkeypatch):
    # Functional cases share the testclient IP with the full backend suite. Quotas are tested explicitly below.
    for kind in ("READ", "VISITOR", "IP", "USER"):
        monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{kind}", "0")


def edit_body(view, index=0, message="edited"):
    return {"turn_id": view["turns"][index]["id"], "message": message,
            "operation_id": uuid.uuid4().hex, "expected_last_turn_id": view["turns"][-1]["id"]}


def prepare(tok, sid, body): return c.post(f"/api/chat/sessions/{sid}/edits", headers=H(tok), json=body)


def execute(tok, result):
    return say(tok, {"chat_session_id": result["session"]["id"], "message": result["message"],
                     "attachment_ids": result["attachment_ids"], "edit_operation_id": result["operation_id"]})


def test_edit_early_message_preserves_source_and_drops_the_future():
    tok = user(); _, sid = chat(tok)
    say(tok, {"chat_session_id": sid, "message": "before"}); wait_turns(tok, sid, 2)
    say(tok, {"chat_session_id": sid, "message": "discard this future"}); before = wait_turns(tok, sid, 4)
    body = edit_body(before)
    result = prepare(tok, sid, body).json()["data"]
    assert result["state"] == "prepared" and result["session"]["turns"] == []
    assert result["session"]["source_session_id"] == sid
    assert execute(tok, result)[-1]["status"] == "ok"
    branch = wait_turns(tok, result["session"]["id"], 2)
    assert branch["turns"][0]["text"] == "edited"
    assert "discard this future" not in branch["turns"][-1]["text"]
    assert turns(tok, sid) == before
    assert result["run_id"] == branch["turns"][-1]["run_id"]


def test_duplicate_delivery_and_concurrent_claim_execute_once():
    tok = user(); _, sid = chat(tok)
    say(tok, {"chat_session_id": sid, "message": "first"}); view = wait_turns(tok, sid, 2)
    body = edit_body(view)
    with ThreadPoolExecutor(max_workers=2) as pool:
        prepared = list(pool.map(lambda _: prepare(tok, sid, body).json(), range(2)))
    assert all(x["success"] for x in prepared), prepared
    result = prepared[0]["data"]
    assert prepared[1]["data"]["session"]["id"] == result["session"]["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        events = list(pool.map(lambda _: execute(tok, result), range(2)))
    assert sum(e["type"] == "run_started" for ev in events for e in ev) == 1
    assert [e["error"]["code"] for ev in events for e in ev if e["type"] == "error"] == ["CHAT_EDIT_STARTED"]
    assert len(wait_turns(tok, result["session"]["id"], 2)["turns"]) == 2
    assert prepare(tok, sid, body).json()["data"]["state"] == "finished"
    assert err(prepare(tok, sid, {**body, "message": "different"})) == "CHAT_EDIT_CONFLICT"


def test_stale_targets_and_other_people_are_rejected_without_a_branch():
    tok = user(); wid, sid = chat(tok)
    say(tok, {"chat_session_id": sid, "message": "first"}); before = wait_turns(tok, sid, 2)
    body = edit_body(before)
    assert err(prepare(user(), sid, body)) == "CHAT_SESSION_NOT_FOUND"
    assert err(prepare(tok, sid, {**body, "turn_id": "unknown"})) == "CHAT_TURN_NOT_FOUND"
    assert err(prepare(tok, sid, {**body, "turn_id": before["turns"][1]["id"]})) == "CHAT_EDIT_INVALID"
    say(tok, {"chat_session_id": sid, "message": "changed"}); wait_turns(tok, sid, 4)
    assert err(prepare(tok, sid, body)) == "CHAT_EDIT_STALE"
    assert len(c.get(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]) == 1


def test_waiting_and_human_answers_are_not_editable_roots():
    tok = user(); _, sid = chat(tok, asking())
    evs = say(tok, {"chat_session_id": sid, "message": "first"}); before = wait_turns(tok, sid, 2)
    assert err(prepare(tok, sid, edit_body(before))) == "CHAT_EDIT_BUSY"
    rid = next(e["run_id"] for e in evs if e["type"] == "run_started")
    say(tok, {"chat_session_id": sid, "resume_run_id": rid, "response": "yes"}); done = wait_turns(tok, sid, 4)
    assert done["turns"][0]["editable"] and not done["turns"][2]["editable"]
    assert err(prepare(tok, sid, edit_body(done, 2))) == "CHAT_EDIT_INVALID"


@pytest.mark.parametrize("storage", ["db", "fs", "s3"])
def test_retained_files_are_independent_and_inherited_feedback_is_read_only(storage, monkeypatch, tmp_path):
    from app.api import deps
    monkeypatch.setenv("STUDIO_ATTACHMENT_STORAGE", storage)
    monkeypatch.setenv("STUDIO_ATTACHMENT_FS_PATH", str(tmp_path))
    if storage == "s3":
        env = {k: os.environ.get(f"STUDIO_TEST_S3_{k}", "") for k in ("ENDPOINT", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")}
        if not env["ENDPOINT"] or not env["BUCKET"]: pytest.skip("requires the CI MinIO fixture")
        env.update(REGION="us-east-1", PATH_STYLE="true", PREFIX="edits-" + uuid.uuid4().hex)
        for key, value in env.items(): monkeypatch.setenv(f"STUDIO_ATTACHMENT_S3_{key}", value)
    deps._attachment_stores.cache_clear()
    cleanup = []; tok = None
    try:
        tok = user(); wid, sid = chat(tok); allow(wid)
        cleanup.append(sid)
        url = f"/api/chat/sessions/{sid}/attachments"
        file = up(c, url, "notes.txt", b"keep independently", headers=H(tok)).json()["data"]
        say(tok, {"chat_session_id": sid, "message": "prefix", "attachment_ids": [file["id"]]}); wait_turns(tok, sid, 2)
        say(tok, {"chat_session_id": sid, "message": "change me"}); view = wait_turns(tok, sid, 4)
        result = prepare(tok, sid, edit_body(view, 2)).json()["data"]; branch = result["session"]; bid = branch["id"]
        cleanup.append(bid)
        assert [x["text"] for x in branch["turns"]] == [x["text"] for x in view["turns"][:2]]
        assert all(x["inherited"] and not x["editable"] for x in branch["turns"])
        copied = branch["turns"][0]["attachments"][0]["id"]; assert copied != file["id"]
        assert err(c.put(f"/api/chat/sessions/{bid}/turns/{branch['turns'][1]['id']}/rating", json={"value": "up"}, headers=H(tok))) == "CHAT_RATING_NOT_ALLOWED"
        assert execute(tok, result)[-1]["status"] == "ok"
        assert c.delete(f"/api/chat/sessions/{sid}", headers=H(tok)).json()["success"]
        assert c.get(f"/api/chat/sessions/{bid}/attachments/{copied}", headers=H(tok)).content == b"keep independently"
        assert len(turns(tok, bid)["turns"]) == 4
    finally:
        for owned in cleanup: c.delete(f"/api/chat/sessions/{owned}", headers=H(tok))
        deps._attachment_stores.cache_clear()


def test_late_source_change_rolls_back_staged_files_and_duplicate_tombstones_never_recreate(monkeypatch):
    tok = user(); wid, sid = chat(tok); allow(wid)
    file = up(c, f"/api/chat/sessions/{sid}/attachments", "notes.txt", b"owned", headers=H(tok)).json()["data"]
    say(tok, {"chat_session_id": sid, "message": "first", "attachment_ids": [file["id"]]}); view = wait_turns(tok, sid, 2)
    body = edit_body(view); svc = chat_session_service(); original = svc.sessions.publish_edit
    staged = []
    def change(source, branch, prefix, intent):
        staged.append(branch.id)
        svc.sessions.set_fields(source.id, title="concurrent change")
        return original(source, branch, prefix, intent)
    monkeypatch.setattr(svc.sessions, "publish_edit", change)
    from app.main import app
    monkeypatch.setitem(app.dependency_overrides, chat_session_service, lambda: svc)
    assert err(prepare(tok, sid, body)) == "CHAT_EDIT_STALE"
    assert svc.files.refs_of_sessions(staged) == []
    assert len(c.get(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]) == 1
    monkeypatch.setattr(svc.sessions, "publish_edit", original)
    result = prepare(tok, sid, body).json()["data"]; bid = result["session"]["id"]
    assert c.delete(f"/api/chat/sessions/{bid}", headers=H(tok)).json()["success"]
    assert err(prepare(tok, sid, body)) == "CHAT_EDIT_GONE"
    assert len(c.get(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]) == 1


def test_changed_file_policy_is_rechecked_before_publishing_an_edit():
    tok = user(); wid, sid = chat(tok); allow(wid)
    file = up(c, f"/api/chat/sessions/{sid}/attachments", "notes.txt", b"owned", headers=H(tok)).json()["data"]
    say(tok, {"chat_session_id": sid, "message": "first", "attachment_ids": [file["id"]]}); view = wait_turns(tok, sid, 2)
    allow(wid, kinds=["image"])
    assert err(prepare(tok, sid, edit_body(view))) == "CHAT_ATTACHMENT_TYPE"
    assert len(c.get(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]) == 1


def test_edit_restores_agent_at_the_prefix_after_removal_and_readdition(monkeypatch):
    from tests.test_chat_active_agent import desk_chat, model, active
    from tests.test_agent_handoff_engine import to
    from tests.test_agent_handoff_model import desk
    tok = user(); wid, sid = desk_chat(tok)
    model(monkeypatch, [("", [to("transfer_to_billing")]), ("Billing here", [])])
    say(tok, {"chat_session_id": sid, "message": "billing"}); wait_turns(tok, sid, 2)
    removed = desk([{"target": "tech"}])
    removed["nodes"] = [n for n in removed["nodes"] if n["id"] != "billing"]
    removed["edges"] = [e for e in removed["edges"] if "billing" not in (e["source"], e["target"])]
    assert c.post("/api/workflows", headers=H(tok), json={**removed, "id": wid}).json()["success"]
    model(monkeypatch, [("Entry again", [])])
    say(tok, {"chat_session_id": sid, "message": "reset"}); wait_turns(tok, sid, 4)
    assert active(sid) is None
    assert c.post("/api/workflows", headers=H(tok), json={**desk(), "id": wid}).json()["success"]
    model(monkeypatch, [("", [to("transfer_to_technical")]), ("Tech here", [])])
    say(tok, {"chat_session_id": sid, "message": "future tech"}); view = wait_turns(tok, sid, 6)
    assert active(sid) == "tech"
    result = prepare(tok, sid, edit_body(view, 4)).json()["data"]
    who = model(monkeypatch, [("Edited at the entry", [])])
    assert execute(tok, result)[-1]["status"] == "ok"
    assert who == ["triage"] and active(result["session"]["id"]) is None
    assert active(sid) == "tech"
    # Pruned run metadata cannot justify guessing a historical agent from the source's future state.
    from sqlalchemy import delete
    from app.api.deps import get_db
    from app.models import Run
    with get_db().session() as db:
        db.execute(delete(Run).where(Run.id == view["turns"][3]["run_id"])); db.commit()
    assert err(prepare(tok, sid, edit_body(view, 4))) == "CHAT_EDIT_CONTEXT_UNAVAILABLE"


def test_public_v1_branch_uses_the_same_identity_and_typed_stream():
    slug = publish(user())[1]; v, token, sid = start(slug); headers = {"X-Chat-Visitor": token}
    talk(v, slug, {"type": "message", "chat_session_id": sid, "text": "old"}, query=f"?visitor={token}")
    root = f"/api/public/v1/chat/{slug}/sessions"
    view = v.get(f"{root}/{sid}", headers=headers).json()["data"]
    body = edit_body(view)
    denied = v.post(f"{root}/{sid}/edits", headers={"X-Chat-Visitor": "new"}, json=body)
    assert err(denied) == "CHAT_SESSION_NOT_FOUND"
    result = v.post(f"{root}/{sid}/edits", headers=headers, json=body).json()["data"]
    frame = {"type": "message", "chat_session_id": result["session"]["id"], "text": result["message"], "edit_operation_id": result["operation_id"]}
    events = talk(v, slug, frame, query=f"?visitor={token}")
    assert events[-1]["status"] == "ok" and events[1]["run_id"] == result["run_id"]
    replay = talk(v, slug, frame, query=f"?visitor={token}")
    assert replay[-1]["error"]["code"] == "CHAT_EDIT_STARTED"
    assert v.get(f"{root}/{sid}", headers=headers).json()["data"] == view


def test_an_edit_does_not_bypass_the_published_chats_daily_quota():
    slug = publish(user(), daily_limit=1)[1]; v, token, sid = start(slug); headers = {"X-Chat-Visitor": token}
    original = talk(v, slug, {"type": "message", "chat_session_id": sid, "text": "original"}, query=f"?visitor={token}")
    assert original[-1]["status"] == "ok"
    root = f"/api/public/v1/chat/{slug}/sessions"
    view = v.get(f"{root}/{sid}", headers=headers).json()["data"]
    result = v.post(f"{root}/{sid}/edits", headers=headers, json=edit_body(view)).json()["data"]
    bid = result["session"]["id"]
    events = talk(v, slug, {"type": "message", "chat_session_id": bid, "text": result["message"], "edit_operation_id": result["operation_id"]}, query=f"?visitor={token}")
    assert events[-1]["error"]["code"] == "CHAT_DAILY_LIMIT"
    assert chat_session_service().runs.get(result["run_id"]) is None
    assert v.get(f"{root}/{bid}", headers=headers).json()["data"]["turns"] == []
    assert v.get(f"{root}/{sid}", headers=headers).json()["data"] == view


def test_app_user_cannot_edit_another_users_session_and_rotation_keeps_the_current_issuer():
    from tests.test_chat_user_tokens import setup, mint, headers, create, talk as app_talk
    from tests.test_public_chat_api import visitor
    owner, wid, slug, key = setup(["https://shop.example"]); v = visitor()
    first = mint(key, slug); other = mint(key, slug, sub="other-user")
    sid = create(v, slug, first, "https://shop.example")
    app_talk(v, slug, first, {"type": "message", "chat_session_id": sid, "text": "original"})
    root = f"/api/public/v1/chat/{slug}/sessions"
    view = v.get(f"{root}/{sid}", headers=headers(first, "https://shop.example")).json()["data"]; body = edit_body(view)
    assert err(v.post(f"{root}/{sid}/edits", headers=headers(other, "https://shop.example"), json=body)) == "CHAT_SESSION_NOT_FOUND"
    assert err(v.post(f"{root}/{sid}/edits", headers=headers(first, "https://blocked.example"), json=body)) == "CHAT_ORIGIN_FORBIDDEN"
    rotated = c.post(f"/api/workflows/{wid}/chat/app-keys", headers=H(owner), json={"label": "Rotated", "origins": ["https://shop.example"]}).json()["data"]
    current = mint(rotated, slug)
    result = v.post(f"{root}/{sid}/edits", headers=headers(current, "https://shop.example"), json=body).json()["data"]
    bid = result["session"]["id"]
    from app.api.deps import get_db
    from app.repositories.chat_app_keys import ChatAppKeyRepository
    current_key = ChatAppKeyRepository(get_db()).get(rotated["key_id"])
    assert chat_session_service().sessions.get(bid).app_key_id == current_key.id
    assert c.delete(f"/api/workflows/{wid}/chat/app-keys/{key['key_id']}", headers=H(owner)).json()["success"]
    assert err(v.post(f"{root}/{sid}/edits", headers=headers(first, "https://shop.example"), json=body)) == "CHAT_APP_KEY_REVOKED"
    events = app_talk(v, slug, current, {"type": "message", "chat_session_id": bid, "text": result["message"], "edit_operation_id": result["operation_id"]})
    assert events[-1]["status"] == "ok"
    other_current = mint(rotated, slug, sub="other-user")
    assert err(v.get(f"{root}/{bid}", headers=headers(other_current, "https://shop.example"))) == "CHAT_SESSION_NOT_FOUND"
