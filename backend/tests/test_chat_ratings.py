"""Thumbs on a chat answer (TASK-0162, TASK-0165, REQ-0075, DEC-0070): one row per turn, the session owner only,
finished answers only, builder totals and the thumbs-down filter, retention, and one LangSmith feedback."""
import asyncio, time, types, uuid
import pytest
from sqlalchemy import delete, update
from app.api.deps import chat_session_service, get_db, langsmith_service, run_worker
from app.models import ChatTurn, Run
from app.services.langsmith import LangSmithService, run_id_of
from app.services import langsmith as LS
from tests.test_chat_sessions import ECHO, H, asking, say as studio_say, turns as studio_turns, user, wait_turns
from tests.test_public_chat_api import c, err, publish
from tests.test_public_chat_runs import say, start, turns

TRACE = "0123456789abcdef"


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    for k in ("READ", "VISITOR", "IP"): monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{k}", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)


def put(v, slug, tok, sid, tid, body):
    return v.put(f"/api/public/chat/{slug}/sessions/{sid}/turns/{tid}/rating", json=body, headers={"X-Chat-Visitor": tok})


def stamp(rid, root):
    with get_db().session() as s:
        s.execute(update(Run).where(Run.id == rid).values(trace_root=root)); s.commit()


class Feedback:
    def __init__(self): self.created, self.updated, self.fail = [], [], False

    def create_feedback(self, rid, key, score=None, comment=None):
        if self.fail: raise ConnectionError("down")
        self.created.append((rid, key, score, comment)); return types.SimpleNamespace(id=f"fb{len(self.created)}")

    def update_feedback(self, fid, score=None, comment=None):
        if self.fail: raise ConnectionError("down")
        self.updated.append((fid, score, comment))


