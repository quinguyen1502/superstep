"""approval of waiting runs through Slack / Telegram, with mocked platform APIs and signed callbacks."""
import hashlib, hmac, json, re, time, uuid
from urllib.parse import urlencode
import httpx, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service
from app.services.approval_channels import ADAPTERS
from tests.test_hitl import APPROVAL
from app.engine.locale import text as vi_text  # expected Vietnamese comes from the server catalog (app/locales/vi.json)

SIGNING = "8f742231b10e8888abcd99yyyzzz85a5".replace("y", "1").replace("z", "2")
SLACK = {"bot_token": "xoxb-1111-2222-abcdefgh", "signing_secret": SIGNING}
TG = {"bot_token": "123456:AAbbCCddEEffGGhhIIjjKKll", "webhook_secret": "tg-secret-0123456789abcdef"}


class FakeApi:
    """Records every call to the Slack/Telegram APIs and answers like them."""
    def __init__(self): self.calls: list[tuple[str, dict]] = []; self.auth: list[str] = []
    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}"); path = req.url.path; self.calls.append((str(req.url), body)); self.auth.append(req.headers.get("Authorization", ""))
        if path.endswith("auth.test"):  # bot tokens here look like xoxb-1111-<TEAM>-...
            team = req.headers["Authorization"].split("-")[2]; return httpx.Response(200, json={"ok": True, "team": f"Team {team}", "team_id": team})
        if path.endswith("getMe"): return httpx.Response(200, json={"ok": True, "result": {"id": 123456, "is_bot": True, "username": "studio_bot"}})
        if path.endswith("chat.postMessage"): return httpx.Response(200, json={"ok": True, "channel": body["channel"], "ts": f"{time.time():.6f}"})
        if path.endswith("sendMessage"): return httpx.Response(200, json={"ok": True, "result": {"message_id": len(self.calls), "chat": {"id": int(body["chat_id"])}}})
        if "fail" in json.dumps(body): return httpx.Response(200, json={"ok": False, "error": "channel_not_found"})
        return httpx.Response(200, json={"ok": True, "result": True})
    def named(self, name): return [b for u, b in self.calls if u.split("?")[0].endswith(name)]
    def requests(self, name="chat.postMessage"):
        """Approval requests only (messages with buttons), not identity-code DMs."""
        return [b for b in self.named(name) if "blocks" in b or "reply_markup" in b]


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client

