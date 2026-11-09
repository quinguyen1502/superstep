"""SMTP credentials and Send email nodes (dry run without a credential, effectively-once sending, quota)."""
import copy, email, socket, uuid
from email import policy
import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from fastapi.testclient import TestClient
from app.core import smtp
from app.engine import emails
from app.engine.effects import Effects
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.main import app

c = TestClient(app)
PASSWORD = "app-password-0123456789"


def H(t): return {"Authorization": f"Bearer {t}"}
def user(): return c.post("/api/auth/register", json={"email": f"mail{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t): return {"id": i, "source": s, "target": t}


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


STATE = [{"name": "email", "type": "string"}, {"name": "name", "type": "string"}, {"name": "emails", "type": "list"}, {"name": "sent", "type": "object"}]


def flow(**extra):
    d = {"label": "Mail", "to": "{{state.email}}", "cc": "boss@acme.test", "bcc": "audit@acme.test", "reply_to": "help@acme.test",
         "subject": "Hello {{state.name}}", "body": "Hi {{state.name}},\nyour order shipped.", "format": "text", "output_field": "sent", **extra}
    return {"name": f"mail {uuid.uuid4().hex[:4]}", "state": copy.deepcopy(STATE), "nodes": [N("s", "start"), {"id": "m", "type": "email", "data": d}, N("e", "end")],
            "edges": [E("1", "s", "m"), E("2", "m", "e")]}


@pytest.fixture
def server(monkeypatch):
    """A local SMTP server that signs in mail@acme.test with PASSWORD (no TLS)."""
    got = []
    class Handler:
        async def handle_DATA(self, srv, session, envelope): got.append(envelope); return "250 OK"
    def auth(srv, session, envelope, mechanism, data):
        ok = data.login == b"mail@acme.test" and data.password == PASSWORD.encode()
        return AuthResult(success=ok, handled=False)  # handled=False: the server answers 535 itself
    port = free_port()
    ctl = Controller(Handler(), hostname="127.0.0.1", port=port, authenticator=auth, auth_required=True, auth_require_tls=False)
    ctl.start(); monkeypatch.setenv("STUDIO_SMTP_ALLOW_PRIVATE", "1")
    yield {"port": port, "got": got}
    ctl.stop()


def settings(port, **kw):
    return {"host": "127.0.0.1", "port": port, "security": "none", "username": "mail@acme.test", "from_email": "mail@acme.test", "from_name": "Acme Support", **kw}


def cred(tok, port, password=PASSWORD, **kw):
    r = c.post("/api/credentials", json={"name": "Mail", "provider": "smtp", "api_key": password, "settings": settings(port, **kw)}, headers=H(tok)).json()
    return r["data"]["id"]


def run_ws(tok, wid, inp):
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": inp}); evs = []
        while True:
            evs.append(ws.receive_json())
            if evs[-1]["type"] in ("run_finished", "error"): return evs


INPUT = {"email": "ann@example.com", "name": "Ann <b>", "emails": [], "sent": {}}


# ---------- dry run ----------
def test_dry_run_without_a_credential_sends_nothing():
    evs = list(run_stream(flow(format="html", body="<p>Hi {{state.name}}</p><p>Bye</p>"), INPUT))
    out = evs[-1]["state"]["sent"]
    assert evs[-1]["type"] == "run_finished" and out["dry_run"] is True and out["sent"] is False and out["message_id"] is None
    assert out["to"] == ["ann@example.com"] and out["cc"] == ["boss@acme.test"] and out["bcc"] == ["audit@acme.test"]
    assert out["subject"] == "Hello Ann <b>" and out["preview"] == "Hi Ann <b>\nBye"  # HTML escaped, then shown as text


def test_build_escapes_html_and_reads_list_recipients():
    m = emails.build("m", flow(to="{{state.emails}}", format="html", body="<b>{{state.name}}</b>")["nodes"][1]["data"],
                     {**INPUT, "emails": ["a@x.io", "B <b@y.io>"]})
    assert m["to"] == ["a@x.io", "b@y.io"] and m["html"] == "<b>Ann &lt;b&gt;</b>" and m["text"] == "Ann <b>"
    assert m["recipients"] == ["a@x.io", "b@y.io", "boss@acme.test", "audit@acme.test"]
    with pytest.raises(Exception) as e: emails.build("m", flow(to="{{state.email}}")["nodes"][1]["data"], {**INPUT, "email": "not-mail"})
    assert e.value.code == "EMAIL_RECIPIENT_INVALID"
    with pytest.raises(Exception) as e: emails.build("m", flow(to="{{state.emails}}", cc="", bcc="")["nodes"][1]["data"], {**INPUT, "emails": []})
    assert e.value.code == "EMAIL_RECIPIENTS_MISSING"


# ---------- SMTP credentials ----------
def test_credential_keeps_settings_and_hides_the_password(server):
    t = user()
    cid = cred(t, server["port"])
    [row] = [x for x in c.get("/api/credentials", headers=H(t)).json()["data"] if x["id"] == cid]
    assert row["provider"] == "smtp" and row["settings"]["host"] == "127.0.0.1" and row["settings"]["from_name"] == "Acme Support" and row["base_url"] is None
    assert PASSWORD not in str(row) and row["hint"].endswith(PASSWORD[-4:])
    r = c.put(f"/api/credentials/{cid}", json={"name": "Mail 2", "settings": settings(2525)}, headers=H(t)).json()["data"]
    assert r["settings"]["port"] == 2525 and r["hint"] == row["hint"]  # the password is kept
    r = c.put(f"/api/credentials/{cid}", json={"name": "Mail 3"}, headers=H(t)).json()["data"]
    assert r["settings"]["port"] == 2525  # settings left out are kept
    bad = c.post("/api/credentials", json={"name": "x", "provider": "smtp", "settings": settings(1, from_email="nope")}, headers=H(t)).json()
    assert bad["error"]["code"] == "CREDENTIAL_SETTINGS_INVALID" and bad["error"]["details"] == {"field": "from_email"}
    info = {p["id"]: p for p in c.get("/api/providers", headers=H(t)).json()["data"]}
    assert info["smtp"]["kind"] == "email" and "host" in info["smtp"]["settings_fields"] and info["smtp"]["supports_embeddings"] is False


def test_connection_check_signs_in_without_sending(server, monkeypatch):
    t = user()
    probe = lambda pw, **kw: c.post("/api/providers/smtp/test", json={"api_key": pw, "settings": settings(server["port"], **kw)}, headers=H(t)).json()
    assert probe(PASSWORD)["data"]["ok"] is True and server["got"] == []
    r = probe("wrong")["error"]; assert r["code"] == "EMAIL_AUTH_FAILED" and "535" in r["message"]
    r = probe(PASSWORD, security="starttls")["error"]; assert r["code"] == "EMAIL_SEND_FAILED" and "STARTTLS" in r["message"]
    monkeypatch.delenv("STUDIO_SMTP_ALLOW_PRIVATE")
    assert probe(PASSWORD)["error"]["code"] == "EMAIL_HOST_BLOCKED"


# ---------- sending ----------
def test_run_sends_one_message_with_cc_bcc_and_reply_to(server):
    t = user(); cid = cred(t, server["port"])
    wid = c.post("/api/workflows", json=flow(credential_id=cid, format="html", body="<p>Hi {{state.name}}</p>"), headers=H(t)).json()["data"]["id"]
    evs = run_ws(t, wid, INPUT)
    assert evs[-1]["type"] == "run_finished", evs[-1]
    out = evs[-1]["state"]["sent"]; [env] = server["got"]
    assert out["sent"] is True and out["refused"] == [] and out["message_id"].startswith("<studio-") and out["message_id"].endswith("@acme.test>")
    assert env.mail_from == "mail@acme.test" and env.rcpt_tos == ["ann@example.com", "boss@acme.test", "audit@acme.test"]
    msg = email.message_from_bytes(env.content, policy=policy.default)
    assert msg["From"] == "Acme Support <mail@acme.test>" and msg["To"] == "ann@example.com" and msg["Cc"] == "boss@acme.test"
    assert msg["Bcc"] is None and msg["Reply-To"] == "help@acme.test" and msg["Subject"] == "Hello Ann <b>" and msg["Message-ID"] == out["message_id"]
    assert msg.get_body(("html",)).get_content().strip() == "<p>Hi Ann &lt;b&gt;</p>" and msg.get_body(("plain",)).get_content().strip() == "Hi Ann <b>"
    assert PASSWORD not in str(evs)


def test_a_recovered_run_does_not_send_again(server):
    class Ledger(dict):
        def get(self, nid, it): return super().get((nid, it))
        def put(self, nid, it, delta, key): self[(nid, it)] = delta
    led = Ledger()
    s = {"provider": "smtp", "api_key": PASSWORD, "settings": settings(server["port"])}
    wf = flow(credential_id="c1")
    for _ in range(2): list(run_stream(wf, INPUT, resolve=lambda cid: s, effects=Effects(run_id="r1", ledger=led)))  # the job runs again
    assert len(server["got"]) == 1 and led[("m", 1)]["sent"]["sent"] is True


def test_wrong_credential_kind_and_hourly_quota(server, monkeypatch):
    t = user()
    oai = c.post("/api/credentials", json={"name": "oai", "provider": "openai", "api_key": "sk-x"}, headers=H(t)).json()["data"]["id"]
    wid = c.post("/api/workflows", json=flow(credential_id=oai), headers=H(t)).json()["data"]["id"]
    assert run_ws(t, wid, INPUT)[-1]["error"]["code"] == "EMAIL_CREDENTIAL_INVALID"
    monkeypatch.setenv("STUDIO_EMAIL_NODE_HOURLY_LIMIT", "4")  # one run reaches 3 recipients
    wid = c.post("/api/workflows", json=flow(credential_id=cred(t, server["port"])), headers=H(t)).json()["data"]["id"]
    assert run_ws(t, wid, INPUT)[-1]["type"] == "run_finished"
    ev = run_ws(t, wid, INPUT)[-1]
    assert ev["error"]["code"] == "EMAIL_RATE_LIMITED" and len(server["got"]) == 1


# ---------- validation ----------
def test_valid_flow():
    assert validate(flow()) == []


@pytest.mark.parametrize("patch,frag", [
    ({"to": "", "cc": "", "bcc": ""}, "add a recipient"),
    ({"to": "ann@example.com, nope"}, "'nope' in to is not an e-mail address"),
    ({"reply_to": "x@"}, "in reply_to is not an e-mail address"),
    ({"to": ", ".join(f"u{i}@x.io" for i in range(51))}, "at most 50 recipients"),
    ({"subject": " "}, "the subject is empty"),
    ({"body": ""}, "the message is empty"),
    ({"format": "markdown"}, "format must be text or html"),
    ({"output_field": "name"}, "output_field 'name' must be of type object"),
    ({"subject": "{{state.ghost}}"}, "state.ghost"),
    ({"retry": {"max_attempts": 3}}, "retry and cache are not available"),
    ({"cache_ttl": 60}, "retry and cache are not available"),
])
def test_validation_errors(patch, frag):
    errs = validate(flow(**patch)); assert any(frag in e for e in errs), errs


def test_addresses_and_text_part():
    assert smtp.addresses("a@x.io; B <b@y.io>\n c@z.io,,") == ["a@x.io", "b@y.io", "c@z.io"]
    assert smtp.invalid(smtp.addresses("a@x.io, broken")) == ["broken"]
    assert emails.to_text("<style>p{}</style><h1>Hi</h1><ul><li>one</li><li>two</li></ul>a<br>b &amp; c") == "Hi\n- one\n- two\na\nb & c"
