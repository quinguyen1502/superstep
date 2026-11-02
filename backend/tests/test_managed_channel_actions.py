"""Existing channels as managed tools: fixed sends, shared policy/quota, no ambiguous resends."""
import json, uuid
import httpx, pytest
from app.api.deps import mcp_service, get_db, run_service
from app.core.errors import AppError
from app.services.approval_channels import links
from app.services.managed_tools import channel_actions as actions
from tests.test_chat_trigger_runs import c, api, user, H
from tests.test_more_channels import WA
from tests.test_managed_http_api import error

SETTINGS = {"slack": {"destination_channel": "C123TEST"}, "whatsapp": {"recipient_phone": "84901234567"},
            "email": {"recipients": "one@example.test,two@example.test"}, "teams": {}}


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.fixture.test"); monkeypatch.setenv("SMTP_FROM", "sender@example.test")
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.example.test")
    monkeypatch.setattr(links, "public_address", lambda url, *a, **kw: (url, "93.184.216.34"))


@pytest.fixture
def remote(monkeypatch):
    state = {"calls": [], "emails": [], "mode": "ok", "status": 200}
    def request(method, url, **kwargs):
        state["calls"].append((method, url, kwargs))
        if state["mode"] == "timeout": raise httpx.ReadTimeout("fixture-token-must-not-leak")
        if state["mode"] == "malformed": return httpx.Response(200, json={})
        if state["status"] != 200: return httpx.Response(state["status"], json={"error": "fixture-token-must-not-leak"})
        if url.endswith("chat.postMessage"):
            if state["mode"] == "reject": return httpx.Response(200, json={"ok": False, "error": "not_in_channel"})
            if state["mode"] == "internal": return httpx.Response(200, json={"ok": False, "error": "internal_error"})
            return httpx.Response(200, json={"ok": True, "channel": kwargs["json"]["channel"], "ts": "1793557800.123456"})
        if url.endswith("/messages"): return httpx.Response(200, json={"messages": [{"id": "wamid.fixture"}]})
        return httpx.Response(202)  # Teams acknowledges submission, not delivery
    def deliver(server, message, recipients):
        state["emails"].append((server, message, recipients))
        if state["mode"] == "timeout": raise AppError("EMAIL_SEND_FAILED", reason="fixture-token-must-not-leak")
        if state["mode"] == "auth": raise AppError("EMAIL_AUTH_FAILED", reason="fixture-token-must-not-leak")
        return recipients[:1] if state["mode"] == "partial" else []
    monkeypatch.setattr(actions, "request", request); monkeypatch.setattr(actions.smtp, "deliver", deliver)
    return state


def channel(c, owner, kind):
    secrets = {"slack": {"bot_token": f"xoxb-1-T{uuid.uuid4().hex[:6].upper()}-fixture-token", "signing_secret": "a" * 32},
        "whatsapp": WA, "email": {}, "teams": {"webhook_url": "https://teams.webhook.test/fixture-secret-path"}}[kind]
    response = c.post("/api/approvals/channels", headers=H(owner["token"]), json={"kind": kind, **secrets})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create(c, owner, kind, source=None, settings=None, **extra):
    source = source or channel(c, owner, kind)
    response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": kind + uuid.uuid4().hex[:6], "transport": "managed", "adapter": kind,
        "settings": {"channel_id": source["id"], **(SETTINGS[kind] if settings is None else settings)}, **extra})
    return response


