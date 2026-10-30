"""A chat stays with the agent a hand-off left it with (TASK-0181, REQ-0078, DEC-0073 decision 4)."""
from app.api.deps import get_db
from app.engine import agents
from app.repositories import ChatSessionRepository
from tests.test_agent_handoff_engine import to
from tests.test_agent_handoff_model import desk
from tests.test_chat_attachment_runs import run_input
from tests.test_chat_sessions import H, c, say, turns, user


def model(monkeypatch, replies):
    """Each model call answers with the next reply; `who` records which agent was called (Triage is offered hand-offs)."""
    who, it = [], iter(replies)
    def fake(messages, tools, model, *_, **__):
        who.append("triage" if any(t["name"].startswith("transfer_to_") for t in tools or []) else "other"); return next(it)
    monkeypatch.setattr(agents, "call_agent", fake)
    return who


def desk_chat(tok):
    wid = c.post("/api/workflows", json=desk(), headers=H(tok)).json()["data"]["id"]
    assert c.put(f"/api/workflows/{wid}/chat", json={"enabled": True}, headers=H(tok)).json()["success"]
    return wid, c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]


def active(sid): return ChatSessionRepository(get_db()).get(sid).active_agent


def answers(tok, sid): return [x["text"] for x in turns(tok, sid)["turns"] if x["role"] == "assistant"]


def test_the_second_message_goes_to_the_agent_that_answered(monkeypatch):
    tok = user(); wid, sid = desk_chat(tok)
    who = model(monkeypatch, [("", [to("transfer_to_billing", "refund")]), ("Refund on its way.", []), ("It is processed.", [])])
    say(tok, {"chat_session_id": sid, "message": "I was charged twice"})
    assert active(sid) == "billing" and who == ["triage", "other"]
    evs = say(tok, {"chat_session_id": sid, "message": "When will it arrive?"})
    assert run_input(evs)[agents.START_INPUT] == "billing" and who == ["triage", "other", "other"]
    assert answers(tok, sid) == ["Refund on its way.", "It is processed."]
    assert not any(e.get("node") == "triage" for e in evs if e.get("type") == "node_started")
    # a new session starts at the entry
    sid2 = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    model(monkeypatch, [("Hello, how can I help?", [])])
    assert agents.START_INPUT not in run_input(say(tok, {"chat_session_id": sid2, "message": "hi"})) and active(sid2) is None


def test_a_removed_target_falls_back_to_the_entry(monkeypatch):
    tok = user(); wid, sid = desk_chat(tok)
    model(monkeypatch, [("", [to("transfer_to_billing")]), ("Billing here.", [])])
    say(tok, {"chat_session_id": sid, "message": "charged"})
    assert active(sid) == "billing"
    wf = desk([{"target": "tech"}])
    wf["nodes"] = [n for n in wf["nodes"] if n["id"] != "billing"]; wf["edges"] = [e for e in wf["edges"] if "billing" not in (e["source"], e["target"])]
    r = c.post("/api/workflows", json={**wf, "id": wid}, headers=H(tok)).json(); assert r["success"], r
    who = model(monkeypatch, [("Triage again.", [])])
    evs = say(tok, {"chat_session_id": sid, "message": "hello?"})
    assert who == ["triage"] and agents.START_INPUT not in run_input(evs) and active(sid) is None


def test_the_start_router_only_takes_hand_off_targets(monkeypatch):
    from app.engine.runtime import run_stream
    from tests.test_agent_node import final
    for start, first in (("billing", "other"), ("triage", "triage"), ("nope", "triage"), (None, "triage")):
        who = model(monkeypatch, [("Answer.", [])])
        out = final(list(run_stream(desk(), {"message": "x", **({agents.START_INPUT: start} if start else {})})))
        assert who == [first] and out["answer"] == "Answer." and not any(k.startswith("__") or k.startswith(agents.PREFIX) for k in out), start
