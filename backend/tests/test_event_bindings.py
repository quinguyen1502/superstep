"""Authenticated generic event admission, metadata mapping and atomic duplicate delivery handling."""
import copy, json, time, uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.api.deps import approval_service, chat_run_service
from app.services.webhooks import sign
from app.services.approval_channels import ADAPTERS
from tests.test_chat_trigger_runs import c, api, user, H, ECHO, TG, runs_of, until

SECRET = "fixture-only-signing-secret-0123456789"


def setup(c, kind="telegram", **policy):
    owner = user(c)
    graph = copy.deepcopy(ECHO)
    graph["name"] = "Event " + uuid.uuid4().hex[:8]
    graph["state"] += [{"name": "context", "type": "object"}, {"name": "message_id", "type": "integer"}]
    wid = c.post("/api/workflows", headers=H(owner["token"]), json=graph).json()["data"]["id"]
    channel = c.post("/api/approvals/channels", headers=H(owner["token"]),
                     json={"kind": kind, **(TG if kind == "telegram" else {"signing_secret": SECRET})}).json()["data"]
    url = f"/api/workflows/{wid}/chat-triggers"
    event = {"senders": ["42"], "type": "message.text", "mapping": {"message": "data.text", "context": "$"}, **policy}
    response = c.post(url, headers=H(owner["token"]), json={"channel_id": channel["id"], "place": "-100123", "event": event})
    assert response.status_code == 200, response.text
    return owner, wid, channel, response.json()["data"], url


def payload(**overrides):
    return {"update_id": int(uuid.uuid4().hex[:12], 16), "message": {"message_id": 101, "date": 1700000000,
        "from": {"id": 42, "first_name": "Example", "last_name": "Sender"}, "chat": {"id": -100123, "type": "supergroup"},
        "text": "Lunch 50000", **overrides}}


def post(c, channel, data, secret=None):
    if channel["kind"] == "telegram":
        return c.post(channel["callback_path"], json=data, headers={"X-Telegram-Bot-Api-Secret-Token": secret or TG["webhook_secret"]})
    raw = json.dumps(data).encode()
    return c.post(channel["callback_path"], content=raw, headers={"Content-Type": "application/json", "X-Studio-Signature": sign(secret or SECRET, raw)})


def test_telegram_plain_text_metadata_owner_run_and_no_automatic_reply(c, api):
    owner, wid, ch, binding, url = setup(c, mapping={"message": "data.text", "context": "$", "message_id": "data.message_id"})
    assert binding["command"] == "*" and binding["event"]["senders"] == ["42"]
    message = payload()
    assert post(c, ch, message).json()["data"] == {"outcome": "queued"}
    until(lambda: runs_of(wid) and runs_of(wid)[0].status == "ok")
    [run] = runs_of(wid); data = json.loads(run.input)
    assert run.owner == owner["id"] and data["message_id"] == 101
    assert data["message"] == "Lunch 50000"
    assert data["context"] == {"id": str(message["update_id"]), "source": "telegram", "type": "message.text",
        "time": "2023-11-14T22:13:20+00:00", "actor": {"id": "42", "name": "Example Sender"},
        "conversation": {"id": "-100123"}, "data": {"text": "Lunch 50000", "message_id": 101}}
    assert not api.sent("sendMessage")
    assert c.patch(f"{url}/{binding['id']}", headers=H(owner["token"]), json={"enabled": False}).json()["data"]["event"] == binding["event"]
    assert post(c, ch, payload()).json()["data"]["outcome"] == "ignored"
    assert len(runs_of(wid)) == 1


def test_wrong_admission_signature_missing_identity_and_oversize_start_nothing(c, monkeypatch):
    owner, wid, ch, binding, url = setup(c)
    assert post(c, ch, payload(), secret="wrong").status_code == 401
    for message in [payload(**{"from": {"id": 99}}), payload(chat={"id": -999, "type": "group"}),
                    payload(**{"from": {"id": 42, "is_bot": True}}), payload(date=None), payload(date=1e100),
                    {"edited_message": payload()["message"]}, {"message": payload()["message"]}]:
        assert post(c, ch, message).json()["data"]["outcome"] == "ignored"
    monkeypatch.setenv("STUDIO_INPUT_MAX_BYTES", "100")
    assert post(c, ch, payload(text="x" * 10000)).json()["data"]["outcome"] == "ignored"
    assert not runs_of(wid)