@pytest.mark.parametrize("kind", ["slack", "whatsapp", "email", "teams"])
def test_discovery_fixed_payload_encrypted_channel_secrets_known_replay_and_dry_run(c, remote, kind):
    owner = user(c); response = create(c, owner, kind); assert response.status_code == 200, response.text
    server = response.json()["data"]; svc = mcp_service(); sid = server["id"]
    tools = svc.discover(sid, owner["id"])["tools"]; name = "send_email" if kind == "email" else "send_message"
    assert tools[0]["name"] == name and not remote["calls"] and not remote["emails"]
    args = {"text": "Hello <@everyone> & example"}
    if kind == "email": args["subject"] = "Report\r\nBcc: injected@example.test"
    if kind == "slack": args["thread_ts"] = "1793557800.1"
    assert svc.call(owner["id"], sid, name, args, dry_run=True)["outcome"] == "dry_run"
    assert not remote["calls"] and not remote["emails"] and not svc.operations(owner["id"], sid)
    result = svc.call(owner["id"], sid, name, args, operation_key="confirmed")
    assert result["outcome"] == "confirmed" and result["delivery"] == "accepted"
    assert svc.call(owner["id"], sid, name, args, operation_key="confirmed") == result
    assert len(remote["emails"] if kind == "email" else remote["calls"]) == 1
    assert "fixture-secret-path" not in json.dumps(result) and "access_token" not in json.dumps(server)
    if kind == "slack":
        _, url, options = remote["calls"][0]
        assert url.endswith("/chat.postMessage") and options["headers"]["Authorization"].startswith("Bearer xoxb-")
        assert options["json"]["channel"] == "C123TEST" and options["json"]["thread_ts"] == "1793557800.1"
        assert options["json"]["text"] == "Hello &lt;@everyone&gt; &amp; example" and options["json"]["mrkdwn"] is False
    elif kind == "whatsapp":
        _, url, options = remote["calls"][0]
        assert url.endswith(f"/{WA['phone_number_id']}/messages") and options["headers"]["Authorization"] == "Bearer " + WA["access_token"]
        assert options["json"] == {"messaging_product": "whatsapp", "to": "84901234567", "type": "text", "text": {"body": args["text"], "preview_url": False}}
    elif kind == "email":
        server, message, recipients = remote["emails"][0]
        assert recipients == ["one@example.test", "two@example.test"] and server["sender"] == "sender@example.test"
        assert message["Bcc"] is None and "\n" not in str(message["Subject"]) and message["Message-ID"] == result["message_id"]
        assert str(message["Message-ID"]).endswith("@example.test>")
    else:
        payload = remote["calls"][0][2]["json"]
        assert payload["attachments"][0]["content"]["body"][0]["text"] == args["text"]
        assert "actions" not in payload["attachments"][0]["content"]
    with error("MCP_ARGUMENT_INVALID"): svc.call(owner["id"], sid, name, {**args, "to": "another-target"}, operation_key="forged")


@pytest.mark.parametrize("kind", ["slack", "whatsapp", "email", "teams"])
def test_lost_response_and_manual_check_never_resend(c, remote, kind):
    owner = user(c); server = create(c, owner, kind).json()["data"]; svc = mcp_service(); remote["mode"] = "timeout"
    for _ in range(2):
        with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], server["id"], "send_email" if kind == "email" else "send_message", {"text": "hello"}, operation_key="unknown")
    [operation] = svc.operations(owner["id"], server["id"])
    with error("MANAGED_OUTCOME_UNKNOWN"): svc.reconcile(owner["id"], server["id"], operation["operation_id"])
    assert len(remote["emails"] if kind == "email" else remote["calls"]) == 1
    assert "fixture-token-must-not-leak" not in json.dumps(operation)


@pytest.mark.parametrize("kind", ["slack", "whatsapp", "email", "teams"])
def test_personal_scope_and_indirect_org_policy_shared_with_telegram(c, remote, monkeypatch, kind):
    owner, stranger = user(c), user(c); source = channel(c, owner, kind)
    assert create(c, stranger, kind, source).json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    server = create(c, owner, kind, source).json()["data"]; svc = mcp_service(); adapter = svc.managed.adapter(kind); channels = adapter.channels
    with error("MCP_SERVER_NOT_FOUND"): svc.call(stranger["id"], server["id"], "send_email" if kind == "email" else "send_message", {"text": "x"}, operation_key="denied")
    row = channels.repo.channel(source["id"]); row.scope = "org"; channels.repo.save_channel(row)
    try:
        with error("CHANNEL_NOT_FOUND"): svc.call(owner["id"], server["id"], "send_email" if kind == "email" else "send_message", {"text": "x"}, org_allowed=False, operation_key="org-policy")
        monkeypatch.setattr(channels, "org_allowed", lambda uid: False)
        with error("CHANNEL_NOT_FOUND"): adapter.authorize(owner["id"], server["settings"])
    finally:
        row.scope = "user"; channels.repo.save_channel(row)
    assert not remote["calls"] and not remote["emails"]