def test_a_visitor_rates_one_answer():
    tok = user(); _wid, slug = publish(tok)
    v, vt, sid = start(slug)
    say(v, slug, vt, {"chat_session_id": sid, "message": "hello"})
    d = turns(v, slug, vt, sid, 2); mine, ans = d["turns"]
    assert ans["rating"] is None and ans["run_exists"] is True and "run_exists" not in mine and "feedback_id" not in d
    r = put(v, slug, vt, sid, ans["id"], {"value": "up"})
    assert r.status_code == 200 and r.json()["data"] == {"value": "up", "comment": "", "updated": r.json()["data"]["updated"]}
    assert "feedback_id" not in r.text
    bad = put(v, slug, vt, sid, mine["id"], {"value": "up"})
    assert (err(bad), bad.status_code) == ("CHAT_RATING_NOT_ALLOWED", 409)
    for body, field in (({"value": "up", "comment": "nice"}, "comment"), ({"value": "down", "comment": "x" * 1001}, "comment"), ({"value": "meh"}, "value")):
        e = put(v, slug, vt, sid, ans["id"], body); assert (err(e), e.status_code, e.json()["error"]["details"]["field"]) == ("CHAT_RATING_INVALID", 400, field), body
    assert put(v, slug, vt, sid, ans["id"], {"value": "down", "comment": "x" * 1000}).json()["data"]["comment"] == "x" * 1000
    assert put(v, slug, vt, sid, ans["id"], {"value": "down"}).json()["data"]["comment"] == "x" * 1000  # omitted comment keeps the stored one
    assert put(v, slug, vt, sid, ans["id"], {"value": "down", "comment": "  wrong  "}).json()["data"]["comment"] == "wrong"
    assert put(v, slug, vt, sid, ans["id"], {"value": "up"}).json()["data"]["comment"] == ""  # up clears the comment
    put(v, slug, vt, sid, ans["id"], {"value": "down", "comment": "The order status was wrong"})
    again = turns(v, slug, vt, sid, 2)["turns"][1]
    assert again["rating"]["value"] == "down" and again["rating"]["comment"] == "The order status was wrong" and "feedback_id" not in again["rating"]
    assert len(chat_session_service().sessions.ratings_of(sid)) == 1
    other, ot, _osid = start(slug)
    assert err(put(other, slug, ot, sid, ans["id"], {"value": "up"})) == "CHAT_SESSION_NOT_FOUND"
    assert err(other.get(f"/api/public/chat/{slug}/sessions/{sid}", headers={"X-Chat-Visitor": ot})) == "CHAT_SESSION_NOT_FOUND"
    assert err(put(v, slug, vt, sid, "no-such-turn", {"value": "up"})) == "CHAT_TURN_NOT_FOUND"
    second = v.post(f"/api/public/chat/{slug}/sessions", headers={"X-Chat-Visitor": vt}).json()["data"]["id"]
    assert err(put(v, slug, vt, second, ans["id"], {"value": "up"})) == "CHAT_TURN_NOT_FOUND"  # the turn is not in this session
    assert err(c.put(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", json={"value": "up"}, headers=H(tok))) == "CHAT_SESSION_NOT_FOUND"
    assert v.delete(f"/api/public/chat/{slug}/sessions/{sid}/turns/{ans['id']}/rating", headers={"X-Chat-Visitor": vt}).json()["data"] == {"ok": True}
    assert turns(v, slug, vt, sid, 2)["turns"][1]["rating"] is None
    assert chat_session_service().sessions.rating(ans["id"]) is None


def test_a_waiting_question_cannot_be_rated_and_the_final_answer_can():
    tok = user(); wid = c.post("/api/workflows", json={**asking(), "name": "Ask"}, headers=H(tok)).json()["data"]["id"]
    slug = f"ask-{wid[:6]}"
    c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "access": "anonymous", "slug": slug, "retention_days": 1}, headers=H(tok))
    v, vt, sid = start(slug)
    say(v, slug, vt, {"chat_session_id": sid, "message": "the refund"})
    q = turns(v, slug, vt, sid, 2)["turns"][1]
    assert q["status"] == "waiting"
    refused = put(v, slug, vt, sid, q["id"], {"value": "down"})
    assert (err(refused), refused.status_code) == ("CHAT_RATING_NOT_ALLOWED", 409)
    assert say(v, slug, vt, {"chat_session_id": sid, "response": "yes"})[-1]["status"] == "ok"
    final = turns(v, slug, vt, sid, 3)["turns"][-1]
    assert final["status"] == "ok" and final["id"] != q["id"]
    assert put(v, slug, vt, sid, final["id"], {"value": "down", "comment": "no"}).json()["data"]["value"] == "down"
    assert err(put(v, slug, vt, sid, q["id"], {"value": "up"})) == "CHAT_RATING_NOT_ALLOWED"  # the waiting turn stays waiting
    # an error answer is rateable; a cancelled one is not
    svc = chat_session_service(); now = time.time()
    failed = svc.sessions.add_turn(ChatTurn(id=uuid.uuid4().hex[:12], session_id=sid, role="assistant", text="boom", status="error", created=now))
    stopped = svc.sessions.add_turn(ChatTurn(id=uuid.uuid4().hex[:12], session_id=sid, role="assistant", text="", status="cancelled", created=now + 1))
    assert put(v, slug, vt, sid, failed.id, {"value": "down"}).json()["data"]["value"] == "down"
    assert err(put(v, slug, vt, sid, stopped.id, {"value": "up"})) == "CHAT_RATING_NOT_ALLOWED"
    c.put(f"/api/workflows/{wid}/chat", json={"access": "studio"}, headers=H(tok))
    blocked = put(v, slug, vt, sid, final["id"], {"value": "up"})
    assert (err(blocked), blocked.status_code) == ("CHAT_NOT_PUBLISHED", 404)
    seen = c.get(f"/api/workflows/{wid}/chat/visitors/{sid}", headers=H(tok)).json()["data"]
    rated = next(t for t in seen["turns"] if t["id"] == final["id"])
    assert rated["rating"]["comment"] == "no"  # the old rating stays for the builder
    svc.sessions.set_fields(sid, updated=time.time() - 2 * 86400)
    assert svc.cleanup() >= 1
    assert err(c.get(f"/api/workflows/{wid}/chat/visitors/{sid}", headers=H(tok))) == "CHAT_SESSION_NOT_FOUND"
    assert svc.sessions.rating(final["id"]) is None and svc.sessions.rating(failed.id) is None


def test_builders_see_the_mark_the_filter_and_the_totals():
    tok = user(); wid, slug = publish(tok)
    a, at, asid = start(slug); b, bt, bsid = start(slug)
    say(a, slug, at, {"chat_session_id": asid, "message": "order"}); turns(a, slug, at, asid, 2)
    say(b, slug, bt, {"chat_session_id": bsid, "message": "thanks"}); turns(b, slug, bt, bsid, 2)
    aid = turns(a, slug, at, asid, 2)["turns"][1]["id"]; bid = turns(b, slug, bt, bsid, 2)["turns"][1]["id"]
    put(a, slug, at, asid, aid, {"value": "down", "comment": "wrong"})
    put(b, slug, bt, bsid, bid, {"value": "up"})
    rows = c.get(f"/api/workflows/{wid}/chat/visitors", headers=H(tok)).json()["data"]
    by = {r["id"]: r for r in rows}
    assert by[asid]["thumbs_down"] is True and by[bsid]["thumbs_down"] is False and "visitor" not in rows[0]
    only = c.get(f"/api/workflows/{wid}/chat/visitors?thumbs_down=1", headers=H(tok)).json()["data"]
    assert [r["id"] for r in only] == [asid] and only[0]["thumbs_down"] is True
    totals = c.get(f"/api/workflows/{wid}/chat/ratings", headers=H(tok)).json()["data"]
    assert totals == {"d7": {"up": 1, "down": 1}, "d30": {"up": 1, "down": 1}}
    assert err(c.get(f"/api/workflows/{wid}/chat/ratings", headers=H(user()))) == "WORKFLOW_NOT_FOUND"
    # deleting the run keeps the rating and tells the builder the run is gone
    rid = turns(a, slug, at, asid, 2)["turns"][1]["run_id"]
    with get_db().session() as s:
        s.execute(delete(Run).where(Run.id == rid)); s.commit()
    gone = c.get(f"/api/workflows/{wid}/chat/visitors/{asid}", headers=H(tok)).json()["data"]["turns"][1]
    assert gone["rating"]["value"] == "down" and gone["run_exists"] is False


