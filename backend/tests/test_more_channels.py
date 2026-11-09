"""WhatsApp (buttons, signed webhook, GET verification, templates), and the link channels e-mail and Teams
(decided by the signed-in studio user on /approve)."""
import hashlib, hmac, json, re, time, uuid
import httpx, pytest
from app.services.approval_channels import ADAPTERS, links as links_mod
from tests.test_approval_channels import H, c, run_row, start_waiting, until, workflow  # noqa: F401  (c is a fixture)

WA = {"access_token": "EAAG" + "x" * 40, "phone_number_id": "1098765432", "app_secret": "0123456789abcdef0123456789abcdef", "verify_token": "verify-me-123"}
PHONE = "84901234567"


def user(c, approvers=None):
    d = c.post("/api/auth/register", json={"email": f"m{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


class Platform:
    """Answers like the WhatsApp Cloud API and a Teams Workflows webhook, and records what was sent."""
    def __init__(self): self.sent: list[dict] = []; self.cards: list[dict] = []
    def __call__(self, req: httpx.Request) -> httpx.Response:
        if req.headers.get("host", "").endswith("webhook.test"):  # the URL holds the pinned IP; Host keeps the name
            self.cards.append(json.loads(req.content)["attachments"][0]["content"]); return httpx.Response(202)
        if req.method == "GET": return httpx.Response(200, json={"verified_name": "Acme Support", "display_phone_number": "+84 90 123"})
        body = json.loads(req.content); self.sent.append(body)
        return httpx.Response(200, json={"messages": [{"id": f"wamid.{len(self.sent)}"}]})


@pytest.fixture(autouse=True)
def platform(monkeypatch):
    import app.services.approval_service as mod
    monkeypatch.setattr(mod, "BACKGROUND", False)
    monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_IP", "0"); monkeypatch.setenv("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", "0")
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.test")
    p = Platform()
    for a in ADAPTERS.values(): monkeypatch.setattr(a, "transport", httpx.MockTransport(p), raising=False)
    monkeypatch.setattr(links_mod, "public_address", lambda url, allow, code, **kw: (url, "93.184.216.34"))  # no DNS in tests
    return p


def connect(c, u, kind, **values):
    r = c.post("/api/approvals/channels", json={"kind": kind, **values}, headers=H(u["token"])); assert r.status_code == 200, r.json(); return r.json()["data"]


def wa_post(c, cid, payload, secret=WA["app_secret"]):
    body = json.dumps(payload).encode(); sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return c.post(f"/api/approvals/callback/whatsapp/{cid}", content=body, headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})


def wa_press(token, sender=PHONE, template=False):
    m = {"from": sender, "type": "button", "button": {"payload": token, "text": "Approve"}} if template else \
        {"from": sender, "type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": token, "title": "Approve"}}}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {"messages": [m]}}]}]}


