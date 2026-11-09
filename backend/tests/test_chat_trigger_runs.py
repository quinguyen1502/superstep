"""chat messages start runs: Slack events, Telegram messages, checks, replies."""
import asyncio, hashlib, hmac, json, time, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from app.main import app
from app.api.deps import approval_service, chat_run_service, run_service
from app.models import ChannelIdentity, Run
from app.repositories import UserRepository, WorkflowRepository
from app.services.approval_channels import ADAPTERS
from tests.test_hitl import APPROVAL

SIGNING = "0123456789abcdef0123456789abcdef"
TG = {"bot_token": "123456:AAbbCCddEEffGGhhIIjjKKll", "webhook_secret": "tg-secret-0123456789abcdef"}
ECHO = {"name": "Echo", "state": [{"name": "message", "type": "string"}, {"name": "notes", "type": "list"}],
        "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
                  {"id": "e", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
        "edges": [{"id": "1", "source": "s", "target": "e"}]}
PICKY = {"name": "Picky", "state": [{"name": "message", "type": "string"}],  # a Condition without a default: other values fail
         "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
                   {"id": "r", "type": "condition", "position": {"x": 0, "y": 0}, "data": {"label": "Route", "field": "message"}},
                   {"id": "e", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
         "edges": [{"id": "1", "source": "s", "target": "r"}, {"id": "2", "source": "r", "target": "e", "label": "yes"}]}


class FakeApi:
    def __init__(self): self.calls: list[tuple[str, dict]] = []
    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}"); path = req.url.path; self.calls.append((path, body))
        if path.endswith("auth.test"):
            team = req.headers["Authorization"].split("-")[2]
            return httpx.Response(200, json={"ok": True, "team": f"Team {team}", "team_id": team},
                                  headers={"x-oauth-scopes": "chat:write,im:write,app_mentions:read,im:history"})
        if path.endswith("getMe"): return httpx.Response(200, json={"ok": True, "result": {"id": 123456, "is_bot": True, "username": "studio_bot"}})
        if path.endswith("sendMessage") and str(body.get("chat_id")) == "404": return httpx.Response(200, json={"ok": False, "description": "chat not found"})
        if path.endswith("sendMessage"): return httpx.Response(200, json={"ok": True, "result": {"message_id": 1, "chat": {"id": body["chat_id"]}}})
        return httpx.Response(200, json={"ok": True, "ts": "1.1", "result": True})
    def sent(self, name): return [b for p, b in self.calls if p.endswith(name)]


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # the in-process worker runs chat_message and run jobs

@pytest.fixture(autouse=True)
def api(monkeypatch):
    fake = FakeApi()
    for a in ADAPTERS.values(): monkeypatch.setattr(a, "transport", httpx.MockTransport(fake), raising=False)
    monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_IP", "0"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", "0")
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.example.com")
    import app.services.approval_service as mod
    monkeypatch.setattr(mod, "BACKGROUND", False)
    return fake

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    d = c.post("/api/auth/register", json={"email": f"cr{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}

def until(fn, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if v := fn(): return v
        time.sleep(0.05)
    raise AssertionError("timed out")

def link(u, kind, external, team="", verified=True):
    """A linked chat account (what Settings → My accounts does after the code is typed)."""
    with approval_service().repo.db.session() as s:
        s.merge(ChannelIdentity(user_id=u["id"], kind=kind, team_id=team, external_id=external, created=time.time(),
                                verified_at=time.time() if verified else None)); s.commit()

def setup(c, owner, wf=ECHO, command="echo", place="C0HR", reply="message", **kw):
    team = uuid.uuid4().hex[:8].upper()
    wid = c.post("/api/workflows", json={**wf, "name": f"{wf['name']} {team[:4]}"}, headers=H(owner["token"])).json()["data"]["id"]
    ch = c.post("/api/approvals/channels", json={"kind": "slack", "bot_token": f"xoxb-1111-{team}-abcdefgh", "signing_secret": SIGNING}, headers=H(owner["token"])).json()["data"]
    t = c.post(f"/api/workflows/{wid}/chat-triggers", json={"channel_id": ch["id"], "place": place, "command": command, "input_field": "message",
                                                            "reply_field": reply, **kw}, headers=H(owner["token"])).json()["data"]
    return team, wid, ch, t

def event(team, text, user="U1", channel="C0HR", dm=False, eid=None, **extra):
    e = {"type": "message", "channel_type": "im"} if dm else {"type": "app_mention"}
    return {"type": "event_callback", "team_id": team, "event_id": eid or f"Ev{uuid.uuid4().hex[:8]}", "authorizations": [{"user_id": "UBOT"}],
            "event": {**e, "user": user, "text": text, "channel": "D0DM" if dm else channel, "ts": "1700.1", **extra}}

def slack_post(c, payload, secret=SIGNING, ts=None, headers=None):
    body = json.dumps(payload).encode(); ts = str(int(ts or time.time()))
    sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return c.post("/api/channels/events/slack", content=body, headers={"Content-Type": "application/json", "X-Slack-Request-Timestamp": ts,
                                                                       "X-Slack-Signature": sig, **(headers or {})})

def replies(api, thread="1700.1"): return [b["text"] for b in api.sent("chat.postMessage") if b.get("thread_ts") == thread]
def private(api): return [b for b in api.sent("chat.postEphemeral")]
def runs_of(wid):
    with approval_service().repo.db.session() as s: return [r for r in s.query(Run).filter(Run.workflow_id == wid).all()]


# ---------- Slack ----------
def test_mention_starts_one_run_and_replies_in_the_thread(c, api):
    o = user(c); team, wid, ch, t = setup(c, o); link(o, "slack", "U1", team)
    ev = event(team, "<@UBOT>  ECHO: hello there")
    assert slack_post(c, ev).json()["data"] == {"outcome": "queued"}
    assert slack_post(c, ev, headers={"X-Slack-Retry-Num": "1"}).json()["data"] == {"outcome": "duplicate"}  # Slack retried
    done = until(lambda: [x for x in replies(api) if "finished" in x])
    started = [x for x in replies(api) if x.startswith("▶️")]
    assert len(started) == 1 and len(done) == 1 and replies(api).index(started[0]) < replies(api).index(done[0])
    assert done[0].startswith(f"✅ {ECHO['name']} {team[:4]} finished: hello there") and "https://studio.example.com/workflows/" in done[0]
    [r] = runs_of(wid)
    assert (r.source, r.owner, json.loads(r.input), r.status) == ("chat", o["id"], {"message": "hello there"}, "ok")
    hist = c.get(f"/api/workflows/{wid}/runs", headers=H(o["token"])).json()["data"]
    assert hist[0]["chat"] == {"kind": "slack", "sender": "U1", "trigger": "echo"}
    got = c.get(f"/api/workflows/{wid}/chat-triggers", headers=H(o["token"])).json()["data"][0]
    assert got["last_run_id"] == r.id and got["last_message"]
    assert any(e["action"] == "chat_started" and e["external_id"] == "U1" for e in c.get("/api/approvals/audit", headers=H(o["token"])).json()["data"])


def test_direct_messages_command_variants_and_ignored_events(c, api):
    o = user(c); team, wid, ch, t = setup(c, o, place="dm", command="ask"); link(o, "slack", "U1", team)
    for text, want in [("ask hi", "hi"), ("Ask:  two words", "two words"), ("<@UBOT> ask", "")]:
        assert slack_post(c, event(team, text, dm=True)).json()["data"]["outcome"] == "queued"
        until(lambda: [b for b in api.sent("chat.postMessage") if b["channel"] == "D0DM" and "finished" in b["text"] and (want or "(no value)") in b["text"]])
        assert "thread_ts" not in api.sent("chat.postMessage")[-1]  # a direct message has no thread
    for ev in [event(team, "ask hi", dm=True, bot_id="B1"), event(team, "ask hi", dm=True, subtype="message_changed"),
               event(team, "asking hi", dm=True), event(team, "ask hi"),  # another word; a mention in a channel with no trigger there
               {"type": "event_callback", "team_id": team, "event": {"type": "reaction_added", "user": "U1"}}]:
        assert slack_post(c, ev).json()["data"] == {"outcome": "ignored"}
    assert len(runs_of(wid)) == 3


def test_url_check_and_signatures(c, api):
    o = user(c); team, wid, ch, t = setup(c, o); link(o, "slack", "U1", team)
    r = c.post("/api/channels/events/slack", json={"type": "url_verification", "challenge": "abc123"})
    assert r.status_code == 200 and r.text == "abc123"
    assert slack_post(c, event(team, "echo hi"), secret="f" * 32).status_code == 401
    assert slack_post(c, event(team, "echo hi"), ts=time.time() - 3600).status_code == 401
    assert slack_post(c, event("TNOBODY", "echo hi")).status_code == 401
    assert c.post("/api/channels/events/telegram", json={}).json()["error"]["code"] == "CHANNEL_KIND_UNSUPPORTED"
    assert runs_of(wid) == []


def test_refusals_are_private_in_the_senders_language_and_audited(c, api, monkeypatch):
    o, other, stranger = user(c), user(c), user(c)
    team, wid, ch, t = setup(c, o); link(o, "slack", "U1", team); link(other, "slack", "U2", team); link(stranger, "slack", "U3", team, verified=False)
    UserRepository(approval_service().repo.db).set_prefs(other["id"], lang="vi")
    def refused(text, user, want):
        n = len(private(api)); assert slack_post(c, event(team, text, user=user)).json()["data"]["outcome"] == "queued"
        p = until(lambda: private(api)[n:])[0]
        assert (p["user"], p["channel"], p["thread_ts"]) == (user, "C0HR", "1700.1") and want in p["text"], p["text"]
    refused("echo hi", "U9", "Link your Slack account")
    refused("echo hi", "U3", "Verify your Slack account")
    refused("echo hi", "U2", "Bạn không có quyền chạy workflow này")  # not shared with them; their language
    monkeypatch.setenv("STUDIO_INPUT_MAX_BYTES", "50")
    refused("echo " + "x" * 80, "U1", "too long")
    monkeypatch.delenv("STUDIO_INPUT_MAX_BYTES")
    monkeypatch.setenv("STUDIO_CHAT_TRIGGER_RATE_LIMIT", "1")
    slack_post(c, event(team, "echo one")); until(lambda: len(runs_of(wid)) == 1)
    refused("echo two", "U1", "Too many runs")
    monkeypatch.delenv("STUDIO_CHAT_TRIGGER_RATE_LIMIT")
    c.patch(f"/api/workflows/{wid}/chat-triggers/{t['id']}", json={"enabled": False}, headers=H(o["token"]))
    refused("echo hi", "U1", "This chat trigger is off")
    WorkflowRepository(approval_service().repo.db).delete(wid)  # gone without the service's cleanup
    with approval_service().repo.db.session() as s:
        from app.models import WorkflowChatTrigger
        s.execute(update(WorkflowChatTrigger).where(WorkflowChatTrigger.id == t["id"]).values(enabled=True)); s.commit()
    refused("echo hi", "U1", "no longer exists")
    codes = [e["code"] for e in c.get("/api/approvals/audit", headers=H(o["token"])).json()["data"] if e["action"] == "chat_refused"]
    assert sorted(codes) == sorted(["CHAT_IDENTITY_UNKNOWN", "CHAT_IDENTITY_UNVERIFIED", "CHAT_FORBIDDEN", "RUN_INPUT_TOO_LARGE", "RATE_LIMITED",
                                    "CHAT_TRIGGER_OFF", "WORKFLOW_NOT_FOUND"])


def test_creator_without_the_share_right_stops_the_trigger(c, api, monkeypatch):
    o = user(c); team, wid, ch, t = setup(c, o); link(o, "slack", "U1", team)
    from app.services import access as acc
    real = acc.AccessService.may
    monkeypatch.setattr(acc.AccessService, "may", lambda self, w, u, a="view": False if a == "share" else real(self, w, u, a))
    slack_post(c, event(team, "echo hi"))
    assert "This chat trigger is off" in until(lambda: private(api))[0]["text"]
    monkeypatch.setattr(acc.AccessService, "may", real)
    got = c.get(f"/api/workflows/{wid}/chat-triggers", headers=H(o["token"])).json()["data"][0]
    assert (got["enabled"], got["note"]) == (False, "access") and runs_of(wid) == []


def test_waiting_then_finished_and_errors(c, api):
    o = user(c); team, wid, ch, t = setup(c, o, wf=APPROVAL, command="refund", reply="decision"); link(o, "slack", "U1", team)
    slack_post(c, event(team, "refund order A100"))
    until(lambda: [x for x in replies(api) if "waiting for approval at Manager approval" in x])
    [r] = runs_of(wid)
    with c.websocket_connect(f"/ws/run?token={o['token']}") as w:
        w.send_json({"resume_run_id": r.id, "response": "approved"})
        while w.receive_json()["type"] != "run_summary": pass
    until(lambda: [x for x in replies(api) if "finished: approved" in x])
    for _ in range(2): asyncio.run(run_service().settled(r.id, "chat"))  # same settled state: answered once
    assert len([x for x in replies(api) if "finished" in x]) == 1 and len([x for x in replies(api) if "waiting" in x]) == 1
    team2, wid2, _, _ = setup(c, o, wf=PICKY, command="pick"); link(o, "slack", "U1", team2)
    slack_post(c, event(team2, "pick no"))
    assert "matches no label" in until(lambda: [x for x in replies(api) if "failed" in x])[0]


def test_long_values_are_shortened_and_list_inputs_wrapped(c, api, monkeypatch):
    from app.services import chat_run_service as mod
    monkeypatch.setattr(mod, "VALUE_MAX", 20)
    o = user(c); team, wid, ch, t = setup(c, o); link(o, "slack", "U1", team)
    slack_post(c, event(team, "echo " + "y" * 40))
    done = until(lambda: [x for x in replies(api) if "finished" in x])[0]
    assert "y" * 19 + "…" in done and "y" * 20 not in done
    c.patch(f"/api/workflows/{wid}/chat-triggers/{t['id']}", json={"input_field": "notes", "reply_field": "notes"}, headers=H(o["token"]))
    slack_post(c, event(team, "echo note one"))
    until(lambda: [r for r in runs_of(wid) if json.loads(r.input) == {"notes": ["note one"]} and r.status == "ok"])
    assert until(lambda: [x for x in replies(api) if 'finished: ["note one"]' in x])


# ---------- Telegram ----------
def test_telegram_messages_and_buttons_share_the_webhook(c, api):
    o = user(c)
    wid = c.post("/api/workflows", json={**ECHO, "name": "Echo TG"}, headers=H(o["token"])).json()["data"]["id"]
    ch = c.post("/api/approvals/channels", json={"kind": "telegram", **TG}, headers=H(o["token"])).json()["data"]
    for place in ("dm", "-100777"):
        c.post(f"/api/workflows/{wid}/chat-triggers", json={"channel_id": ch["id"], "place": place, "command": "echo", "input_field": "message",
                                                            "reply_field": "message"}, headers=H(o["token"]))
    link(o, "telegram", "4242")
    def post(update, secret=TG["webhook_secret"]):
        return c.post(f"/api/approvals/callback/telegram/{ch['id']}", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": secret})
    def msg(text, chat=4242, kind="private", uid=None, sender=4242):
        return {"update_id": uid or int(time.time() * 1000) % 10**9, "message": {"message_id": 7, "from": {"id": sender}, "chat": {"id": chat, "type": kind}, "text": text}}
    m = msg("/echo hi")
    assert post(m).json()["data"] == {"outcome": "queued"} and post(m).json()["data"] == {"outcome": "duplicate"}
    done = until(lambda: [b for b in api.sent("sendMessage") if "finished: hi" in b["text"]])[0]
    assert done["chat_id"] == 4242 and done["reply_parameters"]["message_id"] == 7
    post(msg("/echo@studio_bot from the group", chat=-100777, kind="supergroup"))
    until(lambda: [b for b in api.sent("sendMessage") if "finished: from the group" in b["text"] and b["chat_id"] == -100777])
    # a refusal in a group goes to the sender privately; when the bot cannot write to them, to the group
    post(msg("/echo hi", chat=-100777, kind="group", sender=555))
    assert until(lambda: [b for b in api.sent("sendMessage") if b["chat_id"] == "555"])[0]["text"].startswith("Link your Telegram account")
    post(msg("/echo hi", chat=-100777, kind="group", sender=404))
    assert until(lambda: [b for b in api.sent("sendMessage") if b["chat_id"] == -100777 and "Link your" in b["text"]])
    assert post({"update_id": 1, "edited_message": msg("/echo x")["message"]}).json()["data"] == {"outcome": "ignored"}
    assert post(msg("/echo hi"), secret="wrong").status_code == 401
    # button presses still reach approvals on the same URL
    cb = {"update_id": 2, "callback_query": {"id": "q1", "from": {"id": 4242}, "data": "a.nope.bad"}}
    assert post(cb).json()["data"]["outcome"] == "refused"
    assert len([r for r in runs_of(wid) if r.status == "ok"]) == 2


def test_settled_survives_a_cancelled_handler(c, monkeypatch):
    """the studio socket closes on run_summary, which cancels the handler while settled() waits for a
    thread. With every executor thread busy, a plain to_thread job was dropped and the chat reply never went out."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    svc, answered, busy = run_service(), [], threading.Event()
    monkeypatch.setattr(svc, "chat", lambda: type("Chat", (), {"on_settled": lambda self, rid: answered.append(rid)})())
    monkeypatch.setattr(svc, "deliveries", None)

    async def main():
        asyncio.get_running_loop().set_default_executor(pool := ThreadPoolExecutor(1))
        asyncio.get_running_loop().run_in_executor(None, busy.wait)  # the only thread is taken
        task = asyncio.create_task(svc.settled("r-cancel", "chat")); await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        busy.set(); await asyncio.to_thread(lambda: None); pool.shutdown(wait=True)
    asyncio.run(main())
    assert answered == ["r-cancel"]
