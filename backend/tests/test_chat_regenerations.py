"""Latest-answer regeneration reuses revision admission, never previous Human answers."""
import pytest
from tests.test_chat_edits import c, H, user, chat, say, wait_turns, turns, asking, prepare, execute, err, revision_body


def test_regeneration_keeps_prefix_and_reasks_human_without_replaying_the_old_response():
    tok = user(); _, sid = chat(tok, asking())
    for message in ("prefix", "latest root"):
        evs = say(tok, {"chat_session_id": sid, "message": message})
        rid = next(x["run_id"] for x in evs if x["type"] == "run_started")
        say(tok, {"chat_session_id": sid, "resume_run_id": rid, "response": "old approval"})
    before = wait_turns(tok, sid, 8)
    response = prepare(tok, sid, revision_body(before, "regenerate")).json()
    assert response["success"], response
    result = response["data"]
    bid = result["session"]["id"]
    assert result["session"]["source_action"] == "regenerate"
    assert result["session"]["source_turn_id"] == before["turns"][-1]["id"]
    assert result["message"] == "latest root" and len(result["session"]["turns"]) == 4
    assert all(x["inherited"] for x in result["session"]["turns"])
    assert execute(tok, result)[-1]["status"] == "waiting"
    branch = wait_turns(tok, bid, 6)
    assert branch["turns"][-2]["text"] == "latest root"
    assert branch["turns"][-1]["status"] == "waiting"
    assert result["run_id"] != before["turns"][-1]["run_id"]
    assert not any(x["regeneratable"] for x in branch["turns"])
    say(tok, {"chat_session_id": bid, "resume_run_id": result["run_id"], "response": "fresh approval"})
    finished = wait_turns(tok, bid, 8)
    assert finished["turns"][-2]["text"] == "fresh approval"
    assert finished["turns"][-1]["regeneratable"]
    assert turns(tok, sid) == before


def test_regeneration_requires_the_latest_owned_answer_and_rejects_extra_execution_input():
    tok = user(); _, sid = chat(tok)
    for message in ("earlier", "latest"):
        say(tok, {"chat_session_id": sid, "message": message})
    before = wait_turns(tok, sid, 4); body = revision_body(before, "regenerate")
    assert err(prepare(tok, sid, {**body, "turn_id": before["turns"][1]["id"]})) == "CHAT_REGENERATE_INVALID"
    assert err(prepare(tok, sid, {**body, "turn_id": before["turns"][2]["id"]})) == "CHAT_REGENERATE_INVALID"
    assert err(prepare(user(), sid, body)) == "CHAT_SESSION_NOT_FOUND"
    assert err(prepare(tok, sid, {**body, "expected_last_turn_id": "stale"})) == "CHAT_EDIT_STALE"
    url = f"/api/chat/sessions/{sid}/regenerations"
    assert err(c.post(url, headers=H(tok), json={**body, "input": {"arbitrary": True}})) == "VALIDATION_ERROR"
    result = prepare(tok, sid, body).json()["data"]
    # A prepared branch's inherited last answer cannot be regenerated as a new root.
    inherited = result["session"]
    assert err(prepare(tok, inherited["id"], revision_body(inherited, "regenerate"))) == "CHAT_REGENERATE_INVALID"
    assert err(prepare(tok, sid, {**body, "message": "different action"})) == "CHAT_EDIT_CONFLICT"
    assert err(prepare(tok, sid, {**body, "turn_id": "regenerate", "message": body["turn_id"]})) == "CHAT_EDIT_CONFLICT"
    assert turns(tok, sid) == before


def test_regeneration_creates_a_fresh_reviewer_request():
    tok = user(); _, sid = chat(tok, asking("reviewer"))
    say(tok, {"chat_session_id": sid, "message": "needs review"})
    initial = wait_turns(tok, sid, 2)
    rid = initial["turns"][-1]["run_id"]
    assert err(prepare(tok, sid, revision_body(initial, "regenerate"))) == "CHAT_EDIT_BUSY"
    response = c.post(f"/api/approvals/inbox/{rid}", headers=H(tok), json={"response": "approved before"}).json()
    assert response["success"], response
    from tests.test_workflow_tool_runs import drain
    drain()  # inbox responses are worker jobs; this module's client has no lifespan worker
    before = wait_turns(tok, sid, 3)
    assert before["turns"][-1]["status"] == "ok"
    result = prepare(tok, sid, revision_body(before, "regenerate")).json()["data"]
    assert execute(tok, result)[-1]["status"] == "waiting"
    branch = wait_turns(tok, result["session"]["id"], 2)
    assert branch["turns"][-1]["answered_by"] == "reviewer"
    inbox = c.get("/api/approvals/inbox", headers=H(tok)).json()["data"]
    assert any(x["run_id"] == result["run_id"] for x in inbox)
    assert result["run_id"] != rid and turns(tok, sid) == before


@pytest.mark.parametrize("status", ["error", "cancelled", "expired", "timeout"])
def test_terminal_failures_can_be_regenerated_without_changing_the_source(status):
    from app.api.deps import chat_session_service
    from sqlalchemy import update
    from app.models import ChatTurn, Run
    tok = user(); _, sid = chat(tok)
    say(tok, {"chat_session_id": sid, "message": "try again"}); before = wait_turns(tok, sid, 2)
    rid = before["turns"][-1]["run_id"]
    with chat_session_service().sessions.db.session() as db:
        db.execute(update(ChatTurn).where(ChatTurn.id == before["turns"][-1]["id"]).values(status=status))
        db.execute(update(Run).where(Run.id == rid).values(status=status)); db.commit()
    before = turns(tok, sid)
    assert before["turns"][-1]["regeneratable"]
    result = prepare(tok, sid, revision_body(before, "regenerate")).json()["data"]
    assert execute(tok, result)[-1]["status"] == "ok"
    assert turns(tok, sid) == before
