"""Chatting on the published page (TASK-0141, REQ-0074, DEC-0067): the public socket runs a message as the workflow's
owner, streams only what the steps mode allows, takes the visitor's Human answers, and keeps the limits; builders read
visitor chats."""
import json, time
import pytest
from app.api.deps import run_service
from tests.test_chat_sessions import ECHO, H, asking, user
from tests.test_public_chat_api import c, err, publish, visitor


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    for k in ("READ", "VISITOR", "IP"): monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{k}", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def start(slug, client=None):
    """A widget-style visitor: its token and a new session."""
    v = client or visitor()
    d = v.post(f"/api/public/chat/{slug}/sessions", headers={"X-Chat-Visitor": "new"}).json()["data"]
    return v, d["visitor_token"], d["id"]


def say(v, slug, tok, msg):
    with v.websocket_connect(f"/ws/public/chat/{slug}?visitor={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            e = w.receive_json(); evs.append(e)
            if e["type"] == "run_summary" or (e["type"] == "error" and not e.get("node")): return evs


def code(evs): return evs[-1]["error"]["code"]


def turns(v, slug, tok, sid, n):
    t0 = time.time()
    while time.time() - t0 < 10:
        d = v.get(f"/api/public/chat/{slug}/sessions/{sid}", headers={"X-Chat-Visitor": tok}).json()["data"]
        if len(d["turns"]) >= n: return d
        time.sleep(0.05)
    raise AssertionError(d)


def test_a_visitor_chats_with_memory_and_sees_only_the_labels():
    tok = user(); wid, slug = publish(tok, max_turns=3)
    v, vt, sid = start(slug)
    evs = say(v, slug, vt, {"chat_session_id": sid, "message": "my name is Lan"})
    assert evs[-1]["status"] == "ok"
    for e in evs:
        assert not {"state", "input", "metrics", "trace_url", "usage", "superstep"} & set(e), e
        if e["type"] in ("node_started", "node_finished"): assert set(e) <= {"type", "node", "label", "node_type", "iteration", "ts"}, e
    assert any(e["type"] == "node_token" and e["field"] == "reply" for e in evs)
    assert not any(e.get("node_type") in ("start", "end") for e in evs)
    turns(v, slug, vt, sid, 2)
    say(v, slug, vt, {"chat_session_id": sid, "message": "what is my name?"})
    d = turns(v, slug, vt, sid, 4)
    assert [(x["role"], x["status"]) for x in d["turns"]] == [("user", "ok"), ("assistant", "ok")] * 2
    r = run_service().runs.get(d["turns"][3]["run_id"]); owner = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    assert (r.owner, r.source) == (owner, "chat") and "my name is Lan" in json.dumps(json.loads(r.input))  # the history went in


def test_the_steps_mode_decides_what_streams():
    tok = user(); wid, slug = publish(tok, steps="none")
    v, vt, sid = start(slug)
    assert {e["type"] for e in say(v, slug, vt, {"chat_session_id": sid, "message": "hi"})} <= {"run_started", "node_token", "run_summary"}
    c.put(f"/api/workflows/{wid}/chat", json={"steps": "full"}, headers=H(tok))
    turns(v, slug, vt, sid, 2)
    done = [e for e in say(v, slug, vt, {"chat_session_id": sid, "message": "again"}) if e["type"] == "node_finished"]
    assert done and "input" in done[0] and "delta" in done[0]


def test_a_visitor_answers_a_human_node_but_not_a_reviewers():
    tok = user(); wid = c.post("/api/workflows", json={**asking(), "name": "Ask"}, headers=H(tok)).json()["data"]["id"]
    c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "access": "anonymous", "slug": f"ask-{wid[:6]}"}, headers=H(tok))
    slug = f"ask-{wid[:6]}"
    v, vt, sid = start(slug)
    evs = say(v, slug, vt, {"chat_session_id": sid, "message": "the refund"})
    q = next(e for e in evs if e["type"] == "run_waiting"); assert q["prompt"] == "Sure about the refund?" and "state" not in q
    turns(v, slug, vt, sid, 2)
    assert code(say(v, slug, vt, {"chat_session_id": sid, "message": "more"})) == "CHAT_RUN_WAITING"
    assert say(v, slug, vt, {"chat_session_id": sid, "response": "yes"})[-1]["status"] == "ok"
    d = turns(v, slug, vt, sid, 4)["turns"]  # the visitor's answer is their turn (TASK-0209), then the final answer
    assert [(x["role"], x["status"]) for x in d] == [("user", "ok"), ("assistant", "waiting"), ("user", "ok"), ("assistant", "ok")] and d[2]["text"] == "yes"
    assert code(say(v, slug, vt, {"chat_session_id": sid, "response": "again"})) == "RUN_NOT_WAITING"  # answered already
    # a reviewer's question cannot be answered from the page
    tok2 = user(); wid2 = c.post("/api/workflows", json={**asking("reviewer"), "name": "Ask2"}, headers=H(tok2)).json()["data"]["id"]
    slug2 = f"rev-{wid2[:6]}"; c.put(f"/api/workflows/{wid2}/chat", json={"enabled": True, "access": "anonymous", "slug": slug2}, headers=H(tok2))
    v2, vt2, sid2 = start(slug2)
    say(v2, slug2, vt2, {"chat_session_id": sid2, "message": "x"}); turns(v2, slug2, vt2, sid2, 2)
    assert code(say(v2, slug2, vt2, {"chat_session_id": sid2, "response": "yes"})) == "CHAT_ANSWER_BY_REVIEWER"


