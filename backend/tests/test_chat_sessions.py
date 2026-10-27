"""TASK-0084 (REQ-0048, DEC-0052..0054): the web chat. Settings, sessions, multi-turn memory over the run socket,
reply-once answers, Human nodes answered by the visitor or a reviewer, step visibility, retention."""
import json, time, uuid
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import chat_session_service
from app.services.chat_session_service import steps_of, answered_by

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def user():
    return c.post("/api/auth/register", json={"email": f"cs{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]

def node(i, t, **d): return {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i.title(), **d}}
STATE = [{"name": "message", "type": "string"}, {"name": "messages", "type": "list"}, {"name": "reply", "type": "string"}, {"name": "ok", "type": "string"}]
ECHO = {"name": "Echo chat", "state": STATE,
        "nodes": [node("s", "start"), node("bot", "llm", prompt="History:\n{{state.messages}}", output_field="reply"), node("e", "end")],
        "edges": [{"id": "1", "source": "s", "target": "bot"}, {"id": "2", "source": "bot", "target": "e"}]}
def asking(by=None):
    ask = node("ask", "human", prompt="Sure about {{state.message}}?", output_field="ok", **({"answered_by": by} if by else {}))
    return {"name": "Ask chat", "state": STATE,
            "nodes": [node("s", "start"), ask, node("bot", "llm", prompt="Answer {{state.ok}}", output_field="reply"), node("e", "end")],
            "edges": [{"id": "1", "source": "s", "target": "ask"}, {"id": "2", "source": "ask", "target": "bot"}, {"id": "3", "source": "bot", "target": "e"}]}

def chat(tok, wf=ECHO, **settings):
    wid = c.post("/api/workflows", json=wf, headers=H(tok)).json()["data"]["id"]
    r = c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, **settings}, headers=H(tok)).json()
    assert r["success"], r
    sid = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    return wid, sid

def say(tok, msg):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            e = w.receive_json(); evs.append(e)
            if e["type"] in ("run_summary",) or (e["type"] == "error" and "run_id" not in e and not e.get("node")): return evs

def turns(tok, sid, view="builder"):
    return c.get(f"/api/chat/sessions/{sid}?view={view}", headers=H(tok)).json()["data"]

def wait_turns(tok, sid, n, view="builder"):
    t0 = time.time()
    while time.time() - t0 < 10:
        d = turns(tok, sid, view)
        if len(d["turns"]) >= n: return d
        time.sleep(0.05)
    raise AssertionError(f"timed out: {turns(tok, sid, view)}")


def test_settings_defaults_and_validation():
    tok = user(); wid = c.post("/api/workflows", json=ECHO, headers=H(tok)).json()["data"]["id"]
    d = c.get(f"/api/workflows/{wid}/chat", headers=H(tok)).json()["data"]
    assert d == {"enabled": False, "slug": wid.lower(), "input_field": "message", "reply_field": "reply", "access": "studio",
                 "messages_field": "messages", "max_turns": 10, "steps": "labels", "retention_days": 30,
                 "title": "", "intro": "", "suggestions": [], "daily_limit": 500, "embed_origins": []}
    assert c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["error"]["code"] == "CHAT_NOT_ENABLED"
    for body, field in [({"steps": "all"}, "steps"), ({"max_turns": 0}, "max_turns"), ({"retention_days": 99999}, "retention_days"),
                        ({"messages_field": "reply"}, "messages_field"), ({"input_field": "nope"}, "input_field")]:
        e = c.put(f"/api/workflows/{wid}/chat", json=body, headers=H(tok)).json()["error"]
        assert (e["code"], e["details"]["field"]) == ("CHAT_SETTINGS_INVALID", field), e
    d = c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "steps": "none", "max_turns": 3}, headers=H(tok)).json()["data"]
    assert (d["enabled"], d["steps"], d["max_turns"]) == (True, "none", 3)
    assert c.get(f"/api/workflows/{wid}/chat-triggers", headers=H(tok)).json()["data"] == []  # the web chat is not a Slack/Telegram trigger
    other = user()
    assert c.get(f"/api/workflows/{wid}/chat", headers=H(other)).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


def test_multi_turn_memory_streams_and_answers_once():
    tok = user(); wid, sid = chat(tok, max_turns=1)
    evs = say(tok, {"chat_session_id": sid, "message": "hello one"})
    assert evs[-1]["status"] == "ok"
    toks = [e for e in evs if e["type"] == "node_token"]
    assert all(e["field"] == "reply" for e in toks)  # reply tokens are tagged with their output field
    d = wait_turns(tok, sid, 2)
    assert [(t["role"], t["status"]) for t in d["turns"]] == [("user", "ok"), ("assistant", "ok")] and d["title"] == "hello one"
    say(tok, {"chat_session_id": sid, "message": "and two"})
    d = wait_turns(tok, sid, 4)
    assert "hello one" in d["turns"][3]["text"] and "and two" in d["turns"][3]["text"]  # the history reached the run
    say(tok, {"chat_session_id": sid, "message": "three"})
    d = wait_turns(tok, sid, 6)
    run = [x for x in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]][0]
    assert run["source"] == "chat"
    svc = chat_session_service()
    hist = svc.history(sid, 1)  # max_turns=1: the last exchange only
    assert [m["role"] for m in hist] == ["user", "assistant"] and hist[0]["content"] == "three"
    import asyncio
    from app.api.deps import run_service
    for _ in range(2): asyncio.run(run_service().settled(d["turns"][-1]["run_id"], "chat"))  # settled again: no second answer
    assert len(turns(tok, sid)["turns"]) == 6
    assert [s["id"] for s in c.get(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]] == [sid]
    e = say(tok, {"chat_session_id": sid, "message": "  "})[-1]
    assert e["error"]["code"] == "CHAT_MESSAGE_EMPTY"