# ---------- WhatsApp ----------
def test_whatsapp_verification_identity_buttons_and_signature(c, platform):
    o = user(c); ch = connect(c, o, "whatsapp", **WA)
    assert ch["name"] == "Acme Support"
    ok = c.get(f"/api/approvals/callback/whatsapp/{ch['id']}", params={"hub.mode": "subscribe", "hub.verify_token": WA["verify_token"], "hub.challenge": "1158201444"})
    assert ok.status_code == 200 and ok.text == "1158201444"
    assert c.get(f"/api/approvals/callback/whatsapp/{ch['id']}", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"}).status_code == 401

    # link the owner's WhatsApp number with a one-time code
    assert c.put("/api/approvals/identities", json={"kind": "whatsapp", "external_id": PHONE}, headers=H(o["token"])).status_code == 200
    c.post("/api/approvals/identities/whatsapp/send-code", headers=H(o["token"]))
    code = re.search(r"\b(\d{6})\b", platform.sent[-1]["text"]["body"]).group(1)
    assert c.post("/api/approvals/identities/whatsapp/verify", json={"code": code}, headers=H(o["token"])).status_code == 200

    wid = workflow(c, o, {"channel_id": ch["id"], "channel": "whatsapp", "target": PHONE}); rid = start_waiting(c, o, wid)
    req = until(lambda: next((m for m in platform.sent if m.get("type") == "interactive"), None))
    assert req["to"] == PHONE and "order A100" in req["interactive"]["body"]["text"]
    approve, reject = (b["reply"]["id"] for b in req["interactive"]["action"]["buttons"])
    assert wa_post(c, ch["id"], wa_press(approve), secret="f" * 32).status_code == 401  # wrong app secret
    assert wa_post(c, ch["id"], wa_press(approve)).json()["data"] == {"outcome": "approved"}
    until(lambda: run_row(c, o, wid, rid)["status"] == "ok")
    outcome = platform.sent[-1]
    assert outcome["type"] == "text" and "Approved by" in outcome["text"]["body"] and outcome["context"]["message_id"] == "wamid.2"
    assert wa_post(c, ch["id"], wa_press(reject)).json()["data"]["code"] == "APPROVAL_ALREADY_DECIDED"
    assert "already answered" in platform.sent[-1]["text"]["body"]  # told privately


def test_whatsapp_template_outside_the_24_hour_window(c, platform):
    o = user(c); ch = connect(c, o, "whatsapp", **WA, template_name="studio_approval", template_lang="vi"); phone = "84907654321"  # one verified owner per number
    c.put("/api/approvals/identities", json={"kind": "whatsapp", "external_id": phone}, headers=H(o["token"]))
    c.post("/api/approvals/identities/whatsapp/send-code", headers=H(o["token"]))
    code = re.search(r"\b(\d{6})\b", platform.sent[-1]["text"]["body"]).group(1)
    c.post("/api/approvals/identities/whatsapp/verify", json={"code": code}, headers=H(o["token"]))
    wid = workflow(c, o, {"channel_id": ch["id"], "channel": "whatsapp", "target": phone}); rid = start_waiting(c, o, wid)
    req = until(lambda: next((m for m in platform.sent if m.get("type") == "template"), None))
    assert req["template"]["name"] == "studio_approval" and req["template"]["language"] == {"code": "vi"}
    approve = req["template"]["components"][1]["parameters"][0]["payload"]
    assert wa_post(c, ch["id"], wa_press(approve, sender=phone, template=True)).json()["data"] == {"outcome": "approved"}
    until(lambda: run_row(c, o, wid, rid)["status"] == "ok")


def test_whatsapp_settings_are_validated(c):
    o = user(c)
    r = c.post("/api/approvals/channels", json={"kind": "whatsapp", **WA, "app_secret": "short"}, headers=H(o["token"]))
    assert r.json()["error"] == {**r.json()["error"], "code": "CHANNEL_CONFIG_INVALID"} and r.json()["error"]["details"]["field"] == "app_secret"


# ---------- e-mail ----------
@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setenv("SMTP_HOST", "smtp.test"); monkeypatch.setenv("SMTP_FROM", "studio@acme.test")
    # mailer.send also carries the "a run is waiting" notification; keep only approval e-mail
    monkeypatch.setattr(links_mod.mailer, "send", lambda smtp, to, subject, text, html=None: ("Approval needed" in subject and sent.append({"to": to, "subject": subject, "text": text})) or True)
    return sent


def test_email_needs_smtp_and_a_public_url(c, monkeypatch):
    o = user(c)
    r = c.post("/api/approvals/channels", json={"kind": "email"}, headers=H(o["token"]))
    assert r.json()["error"]["code"] == "CHANNEL_API_FAILED" and "SMTP_HOST" in r.json()["error"]["message"]


def test_email_links_are_decided_by_the_signed_in_approver(c, mail):
    o = user(c); boss = user(c); stranger = user(c)
    ch = connect(c, o, "email"); assert ch["name"] == "studio@acme.test"
    assert "email" not in {s["kind"] for s in c.get("/api/approvals/identities", headers=H(o["token"])).json()["data"]["slots"]}  # nothing to link
    wid = workflow(c, o, {"channel_id": ch["id"], "channel": "email", "target": f"{boss['email']}, ops@acme.test", "approvers": [boss["email"]]})
    rid = start_waiting(c, o, wid)
    until(lambda: len(mail) == 2)
    assert {m["to"] for m in mail} == {boss["email"], "ops@acme.test"} and "order A100" in mail[0]["text"]
    approve = re.search(r"https://studio\.test/approve\?token=(a\.\S+)", mail[0]["text"]).group(1)
    reject = re.search(r"https://studio\.test/approve\?token=(r\.\S+)", mail[0]["text"]).group(1)

    assert c.get("/api/approvals/link", params={"token": approve}, headers=H(stranger["token"])).json()["error"]["code"] == "APPROVAL_FORBIDDEN"
    info = c.get("/api/approvals/link", params={"token": reject}, headers=H(boss["token"])).json()["data"]
    assert info["decision"] == "rejected" and info["status"] == "pending" and "order A100" in info["prompt"] and info["run_id"] == rid
    assert c.post("/api/approvals/link", json={"token": approve}, headers=H(stranger["token"])).json()["error"]["code"] == "APPROVAL_FORBIDDEN"
    assert c.post("/api/approvals/link", json={"token": approve}, headers=H(boss["token"])).json()["data"] == {"decision": "approved", "run_id": rid, "workflow_id": wid}
    until(lambda: run_row(c, o, wid, rid)["status"] == "ok")
    assert c.post("/api/approvals/link", json={"token": reject}, headers=H(o["token"])).json()["error"]["code"] == "APPROVAL_ALREADY_DECIDED"
    assert c.get("/api/approvals/link", params={"token": approve}, headers=H(o["token"])).json()["data"]["decided_by"] == boss["email"]
    assert c.get("/api/approvals/link", params={"token": "a.nope.sig"}, headers=H(o["token"])).json()["error"]["code"] == "APPROVAL_TOKEN_INVALID"
    audit = {e["action"] for e in c.get("/api/approvals/audit", headers=H(o["token"])).json()["data"] if e["run_id"] == rid}
    assert {"requested", "approved", "denied"} <= audit


def test_email_with_a_bad_address_is_audited_as_a_send_failure(c, mail):
    o = user(c); ch = connect(c, o, "email")
    wid = workflow(c, o, {"channel_id": ch["id"], "channel": "email", "target": "not-an-address"}); rid = start_waiting(c, o, wid)
    until(lambda: any(e["action"] == "send_failed" and e["run_id"] == rid for e in c.get("/api/approvals/audit", headers=H(o["token"])).json()["data"]))
    assert not mail and run_row(c, o, wid, rid)["status"] == "waiting"


# ---------- Teams ----------
def test_teams_card_without_a_target_and_outcome_card(c, platform):
    o = user(c); ch = connect(c, o, "teams", webhook_url="https://acme.webhook.test/workflows/abc123")
    assert ch["hint"] and ch["team_id"]
    other = connect(c, o, "teams", webhook_url="https://acme.webhook.test/workflows/other")  # another Teams channel, another connection
    assert other["id"] != ch["id"]
    wid = workflow(c, o, {"channel_id": ch["id"], "channel": "teams", "target": ""}); rid = start_waiting(c, o, wid)
    card = until(lambda: platform.cards and platform.cards[0])
    assert card["type"] == "AdaptiveCard" and any("order A100" in b["text"] for b in card["body"])
    urls = [a["url"] for a in card["actions"]]
    approve = urls[0].split("token=")[1]; assert urls[0].startswith("https://studio.test/approve?token=a.")
    assert c.post("/api/approvals/link", json={"token": approve}, headers=H(o["token"])).json()["data"]["decision"] == "approved"
    until(lambda: run_row(c, o, wid, rid)["status"] == "ok")
    assert "Approved by" in platform.cards[-1]["body"][0]["text"]


def test_teams_webhook_must_be_https_unless_private_callbacks_are_allowed(c, monkeypatch):
    o = user(c); monkeypatch.delenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", raising=False)
    r = c.post("/api/approvals/channels", json={"kind": "teams", "webhook_url": "http://acme.webhook.test/workflows/abc123"}, headers=H(o["token"]))
    assert r.json()["error"]["code"] == "CHANNEL_CONFIG_INVALID" and r.json()["error"]["details"]["field"] == "webhook_url"