def test_a_visitor_answers_the_question_on_the_page_when_another_is_open():
    """Two approvals in one wave: the page names its question, and then shows the next one."""
    tok = user(); wid = c.post("/api/workflows", json={**asking(), "name": "Two"}, headers=H(tok)).json()["data"]["id"]
    slug = f"two-{wid[:6]}"; c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "access": "anonymous", "slug": slug}, headers=H(tok))
    v, vt, sid = start(slug)
    evs = say(v, slug, vt, {"chat_session_id": sid, "message": "the refund"})
    assert next(e for e in evs if e["type"] == "run_waiting")["node"] == "ask"
    d = turns(v, slug, vt, sid, 2); rid = d["turns"][-1]["run_id"]
    svc = run_service(); r = svc.runs.get(rid); cp = json.loads(r.checkpoint)
    cp["waits"] = [{"node": "ask", "kind": "approval", "prompt": "Sure about the refund?", "label": "Ask"},
                   {"node": "other", "kind": "approval", "prompt": "And the other?", "label": "Other"}]
    r.checkpoint = json.dumps(cp); svc.runs.add(r)
    assert code(say(v, slug, vt, {"chat_session_id": sid, "response": "no", "node": "other"})) == "RUN_NOT_WAITING"
    assert [w["node"] for w in json.loads(svc.runs.get(rid).checkpoint)["waits"]] == ["ask", "other"]
    evs = say(v, slug, vt, {"chat_session_id": sid, "response": "yes"})  # the question the page is showing
    assert evs[-1]["status"] == "waiting"
    nxt = next(e for e in evs if e["type"] == "run_waiting")
    assert nxt["node"] == "other" and nxt["prompt"] == "And the other?"
    saved = json.loads(svc.runs.get(rid).checkpoint)
    assert saved["answers"] == {"ask": "yes"} and [w["node"] for w in saved["waits"]] == ["other"]
    page = turns(v, slug, vt, sid, 3)["turns"][-1]
    assert page["status"] == "waiting" and page["node"] == "other" and page["text"] == "And the other?"
    assert code(say(v, slug, vt, {"chat_session_id": sid, "response": "yes", "node": "ask"})) == "RUN_NOT_WAITING"


def test_limits_stop_a_message_before_it_runs(monkeypatch):
    tok = user(); wid, slug = publish(tok, daily_limit=3)
    monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_VISITOR", "2"); monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_WINDOW", "3600")
    v, vt, sid = start(slug)
    for i in range(2):
        assert say(v, slug, vt, {"chat_session_id": sid, "message": f"m{i}"})[-1]["status"] == "ok"; turns(v, slug, vt, sid, 2 * (i + 1))
    before = len(run_service().runs.list_for_workflow(wid))
    e = say(v, slug, vt, {"chat_session_id": sid, "message": "m2"})[-1]["error"]
    assert (e["code"], e["details"]["retry_after"] > 0) == ("RATE_LIMITED", True)
    v2, vt2, sid2 = start(slug)  # another visitor: the daily cap (3) is reached on their second message
    assert say(v2, slug, vt2, {"chat_session_id": sid2, "message": "a"})[-1]["status"] == "ok"; turns(v2, slug, vt2, sid2, 2)
    assert code(say(v2, slug, vt2, {"chat_session_id": sid2, "message": "b"})) == "CHAT_DAILY_LIMIT"
    assert len(turns(v2, slug, vt2, sid2, 2)["turns"]) == 2  # nothing was recorded
    assert len(run_service().runs.list_for_workflow(wid)) == before + 1


def test_the_socket_takes_only_this_chats_messages():
    tok = user(); wid, slug = publish(tok)
    v, vt, sid = start(slug)
    assert code(say(v, slug, vt, {"chat_session_id": sid, "message": "x", "workflow_id": wid})) == "RUN_REQUEST_INVALID"
    assert code(say(v, slug, vt, {"chat_session_id": "nope", "message": "x"})) == "CHAT_SESSION_NOT_FOUND"
    other, ot, _ = start(slug)
    assert code(say(other, slug, ot, {"chat_session_id": sid, "message": "x"})) == "CHAT_SESSION_NOT_FOUND"
    c.put(f"/api/workflows/{wid}/chat", json={"access": "studio"}, headers=H(tok))
    assert code(say(v, slug, vt, {"chat_session_id": sid, "message": "x"})) == "CHAT_NOT_PUBLISHED"
    with pytest.raises(Exception):
        with v.websocket_connect(f"/ws/public/chat/{slug}", headers={"origin": "https://evil.example"}) as w: w.receive_json()


def test_builders_read_visitor_chats():
    tok = user(); wid, slug = publish(tok)
    v, vt, sid = start(slug)
    say(v, slug, vt, {"chat_session_id": sid, "message": "hello"}); turns(v, slug, vt, sid, 2)
    studio = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    rows = c.get(f"/api/workflows/{wid}/chat/visitors", headers=H(tok)).json()["data"]
    assert [r["id"] for r in rows] == [sid] and rows[0]["title"] == "hello" and "visitor" not in rows[0]
    d = c.get(f"/api/workflows/{wid}/chat/visitors/{sid}", headers=H(tok)).json()["data"]
    assert d["steps_mode"] == "full" and d["turns"][1]["steps"]
    assert err(c.get(f"/api/workflows/{wid}/chat/visitors/{studio}", headers=H(tok))) == "CHAT_SESSION_NOT_FOUND"
    assert err(c.get(f"/api/workflows/{wid}/chat/visitors", headers=H(user()))) == "WORKFLOW_NOT_FOUND"