def test_signed_json_uses_same_envelope_and_typed_mapping(c):
    owner, wid, ch, binding, url = setup(c, "webhook")
    assert ch["events_only"] and approval_service().channels.for_node(owner["id"], {"channel_id": ch["id"]}) is None
    event = {"id": uuid.uuid4().hex, "type": "message.text", "time": "2026-11-01T10:00:00+07:00", "place": "-100123", "sender": "42", "data": {"text": "hello"}}
    assert post(c, ch, event, secret="wrong").status_code == 401
    for signature in ["garbage", "t=123,v1", sign(SECRET, json.dumps(event).encode(), ts=int(time.time()) - 3600)]:
        assert c.post(ch["callback_path"], content=json.dumps(event), headers={"X-Studio-Signature": signature}).status_code == 401
    for change in [{"type": "another.event"}, {"sender": "99"}, {"time": "yesterday"}, {"time": "2026-11-01T10:00:00"}, {"data": []}]:
        assert post(c, ch, {**event, **change}).json()["data"]["outcome"] == "ignored"
    assert post(c, ch, event).json()["data"]["outcome"] == "queued"
    assert post(c, ch, {**event, "data": {"text": "changed retry"}}).json()["data"]["outcome"] == "duplicate"
    until(lambda: runs_of(wid) and runs_of(wid)[0].status == "ok")
    [run] = runs_of(wid); inp = json.loads(run.input)
    assert inp["message"] == "hello" and inp["context"]["source"] == "webhook"
    assert inp["context"]["time"] == "2026-11-01T03:00:00+00:00"


def test_mapping_configuration_and_field_types_are_checked(c):
    owner, wid, ch, binding, url = setup(c)
    for change in [{"senders": []}, {"senders": ["*", "42"]}, {"mapping": {"not_declared": "data.text"}},
                   {"mapping": {"message": "data.x[0]"}}, {"mapping": {"message": "__class__"}}, {"type": ""}]:
        r = c.patch(f"{url}/{binding['id']}", headers=H(owner["token"]), json={"event": {**binding["event"], **change}})
        assert r.status_code == 400 and r.json()["error"]["code"] == "CHAT_TRIGGER_CONFIG_INVALID"
    for mapping in [{"message_id": "data.text"}, {"message": "data.missing"}]:
        assert c.patch(f"{url}/{binding['id']}", headers=H(owner["token"]), json={"event": {**binding["event"], "mapping": mapping}}).status_code == 200
        assert post(c, ch, payload()).json()["data"]["outcome"] == "ignored"
    assert not runs_of(wid)


def test_concurrent_delivery_creates_one_run_and_audit(c):
    owner, wid, ch, binding, url = setup(c)
    service = chat_run_service(); channel = service.channels.repo.channel(ch["id"])
    incoming = ADAPTERS["telegram"].handle_message(json.dumps(payload()).encode())
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: service.receive([(channel, TG)], incoming), range(16)))
    assert sum(v["outcome"] == "queued" for v in outcomes) == 1
    until(lambda: runs_of(wid) and runs_of(wid)[0].status == "ok")
    assert len(runs_of(wid)) == 1
    audits = c.get("/api/approvals/audit", headers=H(owner["token"])).json()["data"]
    assert len([a for a in audits if a["action"] == "event_started"]) == 1


def test_queue_failure_retry_reuses_original_persisted_input(c, monkeypatch):
    owner, wid, ch, binding, url = setup(c)
    svc = chat_run_service(); message = payload()
    original = svc.jobs.enqueue
    def fail(_): raise RuntimeError("simulated queue failure after commit")
    monkeypatch.setattr(svc.jobs, "enqueue", fail)
    with pytest.raises(RuntimeError, match="queue failure"): post(c, ch, message)
    [run] = runs_of(wid); assert run.status == "queued"
    monkeypatch.setattr(svc.jobs, "enqueue", original)
    message["message"]["text"] = "changed redelivery"
    assert post(c, ch, message).json()["data"]["outcome"] == "duplicate"
    until(lambda: runs_of(wid)[0].status == "ok")
    assert len(runs_of(wid)) == 1 and json.loads(runs_of(wid)[0].input)["message"] == "Lunch 50000"


def test_other_owner_cannot_bind_personal_source_or_edit_binding(c):
    owner, wid, ch, binding, url = setup(c)
    stranger = user(c)
    assert c.patch(f"{url}/{binding['id']}", headers=H(stranger["token"]), json={"enabled": False}).status_code == 404
    other_wid = c.post("/api/workflows", headers=H(stranger["token"]), json={**ECHO, "name": "Other event"}).json()["data"]["id"]
    assert c.post(f"/api/workflows/{other_wid}/chat-triggers", headers=H(stranger["token"]), json={"channel_id": ch["id"], "event": binding["event"]}).status_code == 404


def test_binding_stops_when_organisation_connection_policy_is_revoked(c, monkeypatch):
    owner, wid, ch, binding, url = setup(c)
    svc = chat_run_service(); channel = svc.channels.repo.channel(ch["id"])
    channel.scope = "org"; svc.channels.repo.save_channel(channel)
    monkeypatch.setattr(svc.channels, "org_allowed", lambda _: False)
    incoming = ADAPTERS["telegram"].handle_message(json.dumps(payload()).encode())
    assert svc.receive([(channel, TG)], incoming)["outcome"] == "ignored"
    assert not runs_of(wid)
    assert c.put("/api/approvals/identities", headers=H(owner["token"]), json={"kind": "webhook", "external_id": "42"}).status_code == 400