def test_a_builder_rates_their_own_studio_chat():
    tok = user(); wid = c.post("/api/workflows", json=ECHO, headers=H(tok)).json()["data"]["id"]
    c.put(f"/api/workflows/{wid}/chat", json={"enabled": True}, headers=H(tok))
    sid = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    assert studio_say(tok, {"chat_session_id": sid, "message": "hello"})[-1]["status"] == "ok"
    ans = wait_turns(tok, sid, 2)["turns"][1]
    r = c.put(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", json={"value": "down", "comment": "thin"}, headers=H(tok))
    assert r.json()["data"]["comment"] == "thin" and "feedback_id" not in r.text
    assert studio_turns(tok, sid)["turns"][1]["rating"]["value"] == "down"
    assert c.get(f"/api/workflows/{wid}/chat/ratings", headers=H(tok)).json()["data"]["d7"] == {"up": 0, "down": 1}
    assert c.delete(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", headers=H(tok)).json()["data"] == {"ok": True}
    assert studio_turns(tok, sid)["turns"][1]["rating"] is None
    assert err(c.put(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", json={"value": "up"}, headers=H(user()))) == "CHAT_SESSION_NOT_FOUND"


def test_langsmith_gets_one_feedback_object(monkeypatch):
    """The worker is running, so its on_rating is held. The test calls the real method itself."""
    original = LangSmithService.on_rating
    monkeypatch.setattr(LangSmithService, "on_rating", lambda self, turn_id: None)
    fake = Feedback(); monkeypatch.setattr(LS, "client_factory", lambda: fake)
    tok = user(); wid = c.post("/api/workflows", json=ECHO, headers=H(tok)).json()["data"]["id"]
    c.put(f"/api/workflows/{wid}/chat", json={"enabled": True}, headers=H(tok))
    sid = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    studio_say(tok, {"chat_session_id": sid, "message": "hello"})
    ans = wait_turns(tok, sid, 2)["turns"][1]
    c.put(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", json={"value": "up"}, headers=H(tok))
    svc = langsmith_service()
    original(svc, ans["id"])  # no key, and no trace yet
    assert fake.created == []
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key"); monkeypatch.setenv("LANGSMITH_TRACING", "true")
    original(svc, ans["id"])  # key and tracing, but the run has no trace root
    assert fake.created == []
    stamp(ans["run_id"], TRACE)
    original(svc, ans["id"])
    assert fake.created == [(run_id_of(TRACE), "user_rating", 1.0, None)]
    assert chat_session_service().sessions.rating(ans["id"]).feedback_id == "fb1"
    c.put(f"/api/chat/sessions/{sid}/turns/{ans['id']}/rating", json={"value": "down", "comment": "thin"}, headers=H(tok))
    original(svc, ans["id"])
    assert len(fake.created) == 1 and fake.updated == [("fb1", 0.0, "thin")]
    assert chat_session_service().sessions.rating(ans["id"]).feedback_id == "fb1"  # the same object, updated
    fake.fail = True
    original(svc, ans["id"])  # LangSmith down: the rating stays, nothing is raised
    assert chat_session_service().sessions.rating(ans["id"]).value == "down"
    monkeypatch.delenv("LANGSMITH_API_KEY")
    calls = []
    monkeypatch.setattr(LS, "client_factory", lambda: calls.append(1) or fake)
    original(svc, ans["id"])
    assert calls == []
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key"); monkeypatch.delenv("LANGSMITH_TRACING")
    original(svc, ans["id"])
    assert calls == []  # tracing off does not follow the studio evals switch, and does not send


def test_the_worker_sends_a_rating_without_reading_a_run_id(monkeypatch):
    seen = []
    monkeypatch.setattr(LangSmithService, "on_rating", lambda self, turn_id: seen.append(turn_id))
    assert asyncio.run(run_worker().run_job({"kind": "chat_rating", "turn_id": "t1"})) is None
    assert seen == ["t1"]