@pytest.fixture(autouse=True)
def api(monkeypatch):
    fake = FakeApi()
    import app.services.approval_service as mod
    monkeypatch.setattr(mod, "BACKGROUND", False)  # send/edit inline: each test sees only its own platform calls
    monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_IP", "0"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", "0")  # see test_callbacks_are_rate_limited
    for a in ADAPTERS.values(): monkeypatch.setattr(a, "transport", httpx.MockTransport(fake), raising=False)
    from sqlalchemy import delete
    from app.models import ApprovalChannel
    with approval_service().repo.db.session() as s: s.execute(delete(ApprovalChannel).where(ApprovalChannel.scope == "org")); s.commit()  # org channels are global
    return fake

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    d = c.post("/api/auth/register", json={"email": f"a{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}

def until(fn, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = fn()
        if v: return v
        time.sleep(0.05)
    raise AssertionError("timed out")

def workflow(c, owner, approval):
    wf = json.loads(json.dumps(APPROVAL)); wf["name"] = f"Refund {uuid.uuid4().hex[:4]}"; wf["nodes"][1]["data"]["approval"] = approval
    return c.post("/api/workflows", json=wf, headers=H(owner["token"])).json()["data"]["id"]

def start_waiting(c, owner, wid):
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"workflow_id": wid, "input": {"message": "order A100"}}); evs = []
        while (evs := evs + [w.receive_json()])[-1]["type"] != "run_summary": pass
    assert evs[-1]["status"] == "waiting"; return evs[0]["run_id"]

def slack_post(c, cid, payload, secret=SIGNING, ts=None):
    """cid None = the shared Slack URL (routed by payload team.id)."""
    body = urlencode({"payload": json.dumps(payload)}).encode(); ts = str(int(ts or time.time()))
    sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return c.post("/api/approvals/callback/slack" + (f"/{cid}" if cid else ""), content=body, headers={"Content-Type": "application/x-www-form-urlencoded",
                                                                              "X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig})

def press(token, uid, action="approve", team="2222"):
    return {"type": "block_actions", "user": {"id": uid}, "team": {"id": team}, "response_url": "https://hooks.slack.com/actions/T1/1/x",
            "actions": [{"action_id": action, "value": token}]}

def connect(c, u, kind, scope="user", **extra):
    body = {"kind": kind, "scope": scope, **(SLACK if kind == "slack" else TG), **extra}
    r = c.post("/api/approvals/channels", json=body, headers=H(u["token"])); assert r.status_code == 200, r.json(); return r.json()["data"]

def admin(c, monkeypatch):
    email = f"adm{uuid.uuid4().hex[:6]}@example.com"; monkeypatch.setenv("STUDIO_ADMIN_EMAILS", f"other@example.com, {email.upper()}")
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}

def code_for(api, external_id):
    """The last verification code the bot DMed to this chat account."""
    msgs = [b.get("text", "") for _, b in api.calls if str(b.get("channel") or b.get("chat_id") or "") == external_id and "blocks" not in b and "reply_markup" not in b]
    return re.search(r"\b(\d{6})\b", msgs[-1]).group(1)

def slot(data, kind, team=None):
    """The identity slot of a platform (and Slack workspace) in GET/PUT /identities."""
    return next(x for x in data["slots"] if x["kind"] == kind and (team is None or x["team_id"] == team))

def ident(c, u, kind, external_id, team=None):
    return c.put("/api/approvals/identities", json={"kind": kind, "external_id": external_id, **({"team_id": team} if team else {})}, headers=H(u["token"]))

def link(c, api, u, kind, external_id, own_channel=True, team=None):
    """Link + verify a chat account the way a user does: (own channel to receive the DM) -> link -> code -> verify."""
    if own_channel: connect(c, u, kind)
    t = {"team_id": team} if team else {}
    assert ident(c, u, kind, external_id, team).status_code == 200
    assert c.post(f"/api/approvals/identities/{kind}/send-code", json=t, headers=H(u["token"])).status_code == 200
    r = c.post(f"/api/approvals/identities/{kind}/verify", json={"code": code_for(api, external_id), **t}, headers=H(u["token"]))
    assert slot(r.json()["data"], kind, team)["verified"] is True, r.json()

def run_row(c, owner, wid, rid): return next(r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(owner["token"])).json()["data"] if r["id"] == rid)


def test_channel_settings_are_validated_encrypted_and_masked(c):
    o = user(c)
    r = c.post("/api/approvals/channels", json={"kind": "slack", "bot_token": "nope"}, headers=H(o["token"]))
    assert r.status_code == 400 and r.json()["error"] == {"code": "CHANNEL_CONFIG_INVALID", "message": "Channel setting bot_token is missing or invalid", "details": {"field": "bot_token"}}
    assert c.post("/api/approvals/channels", json={"kind": "signal"}, headers=H(o["token"])).json()["error"]["code"] == "CHANNEL_KIND_UNSUPPORTED"
    ch = connect(c, o, "slack")
    assert ch["hint"] == "••••efgh" and ch["scope"] == "user" and ch["editable"] and ch["callback_path"] == f"/api/approvals/callback/slack/{ch['id']}" and "bot_token" not in json.dumps(ch)
    assert connect(c, o, "slack")["id"] == ch["id"]  # saving again replaces the secrets, same callback URL
    tg = c.post("/api/approvals/channels", json={"kind": "telegram", "bot_token": TG["bot_token"]}, headers=H(o["token"])).json()["data"]
    assert tg["kind"] == "telegram"  # webhook secret generated when left empty
    from app.repositories import ApprovalRepository
    from app.api.deps import get_db
    row = ApprovalRepository(get_db()).channel(ch["id"]); assert SLACK["bot_token"] not in row.secrets  # Fernet at rest
    listed = c.get("/api/approvals/channels", headers=H(o["token"])).json()["data"]
    assert [k["kind"] for k in listed["kinds"]] == ["slack", "telegram", "whatsapp", "email", "teams", "webhook"] and listed["is_admin"] is False
    assert {x["id"] for x in listed["channels"] if x["scope"] == "user"} == {ch["id"], tg["id"]}
    assert c.put(f"/api/approvals/channels/{ch['id']}", json={"name": "Ops"}, headers=H(o["token"])).json()["data"]["name"] == "Ops"
    other = user(c)
    assert c.delete(f"/api/approvals/channels/{tg['id']}", headers=H(other["token"])).json()["error"]["code"] == "CHANNEL_NOT_FOUND"  # not theirs
    assert c.delete(f"/api/approvals/channels/{tg['id']}", headers=H(o["token"])).json()["data"] == {"ok": True}
    assert c.delete(f"/api/approvals/channels/{tg['id']}", headers=H(o["token"])).json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    assert c.post(f"/api/approvals/channels/{ch['id']}/register-webhook", headers=H(o["token"])).json()["error"]["code"] == "CHANNEL_PUBLIC_URL_REQUIRED"


def test_org_channels_are_admin_managed_and_usable_by_everyone(c, api, monkeypatch):
    adm, u = admin(c, monkeypatch), user(c)
    r = c.post("/api/approvals/channels", json={"kind": "slack", "scope": "org", **SLACK}, headers=H(u["token"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "CHANNEL_ADMIN_REQUIRED"
    org = connect(c, adm, "slack", "org", name="Acme Slack"); assert org["scope"] == "org" and org["editable"] and org["name"] == "Acme Slack"
    mine = connect(c, adm, "slack"); assert mine["id"] != org["id"]  # an admin may also keep a personal connection
    seen = c.get("/api/approvals/channels", headers=H(u["token"])).json()["data"]
    assert [(x["id"], x["editable"]) for x in seen["channels"]] == [(org["id"], False)]  # org yes, the admin's personal no
    assert c.put(f"/api/approvals/channels/{org['id']}", json={"name": "x"}, headers=H(u["token"])).json()["error"]["code"] == "CHANNEL_ADMIN_REQUIRED"
    assert c.delete(f"/api/approvals/channels/{org['id']}", headers=H(u["token"])).status_code == 403
    assert c.delete(f"/api/approvals/channels/{mine['id']}", headers=H(u["token"])).json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    # a user without a connection of their own: verifies through the org bot and uses the org channel on a node
    ua = f"U{uuid.uuid4().hex[:8].upper()}"; link(c, api, u, "slack", ua, own_channel=False)
    wid = workflow(c, u, {"channel_id": org["id"], "channel": "slack", "target": "C0ORG"}); rid = start_waiting(c, u, wid)
    post = until(lambda: [p for p in api.requests() if p["channel"] == "C0ORG"])[-1]
    approve = post["blocks"][1]["elements"][0]["value"]
    assert slack_post(c, org["id"], press(approve, ua)).json()["data"] == {"outcome": "approved"}
    assert until(lambda: run_row(c, u, wid, rid)["status"] == "ok")
    # someone else's personal channel id on a node is not usable: audited as not configured, nothing sent
    n = len(api.requests()); wid2 = workflow(c, u, {"channel_id": mine["id"], "channel": "slack", "target": "C0NO"}); start_waiting(c, u, wid2)
    assert until(lambda: any(e["action"] == "not_configured" for e in c.get("/api/approvals/audit", headers=H(u["token"])).json()["data"])) and len(api.requests()) == n
    # demoted admins cannot touch it anymore
    from app.repositories import UserRepository
    from app.api.deps import get_db
    UserRepository(get_db()).set_admin(adm["id"], False)
    assert c.delete(f"/api/approvals/channels/{org['id']}", headers=H(adm["token"])).json()["error"]["code"] == "CHANNEL_ADMIN_REQUIRED"


def test_several_slack_workspaces_per_owner_routed_by_team_id(c, api):
    o = user(c); ua = f"U{uuid.uuid4().hex[:8].upper()}"; sec_b = "b" * 32
    ta, tb = f"TA{uuid.uuid4().hex[:6].upper()}", f"TB{uuid.uuid4().hex[:6].upper()}"
    a = connect(c, o, "slack", bot_token=f"xoxb-1111-{ta}-abcdefgh")
    b = connect(c, o, "slack", bot_token=f"xoxb-1111-{tb}-abcdefgh", signing_secret=sec_b)
    assert a["id"] != b["id"] and (a["team_id"], a["name"], b["team_id"]) == (ta, f"Team {ta}", tb)
    assert a["shared_callback_path"] == "/api/approvals/callback/slack"
    again = connect(c, o, "slack", bot_token=f"xoxb-1111-{tb}-zzzzzzzz", signing_secret=sec_b)
    assert again["id"] == b["id"] and again["hint"] == "••••zzzz"  # same workspace: replaced, not duplicated
    assert len([x for x in c.get("/api/approvals/channels", headers=H(o["token"])).json()["data"]["channels"] if x["kind"] == "slack"]) == 2
    assert ident(c, o, "slack", ua).json()["error"]["code"] == "CHANNEL_CONFIG_INVALID"  # two workspaces: say which one
    link(c, api, o, "slack", ua, own_channel=False, team=ta)  # verified in A only
    wid = workflow(c, o, {"channel_id": b["id"], "channel": "slack", "target": "C0B"}); rid = start_waiting(c, o, wid)
    approve = until(lambda: [p for p in api.requests() if p["channel"] == "C0B"])[-1]["blocks"][1]["elements"][0]["value"]
    assert slack_post(c, None, press(approve, ua, team="T0NOPE"), secret=sec_b).status_code == 401  # unknown workspace
    assert slack_post(c, None, press(approve, ua, team=tb), secret=SIGNING).status_code == 401      # A's secret for B's team
    assert slack_post(c, None, press(approve, ua, team=ta)).json()["data"]["code"] == "APPROVAL_TOKEN_INVALID"  # sent via B, not A
    r = slack_post(c, None, press(approve, ua, team=tb), secret=sec_b).json()["data"]
    assert r["code"] == "APPROVAL_IDENTITY_UNKNOWN"  # the same member id in workspace B is another account until verified there
    other = user(c); connect(c, other, "slack", bot_token=f"xoxb-1111-{tb}-abcdefgh", signing_secret=sec_b)
    link(c, api, other, "slack", ua, own_channel=False)  # nobody holds ua in B yet: another studio user may verify it there
    ident(c, other, "slack", ""); link(c, api, o, "slack", ua, own_channel=False, team=tb)
    assert len([x for x in c.get("/api/approvals/identities", headers=H(o["token"])).json()["data"]["slots"] if x["kind"] == "slack" and x["verified"]]) == 2
    assert slack_post(c, None, press(approve, ua, team=tb), secret=sec_b).json()["data"] == {"outcome": "approved"}
    assert until(lambda: run_row(c, o, wid, rid)["status"] == "ok")
    upd = api.named("chat.update")[-1]; assert upd["channel"] == "C0B"
    assert [h for (u, _), h in zip(api.calls, api.auth) if u.endswith("chat.update")][-1] == f"Bearer xoxb-1111-{tb}-zzzzzzzz"  # B's (new) token


def test_chat_texts_follow_the_owner_and_presser_language(c, api):
    owner, approver, stranger = user(c), user(c), user(c)
    for u, lang in ((owner, "vi"), (stranger, "en")):
        r = c.put("/api/notifications/preferences", json={"lang": lang}, headers=H(u["token"])); assert r.json()["data"]["lang"] == lang
    r = c.put("/api/notifications/preferences", json={"lang": "fr"}, headers=H(owner["token"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "NOTIFICATION_PREFS_INVALID"
    c.put("/api/notifications/preferences", json={"lang": "vi"}, headers=H(approver["token"]))
    uo, ua, us = (f"U{uuid.uuid4().hex[:8].upper()}" for _ in range(3))
    link(c, api, owner, "slack", uo); assert vi_text("vi", "channels.code").split(":")[0] in [b for b in api.named("chat.postMessage") if b["channel"] == uo][-1]["text"]
    link(c, api, approver, "slack", ua); link(c, api, stranger, "slack", us)
    assert "verification code" in [b for b in api.named("chat.postMessage") if b["channel"] == us][-1]["text"]
    ch = c.get("/api/approvals/channels", headers=H(owner["token"])).json()["data"]["channels"][0]
    wid = workflow(c, owner, {"channel_id": ch["id"], "channel": "slack", "target": "C0VI", "approvers": [approver["email"]]}); rid = start_waiting(c, owner, wid)
    post = until(lambda: [p for p in api.requests() if p["channel"] == "C0VI"])[-1]
    body = post["blocks"][0]["text"]["text"]
    say = lambda key, **kw: vi_text("vi", f"channels.{key}").format(**kw)  # noqa: E731
    assert body.startswith(f"*{say('title')}*") and say("step", v="") in body and say("run", v=rid) in body
    assert [e["text"]["text"] for e in post["blocks"][1]["elements"]] == [say("approve"), say("reject")]
    approve = post["blocks"][1]["elements"][0]["value"]
    slack_post(c, ch["id"], press(approve, us))  # the stranger reads the refusal in English
    assert [b for u, b in api.calls if u.startswith("https://hooks.slack.com/")][-1]["text"] == "You are not allowed to approve this run"
    assert slack_post(c, ch["id"], press(approve, ua)).json()["data"] == {"outcome": "approved"}
    assert api.named("chat.update")[-1]["text"].startswith(say("at", text=say("approved_by", who=approver["email"]), when=""))


def test_identity_is_verified_with_a_one_time_code(c, api, monkeypatch):
    a, b = user(c), user(c); uid = f"U{uuid.uuid4().hex[:8].upper()}"
    # no Slack workspace the user could use yet: nothing to link to
    assert ident(c, a, "slack", uid).json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    assert c.get("/api/approvals/identities", headers=H(a["token"])).json()["data"] == {"slots": [
        {"kind": k, "team_id": None, "team_name": None, "available": False, "external_id": None, "verified": False, "code_pending": False, "code_expires": None}
        for k in ("telegram", "whatsapp")]}  # e-mail and Teams are link channels: no identity
    connect(c, a, "slack")
    assert ident(c, a, "slack", "lower").json()["error"]["code"] == "IDENTITY_INVALID"
    assert c.post("/api/approvals/identities/slack/send-code", headers=H(a["token"])).json()["error"]["code"] == "IDENTITY_NOT_LINKED"
    got = slot(ident(c, a, "slack", uid).json()["data"], "slack")
    assert got == {"kind": "slack", "team_id": "2222", "team_name": "Team 2222", "available": True, "external_id": uid, "verified": False, "code_pending": False, "code_expires": None}
    sent = slot(c.post("/api/approvals/identities/slack/send-code", headers=H(a["token"])).json()["data"], "slack")
    assert sent["code_pending"] and not sent["verified"] and api.named("chat.postMessage")[-1]["channel"] == uid 
    code = code_for(api, uid); assert code not in json.dumps(sent)
    r = c.post("/api/approvals/identities/slack/send-code", headers=H(a["token"]))  # resend throttle
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED" and int(r.headers["Retry-After"]) > 0
    wrong = "000000" if code != "000000" else "111111"
    r = c.post("/api/approvals/identities/slack/verify", json={"code": wrong}, headers=H(a["token"]))
    assert r.status_code == 400 and r.json()["error"] == {"code": "IDENTITY_CODE_INVALID", "message": "Wrong code, 4 attempt(s) left", "details": {"left": 4}}
    for _ in range(3): c.post("/api/approvals/identities/slack/verify", json={"code": wrong}, headers=H(a["token"]))
    r = c.post("/api/approvals/identities/slack/verify", json={"code": wrong}, headers=H(a["token"]))
    assert r.status_code == 429 and r.json()["error"]["code"] == "IDENTITY_CODE_ATTEMPTS"
    assert c.post("/api/approvals/identities/slack/verify", json={"code": code}, headers=H(a["token"])).json()["error"]["code"] == "IDENTITY_CODE_ATTEMPTS"
    monkeypatch.setenv("STUDIO_IDENTITY_CODE_RESEND", "0")
    c.post("/api/approvals/identities/slack/send-code", headers=H(a["token"])); code = code_for(api, uid)
    import app.services.identity_service as mod
    from types import SimpleNamespace
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mod, "time", SimpleNamespace(time=lambda: time.time() + 3600))
        assert c.post("/api/approvals/identities/slack/verify", json={"code": code}, headers=H(a["token"])).status_code == 410  # IDENTITY_CODE_EXPIRED
    c.post("/api/approvals/identities/slack/send-code", headers=H(a["token"])); code = code_for(api, uid)
    assert c.post("/api/approvals/identities/slack/verify", json={"code": code}, headers=H(a["token"])).json()["data"]["slots"][0]["verified"] is True
    # b claims the same account: may link (unverified) but cannot verify it while a holds it
    connect(c, b, "slack")
    ident(c, b, "slack", uid); c.post("/api/approvals/identities/slack/send-code", headers=H(b["token"]))
    r = c.post("/api/approvals/identities/slack/verify", json={"code": code_for(api, uid)}, headers=H(b["token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDENTITY_TAKEN"
    assert slot(ident(c, a, "slack", "").json()["data"], "slack")["external_id"] is None  # unlink
    link(c, api, b, "slack", uid, own_channel=False)


def test_slack_approval_end_to_end(c, api):
    owner, approver, stranger = user(c), user(c), user(c)
    ch = connect(c, owner, "slack")
    ua, us = f"U{uuid.uuid4().hex[:8].upper()}", f"U{uuid.uuid4().hex[:8].upper()}"
    link(c, api, approver, "slack", ua); link(c, api, stranger, "slack", us)
    wid = workflow(c, owner, {"channel": "slack", "target": "C0APPROVALS", "approvers": [approver["email"].upper()]})
    rid = start_waiting(c, owner, wid)
    post = until(lambda: api.requests())[0]
    assert post["channel"] == "C0APPROVALS" and "Approve refund for order A100?" in post["blocks"][0]["text"]["text"]
    approve, reject = (e["value"] for e in post["blocks"][1]["elements"])
    # unauthenticated / tampered / replayed-late requests
    assert slack_post(c, ch["id"], press(approve, ua), secret="0" * 32).status_code == 401
    r = slack_post(c, ch["id"], press(approve, ua), ts=time.time() - 600); assert r.status_code == 401 and r.json()["error"]["code"] == "CHANNEL_SIGNATURE_INVALID"
    assert slack_post(c, ch["id"], press(approve[:-2] + "xx", ua)).json()["data"] == {"outcome": "refused", "code": "APPROVAL_TOKEN_INVALID"}
    assert slack_post(c, ch["id"], press(approve.replace("a.", "r.", 1), ua)).json()["data"]["code"] == "APPROVAL_TOKEN_INVALID"  # decision is signed
    # not mapped / not allowed: refused, told privately, run still waiting
    unverified = user(c); connect(c, unverified, "slack"); ident(c, unverified, "slack", "U0NOBODY")  # linked, never verified
    assert slack_post(c, ch["id"], press(approve, "U0NOBODY")).json()["data"]["code"] == "APPROVAL_IDENTITY_UNKNOWN"
    assert slack_post(c, ch["id"], press(approve, us)).json()["data"]["code"] == "APPROVAL_FORBIDDEN"
    eph = [b for u, b in api.calls if u.startswith("https://hooks.slack.com/")]
    assert len(eph) == 4 and {e["response_type"] for e in eph} == {"ephemeral"} and "not allowed" in eph[-1]["text"] and "Link and verify your Slack account" in eph[-2]["text"]
    assert run_row(c, owner, wid, rid)["status"] == "waiting"
    # allowed approver: accepted, run resumes in the worker, message edited
    assert slack_post(c, ch["id"], press(approve, ua)).json()["data"] == {"outcome": "approved"}
    done = until(lambda: (r := run_row(c, owner, wid, rid))["status"] == "ok" and r)
    assert done["final_state"]["decision"] == "approved"
    resumed = next(e for e in done["events"] if e["type"] == "run_resumed")
    assert resumed["response"] == "approved" and resumed["by"] == {"channel": "slack", "user_id": approver["id"]}
    upd = api.named("chat.update")[-1]; assert upd["ts"] == post.get("ts", upd["ts"]) and approver["email"] in upd["text"] and "Approved" in upd["text"]
    # single use: the same (or the other) button is refused afterwards
    assert slack_post(c, ch["id"], press(approve, ua)).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    assert slack_post(c, ch["id"], press(reject, ua, "reject")).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    log = c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"]
    mine = [e for e in log if e["run_id"] == rid][::-1]
    assert [(e["action"], e["code"]) for e in mine] == [("requested", None), ("denied", "APPROVAL_IDENTITY_UNKNOWN"), ("denied", "APPROVAL_FORBIDDEN"),
                                                       ("approved", None), ("denied", "APPROVAL_ALREADY_DECIDED"), ("denied", "APPROVAL_ALREADY_DECIDED")]
    assert mine[3]["actor"] == approver["email"] and mine[3]["external_id"] == ua and mine[0]["workflow_name"].startswith("Refund")
    assert c.get("/api/approvals/audit", headers=H(approver["token"])).json()["data"] == []  # the owner's log only


def test_telegram_webhook_registration_reject_and_secret_header(c, api, monkeypatch):
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.example.com")
    owner = user(c); tid = str(int(time.time() * 1000) % 10**12)
    ch = connect(c, owner, "telegram")
    assert ch["callback_url"] == f"https://studio.example.com/api/approvals/callback/telegram/{ch['id']}"
    reg = c.post(f"/api/approvals/channels/{ch['id']}/register-webhook", headers=H(owner["token"])).json()["data"]
    assert reg["registered"] is True and api.named("setWebhook")[-1] == {"url": ch["callback_url"], "secret_token": TG["webhook_secret"], "allowed_updates": ["callback_query", "message"]}
    link(c, api, owner, "telegram", tid, own_channel=False)
    wid = workflow(c, owner, {"channel": "telegram", "target": "-100200300"}); rid = start_waiting(c, owner, wid)
    msg = until(lambda: api.requests("sendMessage"))[-1]
    keys = msg["reply_markup"]["inline_keyboard"][0]; reject = keys[1]["callback_data"]
    assert all(len(k["callback_data"].encode()) <= 64 for k in keys)  # Telegram's callback_data limit
    assert f"studio.example.com/workflows/{wid}?run={rid}" in msg["text"]
    upd = {"update_id": 1, "callback_query": {"id": "cq1", "from": {"id": int(tid)}, "data": reject, "message": {"message_id": 1, "chat": {"id": -100200300}}}}
    url = f"/api/approvals/callback/telegram/{ch['id']}"
    assert c.post(url, json=upd, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 401
    assert c.post(url, json={"update_id": 2, "message": {"text": "hi"}}, headers={"X-Telegram-Bot-Api-Secret-Token": TG["webhook_secret"]}).json()["data"] == {"outcome": "ignored"}
    assert c.post(url, json=upd, headers={"X-Telegram-Bot-Api-Secret-Token": TG["webhook_secret"]}).json()["data"] == {"outcome": "rejected"}
    done = until(lambda: (r := run_row(c, owner, wid, rid))["status"] == "ok" and r)
    assert done["final_state"]["decision"] == "rejected"
    assert api.named("answerCallbackQuery")[-1]["show_alert"] is False and "Rejected" in api.named("editMessageText")[-1]["text"]


def test_expired_button_and_answer_in_studio_supersede(c, api):
    owner = user(c); ua = f"U{uuid.uuid4().hex[:8].upper()}"
    ch = connect(c, owner, "slack")
    link(c, api, owner, "slack", ua, own_channel=False)
    wid = workflow(c, owner, {"channel": "slack", "target": "C1"})
    # (1) expired token
    rid = start_waiting(c, owner, wid); approve = until(lambda: api.requests())[-1]["blocks"][1]["elements"][0]["value"]
    svc = approval_service(); req = svc.repo.requests_for_run(rid)[0]
    from sqlalchemy import update
    from app.models import ApprovalRequest
    with svc.repo.db.session() as s: s.execute(update(ApprovalRequest).where(ApprovalRequest.id == req.id).values(expires=time.time() - 1)); s.commit()
    assert slack_post(c, ch["id"], press(approve, ua)).json()["data"]["code"] == "APPROVAL_TOKEN_INVALID"  # expiry is signed into the token
    with svc.repo.db.session() as s: s.execute(update(ApprovalRequest).where(ApprovalRequest.id == req.id).values(expires=req.expires)); s.commit()
    import app.services.approval_service as mod
    from types import SimpleNamespace
    later = SimpleNamespace(time=lambda: req.expires + 1, strftime=time.strftime, gmtime=time.gmtime)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mod, "time", later)  # the service's clock only; the Slack signature check keeps real time
        assert slack_post(c, ch["id"], press(approve, ua)).json()["data"]["code"] == "APPROVAL_TOKEN_EXPIRED"
    assert svc.repo.request(req.id).status == "expired"
    # (2) answered in the studio: the channel request is closed and its message edited
    rid2 = start_waiting(c, owner, wid); approve2 = until(lambda: len(api.requests()) >= 2 and api.requests())[-1]["blocks"][1]["elements"][0]["value"]
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"resume_run_id": rid2, "response": True})
        while w.receive_json()["type"] != "run_summary": pass
    assert until(lambda: any(b["text"] == "Answered in Superstep" for b in api.named("chat.update")))
    assert slack_post(c, ch["id"], press(approve2, ua)).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    actions = [e["action"] for e in c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"] if e["run_id"] == rid2]
    assert "superseded" in actions


def test_inbox_answer_closes_the_channel_request(c, api):
    """an approver answers from the Approvals inbox first; the Slack buttons are refused afterwards."""
    owner, approver = user(c), user(c); ua = f"U{uuid.uuid4().hex[:8].upper()}"
    ch = connect(c, owner, "slack"); link(c, api, approver, "slack", ua)
    wid = workflow(c, owner, {"channel": "slack", "target": "C1", "approvers": [approver["email"]]})
    rid = start_waiting(c, owner, wid); approve = until(lambda: api.requests())[-1]["blocks"][1]["elements"][0]["value"]
    [row] = [x for x in c.get("/api/approvals/inbox", headers=H(approver["token"])).json()["data"] if x["run_id"] == rid]
    assert row["channel"] == "slack" and row["mine"] is False
    assert c.post(f"/api/approvals/inbox/{rid}", json={"response": "rejected"}, headers=H(approver["token"])).status_code == 200
    assert until(lambda: any(b["text"] == "Answered in Superstep" for b in api.named("chat.update")))
    assert slack_post(c, ch["id"], press(approve, ua)).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    assert until(lambda: run_row(c, owner, wid, rid)["status"] == "ok")
    assert run_row(c, owner, wid, rid)["final_state"]["decision"] == "rejected"


def test_deadline_reminder_replaces_the_slack_message(c, api):
    """a reminder posts a new request and closes the old one; buttons expire at the deadline; a timeout edits it."""
    owner, approver = user(c), user(c); ua = f"U{uuid.uuid4().hex[:8].upper()}"
    ch = connect(c, owner, "slack"); link(c, api, approver, "slack", ua)
    wf = json.loads(json.dumps(APPROVAL)); wf["name"] = f"Leave {uuid.uuid4().hex[:4]}"
    wf["nodes"][1]["data"].update(approval={"channel": "slack", "target": "C1", "approvers": [approver["email"]]},
                                  deadline={"after": "2h", "remind_every": "1h", "on_timeout": "reject"})
    wid = c.post("/api/workflows", json=wf, headers=H(owner["token"])).json()["data"]["id"]
    rid = start_waiting(c, owner, wid); first = until(lambda: api.requests())[-1]["blocks"][1]["elements"][0]["value"]
    svc = approval_service(); w = svc.repo.latest_wait(rid)
    assert svc.repo.requests_for_run(rid)[0].expires == pytest.approx(w.due_at)  # sooner than STUDIO_APPROVAL_TTL (24 h)
    assert svc.fire_deadlines(w.created + 3601) == 1
    assert len(api.requests()) == 2 and any("Reminder sent" in b["text"] for b in api.named("chat.update"))
    assert slack_post(c, ch["id"], press(first, ua)).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    assert svc.fire_deadlines(w.created + 7201) == 1
    assert any("rejected by the deadline" in b["text"] for b in api.named("chat.update"))
    assert until(lambda: run_row(c, owner, wid, rid)["status"] == "ok")


def test_no_op_without_a_configured_channel(c, api):
    owner = user(c)
    wid = workflow(c, owner, {"channel": "slack", "target": "C1"}); rid = start_waiting(c, owner, wid)
    log = until(lambda: c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"])
    assert [(e["action"], e["code"], e["run_id"]) for e in log] == [("not_configured", "CHANNEL_NOT_FOUND", rid)] and api.calls == []
    wid2 = workflow(c, owner, {}); start_waiting(c, owner, wid2); time.sleep(0.2)
    assert len(c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"]) == 1  # no channel on the node: nothing at all


def test_send_failure_is_audited_and_the_run_keeps_waiting(c, api):
    owner = user(c); connect(c, owner, "slack")
    wid = workflow(c, owner, {"channel": "slack", "target": "C0FAIL"})
    orig = api.__call__
    rid = None
    def failing(req):
        if req.url.path.endswith("chat.postMessage"): return httpx.Response(200, json={"ok": False, "error": "channel_not_found"})
        return orig(req)
    for a in ADAPTERS.values(): a.transport = httpx.MockTransport(failing)
    rid = start_waiting(c, owner, wid)
    log = until(lambda: [e for e in c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"] if e["action"] == "send_failed"])
    assert log[0]["code"] == "CHANNEL_API_FAILED" and log[0]["run_id"] == rid
    assert run_row(c, owner, wid, rid)["status"] == "waiting"


def test_api_run_resumed_from_a_channel_sends_its_callback(c, api, monkeypatch):
    """follow-up: the callback_url of an API-triggered run gets the final result after a chat approval."""
    from app.services import webhooks
    got = []
    def hook(req): got.append((req.headers["x-studio-event"], json.loads(req.content), req)); return httpx.Response(204)
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(hook)))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1")
    owner = user(c); uo = f"U{uuid.uuid4().hex[:8].upper()}"; link(c, api, owner, "slack", uo)
    ch = c.get("/api/approvals/channels", headers=H(owner["token"])).json()["data"]["channels"][0]
    wid = workflow(c, owner, {"channel_id": ch["id"], "channel": "slack", "target": "C0API"})
    tok = c.post(f"/api/workflows/{wid}/tokens", json={"name": "ci"}, headers=H(owner["token"])).json()["data"]
    rid = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "order A100"}, "callback_url": "http://localhost:9/hook"},
                 headers=H(tok["token"])).json()["data"]["run_id"]
    first = until(lambda: [b for _, b, _ in got if b["run_id"] == rid])[0]
    assert first["status"] == "waiting"  # the pause is reported as before
    post = until(lambda: [p for p in api.requests() if p["channel"] == "C0API"])[-1]
    assert slack_post(c, ch["id"], press(post["blocks"][1]["elements"][0]["value"], uo)).json()["data"] == {"outcome": "approved"}
    final = until(lambda: [(e, b, r) for e, b, r in got if b["run_id"] == rid and b["status"] == "ok"])[0]
    assert final[0] == "run.finished" and final[1]["final_state"]["decision"] == "approved"
    assert webhooks.verify_signature(tok["signing_secret"], final[2].headers["x-studio-signature"], final[2].content)  # same pipeline: signed
    # the hook sees the request before the worker marks the delivery ok: wait for the log, do not read it once
    statuses = lambda: sorted(d["status"] for d in c.get(f"/api/workflows/{wid}/deliveries", headers=H(owner["token"])).json()["data"] if d["run_id"] == rid)
    assert until(lambda: statuses() == ["ok", "ok"]), statuses()


def test_callbacks_are_rate_limited_per_ip_and_per_channel(c, api, monkeypatch):
    monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_IP", "3"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", "5")
    monkeypatch.setenv("STUDIO_TRUST_PROXY", "1")
    o = user(c); ch = connect(c, o, "telegram"); url = f"/api/approvals/callback/telegram/{ch['id']}"
    run = uuid.uuid4().hex[:6]
    def hit(ip, path=url): return c.post(path, json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": TG["webhook_secret"],
                                                                           "X-Forwarded-For": f"6.6.6.6, 10.{run[:2]}.{ip}"})
    ips = [f"{int(run[2:4], 16)}.{n}" for n in range(1, 4)]
    assert [hit(ips[0]).status_code for _ in range(3)] == [200, 200, 200]  # 3 per IP (the spoofable first hop is ignored)
    r = hit(ips[0]); assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED" and int(r.headers["Retry-After"]) >= 1
    assert [hit(ips[1]).status_code for _ in range(2)] == [200, 200]   # 5 per connection, whatever the IP
    assert hit(ips[2]).status_code == 429
    other = connect(c, user(c), "telegram")
    assert hit(ips[2], f"/api/approvals/callback/telegram/{other['id']}").status_code == 200  # other connections are not affected
    # the shared Slack URL counts per claimed workspace; unauthenticated floods are cut before signature checks
    monkeypatch.setenv("STUDIO_TRUST_PROXY", "0"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_IP", "0"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", "2")
    codes = [slack_post(c, None, press("x", "U1", team=f"T{run}"), secret="0" * 32).status_code for _ in range(3)]
    assert codes == [401, 401, 429]
    assert slack_post(c, None, press("x", "U1", team=f"T{run}X"), secret="0" * 32).status_code == 401  # another workspace: own budget


def test_concurrent_verification_has_one_winner(c, api, monkeypatch):
    """Both users pass the "already taken?" read before either writes: the partial unique index picks one winner,
    the loser gets IDENTITY_TAKEN (409), and the DB never holds two verified owners of one account."""
    from sqlalchemy import text
    from app.repositories.approvals import ApprovalRepository
    a, b = user(c), user(c); ext = f"U{uuid.uuid4().hex[:8].upper()}"
    for u in (a, b):
        connect(c, u, "slack")
        assert ident(c, u, "slack", ext).status_code == 200
        assert c.post("/api/approvals/identities/slack/send-code", json={}, headers=H(u["token"])).status_code == 200
    monkeypatch.setattr(ApprovalRepository, "user_for", lambda *_a, **_k: None)  # the race: nobody looks verified yet
    ca, cb = [re.search(r"\b(\d{6})\b", m["text"]).group(1) for m in api.named("chat.postMessage")[-2:]]  # a's code, then b's
    ra = c.post("/api/approvals/identities/slack/verify", json={"code": ca}, headers=H(a["token"]))
    rb = c.post("/api/approvals/identities/slack/verify", json={"code": cb}, headers=H(b["token"]))
    assert ra.status_code == 200 and slot(ra.json()["data"], "slack")["verified"] is True
    assert rb.status_code == 409 and rb.json()["error"]["code"] == "IDENTITY_TAKEN"
    monkeypatch.undo()
    with approval_service().repo.db.session() as s:
        n = s.execute(text("SELECT count(*) FROM channel_identities WHERE external_id = :e AND verified_at IS NOT NULL"), {"e": ext}).scalar_one()
    assert n == 1


def test_api_run_resumed_from_the_studio_sends_its_callback_once(c, api, monkeypatch):
    """Every resume source ends in RunService.settled: the studio (WebSocket) resume of an API run sends the callback too,
    and settling the same segment again (a second worker, a recovery) inserts no second delivery."""
    import asyncio
    from app.api.deps import run_service
    from app.services import webhooks
    got = []
    def hook(req): got.append(json.loads(req.content)); return httpx.Response(204)
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(hook)))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1")
    owner = user(c); wid = workflow(c, owner, {})  # no chat channel: answered in the studio
    tok = c.post(f"/api/workflows/{wid}/tokens", json={"name": "ci"}, headers=H(owner["token"])).json()["data"]
    rid = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "order A100"}, "callback_url": "http://localhost:9/hook"},
                 headers=H(tok["token"])).json()["data"]["run_id"]
    until(lambda: [b for b in got if b["run_id"] == rid and b["status"] == "waiting"])
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"resume_run_id": rid, "response": "approved"})
        while w.receive_json()["type"] != "run_summary": pass
    final = until(lambda: [b for b in got if b["run_id"] == rid and b["status"] == "ok"])[0]
    assert final["final_state"]["decision"] == "approved"
    for _ in range(2): asyncio.run(run_service().settled(rid))  # same settled state: idempotent
    log = [d for d in c.get(f"/api/workflows/{wid}/deliveries", headers=H(owner["token"])).json()["data"] if d["run_id"] == rid]
    assert len(log) == 2 and len([b for b in got if b["run_id"] == rid]) == 2  # the pause + the result, nothing twice


def test_test_connection(c, api, monkeypatch):
    from app.core.errors import AppError
    o = user(c); ch = connect(c, o, "slack")
    r = c.post(f"/api/approvals/channels/{ch['id']}/test", headers=H(o["token"]))
    assert r.status_code == 200 and r.json()["data"] == {"ok": True, "name": "Team 2222", "team_id": "2222", "matches": True,
                                                         "missing_scopes": None}  # the fake sends no x-oauth-scopes: unknown
    assert c.post(f"/api/approvals/channels/{ch['id']}/test", headers=H(user(c)["token"])).json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    def broken(self, secrets): raise AppError("CHANNEL_API_FAILED", kind="Slack", reason="invalid_auth")
    monkeypatch.setattr(type(ADAPTERS["slack"]), "describe", broken)
    r = c.post(f"/api/approvals/channels/{ch['id']}/test", headers=H(o["token"]))
    assert r.status_code == 502 and r.json()["error"]["code"] == "CHANNEL_API_FAILED"
