"""The exact portable expense template through authenticated input, real Code runner and managed actions."""
import json, uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx, pytest
from app.api.deps import run_service, mcp_service, get_db
from app.engine import nodes
from app.engine.effects import Effects
from app.engine.providers import ProviderError
from app.engine.runtime import run_stream
from app.engine.templates import problems, sanitize
from app.engine.validator import validate
from app.repositories import NodeResultRepository, UserRepository
from app.services.managed_tools import sheets
from tests.test_managed_tools import c, api, account, external, create, user, H, TG
from tests.test_chat_trigger_runs import until, runs_of

FILE = Path(__file__).resolve().parents[2] / "examples/telegram-expenses.template.json"
VALID = {"is_expense": True, "amount": 50000, "description": "Lunch", "category": "Food", "expense_date": "2026-10-31"}


@pytest.fixture(autouse=True)
def runtime(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1")
    monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    monkeypatch.setenv("STUDIO_CODE_LANGUAGES", "python")
    monkeypatch.setenv("STUDIO_CODE_NO_NETWORK", "1")


@pytest.fixture
def model(monkeypatch):
    scenario = {"response": json.dumps(VALID, ensure_ascii=False), "primary_error": False, "backup_error": False, "calls": []}
    def invoke(prompt, name, credential, on_usage=None, on_token=None, **kwargs):
        scenario["calls"].append((name, credential["provider"]))
        failed = scenario["backup_error"] if credential["provider"] == "ollama" else scenario["primary_error"]
        if failed: raise ProviderError("PROVIDER_UNREACHABLE", credential["provider"])
        return scenario["response"]
    monkeypatch.setattr(nodes, "call_llm", invoke)
    return scenario


def setup(c, account):
    owner = user(c)
    UserRepository(get_db()).set_admin(owner["id"])  # importing the reviewed Code template requires code.write
    telegram = create(c, owner)
    google = create(c, owner, account, settings={"spreadsheet_id": "fixture-expenses-123", "sheet_name": "Expenses", "data_columns": 7})
    policy = {}
    for role, provider in (("primary", "openrouter"), ("backup", "ollama")):
        response = c.post("/api/credentials", headers=H(owner["token"]), json={"name": role + uuid.uuid4().hex[:6], "provider": provider, "api_key": "fixture-only-model-key" if provider == "openrouter" else ""})
        assert response.status_code == 200, response.text
        policy[role] = response.json()["data"]["id"]
    payload = json.loads(FILE.read_text())
    imported = c.post("/api/templates/import", headers=H(owner["token"]), json={"file": payload})
    assert imported.status_code == 200, imported.text
    tid = imported.json()["data"]["id"]
    made = c.post(f"/api/templates/{tid}/use", headers=H(owner["token"]), json={"name": "Expense " + uuid.uuid4().hex[:8]}).json()["data"]
    wid = made["id"]
    graph = c.get(f"/api/workflows/{wid}", headers=H(owner["token"])).json()["data"]
    for node in graph["nodes"]:
        data = node["data"]
        if node["type"] == "mcp": data["server_id"] = google["id"] if data["tool"] == "append_row" else telegram["id"]
        if node["type"] == "llm":
            data["credential_id"] = policy["primary"]
            data["fallback"]["credential_id"] = policy["backup"]
    assert not validate(graph), validate(graph)
    saved = c.post("/api/workflows", headers=H(owner["token"]), json=graph)
    assert saved.status_code == 200, saved.text
    trigger = c.post(f"/api/workflows/{wid}/chat-triggers", headers=H(owner["token"]), json={
        "name": "Expense messages", "channel_id": telegram["settings"]["channel_id"], "place": "-100123",
        "event": {"senders": ["42"], "type": "message.text", "mapping": {"message": "data.text", "context": "$"}},
    })
    assert trigger.status_code == 200, trigger.text
    return owner, wid, telegram, google, graph


def deliver(c, telegram, message="Lunch 50000 on 2026-10-31", event_id=None):
    body = {"update_id": event_id or int(uuid.uuid4().hex[:12], 16), "message": {
        "message_id": 101, "date": int(datetime(2026, 11, 1, 18, 30, tzinfo=timezone.utc).timestamp()),
        "from": {"id": 42, "first_name": "Sample employee"}, "chat": {"id": -100123, "type": "supergroup"}, "text": message}}
    response = c.post(f"/api/approvals/callback/telegram/{telegram['settings']['channel_id']}", json=body,
                      headers={"X-Telegram-Bot-Api-Secret-Token": TG["webhook_secret"]})
    assert response.status_code == 200, response.text
    return response.json()["data"]["outcome"]


def settled(wid):
    return until(lambda: next((run for run in runs_of(wid) if run.status in ("ok", "error")), None), timeout=20)


def test_exact_template_valid_expense_date_metadata_duplicate_and_worker_replay(c, external, account, model):
    owner, wid, telegram, google, graph = setup(c, account)
    assert deliver(c, telegram, event_id=10101) == "queued"
    run = settled(wid)
    assert run.status == "ok", run.events
    assert external.rows[0][:7] == ["2026-10-31", "Sample employee", "Lunch", "Food", 50000, "Pending approval", "2026-11-02T01:30:00+07:00"]
    assert len(external.rows[0]) == 8 and len(external.messages) == 2
    assert external.messages[0]["text"].startswith("Processing your expense")
    assert external.messages[1]["text"].startswith("Recorded expense")
    append_index = next(i for i, call in enumerate(external.calls) if call[1].endswith(":append"))
    reply_indices = [i for i, call in enumerate(external.calls) if call[1].endswith("/sendMessage")]
    assert reply_indices[0] < append_index < reply_indices[1]
    assert deliver(c, telegram, event_id=10101) == "duplicate" and len(runs_of(wid)) == 1
    before = len(external.calls)
    service = run_service()
    assert not NodeResultRepository(get_db()).for_run(run.id)  # completed runs purge the transient node cache
    replay = list(run_stream(graph, json.loads(run.input), resolve=service.credentials.resolver(owner["id"]),
        ports=service.ports(owner["id"]), effects=Effects(run.id)))
    assert replay[-1]["type"] == "run_finished"
    assert len(external.calls) == before and len(external.rows) == 1  # durable tool intents still prevent duplicate writes


@pytest.mark.parametrize("amount", [None, 0, -1, "50000", True, 0.5, 1000000000001])
def test_invalid_or_missing_amount_never_writes(c, external, account, model, amount):
    model["response"] = json.dumps({**VALID, "amount": amount})
    owner, wid, telegram, google, graph = setup(c, account)
    assert deliver(c, telegram) == "queued"
    assert settled(wid).status == "ok"
    assert not external.rows and len(external.messages) == 2
    assert external.messages[-1]["text"].startswith("Please")
    assert not any(message["text"].startswith("Recorded") for message in external.messages)


def test_unrelated_text_and_missing_date_default(c, external, account, model):
    model["response"] = json.dumps({**VALID, "is_expense": False, "amount": None})
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram, "Hello everyone")
    assert settled(wid).status == "ok" and not external.rows
    assert "has no expense yet" in external.messages[-1]["text"]
    model["response"] = json.dumps({**VALID, "expense_date": None})
    deliver(c, telegram, event_id=20202)
    until(lambda: len(runs_of(wid)) == 2 and all(run.status == "ok" for run in runs_of(wid)), timeout=20)
    assert external.rows[0][0] == "2026-11-02" and external.rows[0][6].startswith("2026-11-02T01:30")


