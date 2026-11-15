"""chat trigger settings: rows per workflow, the management API, Slack scopes, Telegram webhook."""
import json, time, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service
from app.models import ApprovalChannel
from app.services.approval_channels import ADAPTERS

SIGNING = "0123456789abcdef0123456789abcdef"
ALL = "chat:write,chat:write.public,im:write,app_mentions:read,im:history"


class FakeApi:
    """Slack auth.test (scopes in the x-oauth-scopes header, team from the token xoxb-1111-<TEAM>-...) and Telegram."""
    def __init__(self): self.scopes = ALL; self.calls: list[tuple[str, dict]] = []
    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}"); self.calls.append((req.url.path, body))
        if req.url.path.endswith("auth.test"):
            team = req.headers["Authorization"].split("-")[2]
            return httpx.Response(200, json={"ok": True, "team": f"Team {team}", "team_id": team}, headers={"x-oauth-scopes": self.scopes} if self.scopes is not None else {})
        if req.url.path.endswith("getMe"): return httpx.Response(200, json={"ok": True, "result": {"id": 123456, "is_bot": True, "username": "studio_bot"}})
        return httpx.Response(200, json={"ok": True, "result": True})


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client

@pytest.fixture(autouse=True)
def api(monkeypatch):
    fake = FakeApi()
    for a in ADAPTERS.values(): monkeypatch.setattr(a, "transport", httpx.MockTransport(fake), raising=False)
    return fake

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c): return c.post("/api/auth/register", json={"email": f"ct{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]  # state: message, intent, tool_result, answer

def slack(c, tok, team=None):
    team = team or uuid.uuid4().hex[:8].upper()
    r = c.post("/api/approvals/channels", json={"kind": "slack", "bot_token": f"xoxb-1111-{team}-abcdefgh", "signing_secret": SIGNING}, headers=H(tok))
    return r.json()["data"]

def body(ch, **kw): return {"channel_id": ch["id"], "place": "dm", "command": "ask", "input_field": "message", "reply_field": "answer", **kw}
def err(r): return r.json()["error"]["code"]


def test_crud_and_validation(c):
    tok = user(c); wid = example(c, tok); ch = slack(c, tok); url = f"/api/workflows/{wid}/chat-triggers"
    assert ch["chat"] == {"missing_scopes": [], "events_path": "/api/channels/events/slack", "events_url": ch["chat"]["events_url"]}
    t = c.post(url, json=body(ch, command="/Ask", name=" Support "), headers=H(tok)).json()["data"]
    assert (t["command"], t["name"], t["kind"], t["channel_name"], t["enabled"], t["note"]) == ("ask", "Support", "slack", ch["name"], True, None)
    assert [x["id"] for x in c.get(url, headers=H(tok)).json()["data"]] == [t["id"]]
    # one trigger per connection, place and command; another place or command is fine
    r = c.post(url, json=body(ch), headers=H(tok)); assert r.status_code == 409 and err(r) == "CHAT_TRIGGER_COMMAND_TAKEN"
    assert c.post(url, json=body(ch, place="C0123HR"), headers=H(tok)).json()["data"]["place"] == "C0123HR"
    assert c.post(url, json=body(ch, command="ask-2", name=""), headers=H(tok)).json()["data"]["name"] == "ask-2"  # name defaults to the command
    for bad, field in [({"command": "two words"}, "command"), ({"command": "x" * 33}, "command"), ({"place": "general"}, "place"),
                       ({"input_field": "nope"}, "input_field"), ({"reply_field": "nope"}, "reply_field")]:
        r = c.post(url, json={**body(ch, command="other"), **bad}, headers=H(tok))
        assert r.status_code == 400 and err(r) == "CHAT_TRIGGER_CONFIG_INVALID" and r.json()["error"]["details"]["field"] == field, bad
    # edit: settings are checked again, a taken command is refused, turning on clears the note
    r = c.patch(f"{url}/{t['id']}", json={"command": "ask-2"}, headers=H(tok)); assert err(r) == "CHAT_TRIGGER_COMMAND_TAKEN"
    assert c.patch(f"{url}/{t['id']}", json={"enabled": False, "reply_field": "intent"}, headers=H(tok)).json()["data"]["enabled"] is False
    assert c.patch(f"{url}/{t['id']}", json={"enabled": True}, headers=H(tok)).json()["data"]["reply_field"] == "intent"
    assert c.delete(f"{url}/{t['id']}", headers=H(tok)).json()["data"] == {"ok": True}
    assert err(c.patch(f"{url}/{t['id']}", json={"enabled": True}, headers=H(tok))) == "CHAT_TRIGGER_NOT_FOUND"


def test_share_right_and_connections_the_user_may_use(c):
    tok, other = user(c), user(c); wid = example(c, tok); url = f"/api/workflows/{wid}/chat-triggers"
    mine, theirs = slack(c, tok), slack(c, other)
    t = c.post(url, json=body(mine), headers=H(tok)).json()["data"]
    assert err(c.get(url, headers=H(other))) == "WORKFLOW_NOT_FOUND"
    assert c.delete(f"{url}/{t['id']}", headers=H(other)).status_code == 404
    assert err(c.post(url, json=body(theirs, command="x"), headers=H(tok))) == "CHANNEL_NOT_FOUND"  # someone else's personal connection
    # a link channel (Teams) cannot start runs
    repo = approval_service().repo
    teams = repo.save_channel(ApprovalChannel(id=repo.new_id(), owner=repo.channel(mine["id"]).owner, kind="teams", scope="user",
                                              secrets="x", created=time.time()))
    r = c.post(url, json=body({"id": teams.id}, command="x"), headers=H(tok))
    assert err(r) == "CHAT_TRIGGER_CONFIG_INVALID" and r.json()["error"]["details"]["field"] == "channel_id"


def test_limit_per_workflow(c, monkeypatch):
    from app.services import chat_trigger_service as mod
    monkeypatch.setattr(mod, "MAX_PER_WORKFLOW", 2)
    tok = user(c); wid = example(c, tok); ch = slack(c, tok); url = f"/api/workflows/{wid}/chat-triggers"
    for i in range(2): c.post(url, json=body(ch, command=f"c{i}"), headers=H(tok))
    r = c.post(url, json=body(ch, command="c3"), headers=H(tok))
    assert err(r) == "CHAT_TRIGGER_LIMIT" and r.json()["error"]["details"]["max"] == 2


def test_deleting_the_connection_stops_and_deleting_the_workflow_removes(c):
    tok = user(c); wid = example(c, tok); ch = slack(c, tok); url = f"/api/workflows/{wid}/chat-triggers"
    t = c.post(url, json=body(ch), headers=H(tok)).json()["data"]
    c.delete(f"/api/approvals/channels/{ch['id']}", headers=H(tok))
    got = c.get(url, headers=H(tok)).json()["data"][0]
    assert (got["enabled"], got["note"], got["kind"]) == (False, "channel", None)
    assert err(c.patch(f"{url}/{t['id']}", json={"enabled": True}, headers=H(tok))) == "CHANNEL_NOT_FOUND"  # cannot turn on without a connection
    c.delete(f"/api/workflows/{wid}", headers=H(tok))
    from app.api.deps import chat_trigger_service
    assert chat_trigger_service().triggers.get(t["id"]) is None


def test_slack_scopes_are_read_and_checked(c, api):
    tok = user(c); wid = example(c, tok); url = f"/api/workflows/{wid}/chat-triggers"
    api.scopes = "chat:write,im:write"  # installed before chat triggers
    ch = slack(c, tok)
    assert ch["chat"]["missing_scopes"] == ["app_mentions:read", "im:history"]
    r = c.post(url, json=body(ch), headers=H(tok))
    assert err(r) == "CHAT_TRIGGER_SCOPE_MISSING" and "im:history" in r.json()["error"]["message"]
    assert c.post(url, json=body(ch, enabled=False), headers=H(tok)).json()["data"]["enabled"] is False  # may be saved off
    api.scopes = ALL  # reinstalled; Test reads the scopes again
    assert c.post(f"/api/approvals/channels/{ch['id']}/test", headers=H(tok)).json()["data"]["missing_scopes"] == []
    assert c.post(url, json=body(ch, command="ask-2"), headers=H(tok)).json()["data"]["enabled"] is True
    api.scopes = None  # no header: unknown, not refused
    ch2 = slack(c, tok)
    assert ch2["chat"]["missing_scopes"] is None and c.post(url, json=body(ch2), headers=H(tok)).json()["data"]["enabled"] is True


def test_telegram_webhook_asks_for_messages(c, api, monkeypatch):
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.example.com")
    tok = user(c); wid = example(c, tok)
    ch = c.post("/api/approvals/channels", json={"kind": "telegram", "bot_token": "123456:AAbbCCddEEffGGhhIIjjKKll"}, headers=H(tok)).json()["data"]
    assert ch["chat"] == {"missing_scopes": [], "events_path": None, "events_url": None}  # messages come to the callback URL
    c.post(f"/api/approvals/channels/{ch["id"]}/register-webhook", headers=H(tok))
    assert [b for p, b in api.calls if p.endswith("setWebhook")][-1]["allowed_updates"] == ["callback_query", "message"]
    t = c.post(f"/api/workflows/{wid}/chat-triggers", json=body(ch, place="-1001234567890"), headers=H(tok)).json()["data"]
    assert (t["kind"], t["place"]) == ("telegram", "-1001234567890")
    r = c.post(f"/api/workflows/{wid}/chat-triggers", json=body(ch, command="x", place="C0123"), headers=H(tok))
    assert r.json()["error"]["details"]["field"] == "place"