def test_visitor_answers_the_human_node_in_the_chat():
    tok = user(); wid, sid = chat(tok, asking())
    evs = say(tok, {"chat_session_id": sid, "message": "refund A1"})
    assert evs[-1]["status"] == "waiting"
    d = wait_turns(tok, sid, 2); q = d["turns"][1]
    assert (q["status"], q["node"], q["answered_by"], q["text"]) == ("waiting", "ask", "visitor", "Sure about refund A1?")
    assert say(tok, {"chat_session_id": sid, "message": "next"})[-1]["error"]["code"] == "CHAT_RUN_WAITING"
    evs = say(tok, {"chat_session_id": sid, "resume_run_id": q["run_id"], "response": "yes"})
    assert evs[-1]["status"] == "ok"
    d = wait_turns(tok, sid, 3)
    assert d["turns"][2]["status"] == "ok" and "Answer yes" in d["turns"][2]["text"]


def test_reviewer_answers_in_the_inbox_not_the_chat():
    tok = user(); wid, sid = chat(tok, asking("reviewer"))
    say(tok, {"chat_session_id": sid, "message": "refund B2"})
    q = wait_turns(tok, sid, 2)["turns"][1]
    assert (q["status"], q["answered_by"]) == ("waiting", "reviewer")
    e = say(tok, {"chat_session_id": sid, "resume_run_id": q["run_id"], "response": "yes"})[-1]
    assert e["error"]["code"] == "CHAT_ANSWER_BY_REVIEWER"
    inbox = c.get("/api/approvals/inbox", headers=H(tok)).json()["data"]
    assert any(x["run_id"] == q["run_id"] for x in inbox)  # the reviewer answers it there
    v = c.post("/api/validate", json=asking("boss"), headers=H(tok)).json()
    assert "answered by must be visitor or reviewer" in json.dumps(v)


def test_step_visibility_modes():
    events = [{"type": "node_started", "node": "bot", "label": "Bot", "node_type": "llm"},
              {"type": "node_finished", "node": "bot", "label": "Bot", "node_type": "llm", "duration_ms": 3.0, "input": {"a": 1}, "delta": {"reply": "x"}}]
    assert steps_of(events, "none") == []
    assert steps_of(events, "labels") == [{"node": "bot", "label": "Bot", "type": "llm", "status": "ok"}]
    assert steps_of(events, "full")[0]["delta"] == {"reply": "x"} and steps_of(events, "full")[0]["duration_ms"] == 3.0
    waiting = [{"type": "node_started", "node": "ask", "label": "Ask", "node_type": "human"}, {"type": "run_waiting", "node": "ask", "prompt": "?"}]
    assert steps_of(waiting, "labels") == [{"node": "ask", "label": "Ask", "type": "human", "status": "waiting"}]
    tok = user(); wid, sid = chat(tok, steps="none")
    say(tok, {"chat_session_id": sid, "message": "hi"})
    wait_turns(tok, sid, 2)
    builder, visitor = turns(tok, sid), turns(tok, sid, "visitor")
    assert builder["steps_mode"] == "full" and builder["turns"][1]["steps"][0]["node"] == "bot" and "delta" in builder["turns"][1]["steps"][0]
    assert visitor["steps_mode"] == "none" and visitor["turns"][1]["steps"] == []
    c.put(f"/api/workflows/{wid}/chat", json={"steps": "labels"}, headers=H(tok))
    v = turns(tok, sid, "visitor")["turns"][1]["steps"][0]
    assert v == {"node": "bot", "label": "Bot", "type": "llm", "status": "ok"}
    assert answered_by(None) == "visitor" and answered_by({"answered_by": "reviewer"}) == "reviewer"


def test_retention_cleanup_and_access():
    tok = user(); wid, sid = chat(tok, retention_days=1)
    svc = chat_session_service()
    assert svc.cleanup() >= 0 and turns(tok, sid)["id"] == sid  # fresh: kept
    svc.sessions.set_fields(sid, updated=time.time() - 2 * 86400)
    assert svc.cleanup() >= 1
    assert c.get(f"/api/chat/sessions/{sid}", headers=H(tok)).json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    _, sid2 = chat(tok)
    other = user()
    assert c.get(f"/api/chat/sessions/{sid2}", headers=H(other)).json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert c.delete(f"/api/chat/sessions/{sid2}", headers=H(tok)).json()["data"] == {"ok": True}