@pytest.mark.parametrize("date_value", ["2026-02-30", "tomorrow", False])
def test_invalid_expense_date_requests_correction_without_write(c, external, account, model, date_value):
    model["response"] = json.dumps({**VALID, "expense_date": date_value})
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    assert settled(wid).status == "ok" and not external.rows
    assert "The expense date is not valid" in external.messages[-1]["text"]


def test_model_cannot_override_actor_submission_time_or_tool_targets(c, external, account, model):
    model["response"] = json.dumps({**VALID, "employee": "Forged person", "submitted_at": "2000-01-01", "chat_id": "0", "spreadsheet_id": "another-target", "description": "=untrusted formula-like text"})
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    assert settled(wid).status == "ok"
    assert external.rows[0][1:3] == ["Sample employee", "=untrusted formula-like text"]
    assert external.rows[0][6] == "2026-11-02T01:30:00+07:00"
    assert all(message["chat_id"] == "-100123" for message in external.messages)
    assert all("another-target" not in call[1] for call in external.calls)


def test_malformed_json_and_both_models_failed_are_visible(c, external, account, model):
    model["response"] = "{invalid"
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    run = settled(wid)
    assert run.status == "error" and any((event.get("error") or {}).get("code") == "CODE_FAILED" for event in json.loads(run.events)), run.events
    assert not external.rows and len(external.messages) == 1
    model["primary_error"] = model["backup_error"] = True
    deliver(c, telegram, event_id=30303)
    until(lambda: len(runs_of(wid)) == 2 and all(run.status == "error" for run in runs_of(wid)), timeout=20)
    assert not external.rows and len(external.messages) == 2
    assert any("PROVIDER_UNREACHABLE" in run.events for run in runs_of(wid))


