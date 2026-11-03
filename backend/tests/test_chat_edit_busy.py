"""A later finished message must not hide an earlier pending execution from revision admission."""
from app.api.deps import chat_session_service
from tests.test_chat_sessions import chat, user, say, wait_turns
from tests.test_chat_edits import edit_body, prepare
from tests.test_public_chat_api import err


def test_an_earlier_pending_message_blocks_edit_even_after_a_later_answer():
    tok = user(); _, sid = chat(tok)
    say(tok, {"chat_session_id": sid, "message": "first"}); wait_turns(tok, sid, 2)
    web = chat_session_service(); session = web.sessions.get(sid); trigger = web.triggers.get(session.trigger_id)
    # Pause a normal message between its persisted admission and starting its run.
    web.write(session, trigger, "earlier pending", "pending-run-id", session.owner)
    say(tok, {"chat_session_id": sid, "message": "later finished"}); view = wait_turns(tok, sid, 5)
    assert view["turns"][-1]["status"] == "ok"
    assert err(prepare(tok, sid, edit_body(view))) == "CHAT_EDIT_BUSY"