@pytest.mark.parametrize("kind,settings", [("slack", {"destination_channel": "https://other.test"}), ("whatsapp", {"recipient_phone": "+84901234567"}),
    ("email", {"recipients": "invalid"}), ("email", {"recipients": "one@example.test\r\nBcc: bad@example.test"}), ("teams", {"webhook_url": "https://another.test"})])
def test_targets_are_reviewed_and_channel_kinds_cannot_be_swapped(c, remote, kind, settings):
    owner = user(c)
    assert create(c, owner, kind, settings=settings).json()["error"]["code"] == "MCP_CONFIG_INVALID"
    wrong = channel(c, owner, "email" if kind != "email" else "slack")
    assert create(c, owner, kind, source=wrong).json()["error"]["code"] == "CHANNEL_NOT_FOUND"


def test_provider_rejections_malformed_and_partial_smtp(c, remote):
    owner = user(c); svc = mcp_service(); server = create(c, owner, "slack").json()["data"]
    for mode, code in [("reject", "MCP_TOOL_FAILED"), ("internal", "MANAGED_OUTCOME_UNKNOWN"), ("malformed", "MANAGED_OUTCOME_UNKNOWN")]:
        remote["mode"] = mode
        with error(code): svc.call(owner["id"], server["id"], "send_message", {"text": "hello"}, operation_key=mode)
    remote["mode"] = "ok"
    for kind in ["slack", "whatsapp", "teams"]:
        server = create(c, owner, kind).json()["data"]
        for status, code in [(403, "MCP_TOOL_FAILED"), (503, "MANAGED_OUTCOME_UNKNOWN")]:
            remote["status"] = status
            with error(code): svc.call(owner["id"], server["id"], "send_message", {"text": "hello"}, operation_key=str(status))
    server = create(c, owner, "email").json()["data"]
    for mode, code in [("auth", "MCP_TOOL_FAILED"), ("partial", "MANAGED_OUTCOME_UNKNOWN")]:
        remote["mode"] = mode
        for _ in range(2):
            with error(code): svc.call(owner["id"], server["id"], "send_email", {"text": "hello"}, operation_key=mode)
    assert len(remote["emails"]) == 2


def test_email_shares_workflow_quota_without_charging_replay_or_dry_run(c, remote, monkeypatch):
    monkeypatch.setenv("STUDIO_EMAIL_NODE_HOURLY_LIMIT", "3")
    owner = user(c); svc = mcp_service(); server = create(c, owner, "email").json()["data"]
    run_service().email_quota(owner["id"])(1)  # same owner/key as existing Send email nodes
    args = {"text": "budget"}
    svc.call(owner["id"], server["id"], "send_email", args, dry_run=True)
    svc.call(owner["id"], server["id"], "send_email", args, operation_key="first")
    svc.call(owner["id"], server["id"], "send_email", args, operation_key="first")
    with error("EMAIL_RATE_LIMITED"): svc.call(owner["id"], server["id"], "send_email", args, operation_key="next")
    assert len(remote["emails"]) == 1


def test_removed_channel_and_malformed_whatsapp_cannot_confirm(c, remote):
    owner = user(c); svc = mcp_service(); source = channel(c, owner, "slack")
    server = create(c, owner, "slack", source).json()["data"]
    assert c.delete(f"/api/approvals/channels/{source['id']}", headers=H(owner["token"])).status_code == 200
    with error("CHANNEL_NOT_FOUND"): svc.call(owner["id"], server["id"], "send_message", {"text": "hello"}, operation_key="removed")
    assert not remote["calls"]
    server = create(c, owner, "whatsapp").json()["data"]; remote["mode"] = "malformed"
    for _ in range(2):
        with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], server["id"], "send_message", {"text": "hello"}, operation_key="invalid-response")
    assert len(remote["calls"]) == 1


def test_invalid_channel_reference_is_a_domain_error(c):
    owner = user(c)
    for value in ({"id": "not-a-resource"}, ["not-a-resource"], None):
        response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "Invalid channel", "transport": "managed", "adapter": "teams", "settings": {"channel_id": value}})
        assert response.status_code == 404 and response.json()["error"]["code"] == "CHANNEL_NOT_FOUND"