def test_primary_model_failure_uses_fallback_and_confirms(c, external, account, model):
    model["primary_error"] = True
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    run = settled(wid)
    assert run.status == "ok" and len(external.rows) == 1 and len(external.messages) == 2
    assert [provider for _, provider in model["calls"]] == ["openrouter", "ollama"]
    finished = next(event for event in json.loads(run.events) if event.get("type") == "node_finished" and event.get("node") == "extract")
    assert [attempt["status"] for attempt in finished["model_attempts"]] == ["error", "ok"]


def test_lost_sheet_response_is_reconciled_before_success_reply(c, external, account, model):
    external.append_mode = "timeout"
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    run = settled(wid)
    assert run.status == "ok", run.events
    assert len(external.rows) == 1 and len(external.messages) == 2
    assert len([call for call in external.calls if call[1].endswith(":append")]) == 1
    assert json.loads(run.final_state)["sheet_write"]["reconciled"]


@pytest.mark.parametrize("mode", ["reject", "unknown"])
def test_sheet_rejection_or_unresolved_write_never_sends_success(c, external, account, model, monkeypatch, mode):
    external.append_mode = "reject" if mode == "reject" else "timeout"
    original = external.request
    def request(method, url, **kwargs):
        if mode == "unknown" and method == "GET" and external.rows:
            return httpx.Response(503, json={"error": "lookup unavailable"})
        return original(method, url, **kwargs)
    monkeypatch.setattr(sheets, "request", request)
    owner, wid, telegram, google, graph = setup(c, account)
    deliver(c, telegram)
    run = settled(wid)
    assert run.status == "error" and len(external.messages) == 1
    assert len(external.rows) == (0 if mode == "reject" else 1)
    code = "MCP_TOOL_FAILED" if mode == "reject" else "MANAGED_OUTCOME_UNKNOWN"
    assert any((event.get("error") or {}).get("code") == code for event in json.loads(run.events))


def test_portable_example_contains_only_setup_references():
    payload = json.loads(FILE.read_text())
    assert not problems(payload)
    assert payload["workflow"] == sanitize(payload["workflow"])
    assert all(not node["data"].get("server_id") and not node["data"].get("credential_id") for node in payload["workflow"]["nodes"])
    assert next(node for node in payload["workflow"]["nodes"] if node["id"] == "extract")["data"]["fallback"]["credential_id"] == ""
