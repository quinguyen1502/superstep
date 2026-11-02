"""Managed adapters: owner scope, typed calls, stable intent and uncertain-write recovery."""
import json, threading, uuid
from concurrent.futures import ThreadPoolExecutor
import httpx, jwt, pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from app.api.deps import mcp_service, get_db
from app.core.errors import AppError
from app.engine.agents import run_tool
from app.engine.effects import Effects
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.repositories import McpServerRepository
from app.services.managed_tools import sheets, telegram
from tests.test_chat_trigger_runs import c, api, user, H, TG

SETTINGS = {"spreadsheet_id": "fixture-spreadsheet-123", "sheet_name": "Expenses", "data_columns": 6}
VALUES = ["2026-11-01", "Example", "=untrusted text", "Food", 50000, "Chờ duyệt"]


@pytest.fixture(scope="module")
def account():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {"type": "service_account", "client_email": "fixture@example-project.iam.gserviceaccount.com",
            "private_key": private.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode(),
            "public_key": private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()}


class FakeService:
    def __init__(self, account):
        self.account, self.calls, self.rows, self.messages = account, [], [], []
        self.append_mode, self.send_mode = "ok", "ok"
        self.entered, self.release = threading.Event(), threading.Event()

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url == sheets.TOKEN_URL:
            claims = jwt.decode(kwargs["data"]["assertion"], self.account["public_key"], algorithms=["RS256"], audience=sheets.TOKEN_URL)
            assert claims["iss"] == self.account["client_email"] and claims["scope"] == sheets.SCOPE
            return httpx.Response(200, json={"access_token": "fixture-access-token"})
        if method == "GET": return httpx.Response(200, json={"values": [[row[-1]] for row in self.rows]})
        if url.endswith(":append"):
            assert kwargs["params"]["valueInputOption"] == "RAW"
            assert kwargs["headers"]["Authorization"] == "Bearer fixture-access-token"
            if self.append_mode == "reject": return httpx.Response(403, json={"error": "rejected"})
            self.rows.append(kwargs["json"]["values"][0])
            if self.append_mode in ("server_error", "request_timeout"):
                return httpx.Response(503 if self.append_mode == "server_error" else 408, json={"error": "uncertain"})
            if self.append_mode == "malformed": return httpx.Response(200, json={})
            if self.append_mode == "block": self.entered.set(); self.release.wait(5)
            if self.append_mode == "timeout": raise httpx.ReadTimeout("fixture-access-token must not leak")
            return httpx.Response(200, json={"updates": {"updatedRows": 1, "updatedRange": f"Expenses!A{len(self.rows)}:G{len(self.rows)}"}})
        if url.endswith("/sendMessage"):
            self.messages.append(kwargs["json"])
            if self.send_mode == "timeout": raise httpx.ReadTimeout("bot token must not leak")
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 99}})
        raise AssertionError("Unexpected request " + url)


@pytest.fixture
def external(monkeypatch, account):
    fake = FakeService(account)
    monkeypatch.setattr(sheets, "request", fake.request)
    monkeypatch.setattr(telegram, "request", fake.request)
    return fake


def create(c, owner, account=None, **extra):
    if account is None:
        channel = c.post("/api/approvals/channels", headers=H(owner["token"]), json={"kind": "telegram", **TG}).json()["data"]
        body = {"adapter": "telegram", "settings": {"channel_id": channel["id"], "chat_id": "-100123"}}
    else:
        body = {"adapter": "google_sheets", "settings": SETTINGS, "secrets": {"service_account": json.dumps({k: v for k, v in account.items() if k != "public_key"})}}
    response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "Managed " + uuid.uuid4().hex[:8], "transport": "managed", **body, **extra})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_discovery_encryption_and_argument_schema(c, external, account):
    owner = user(c); server = create(c, owner, account)
    row = McpServerRepository(get_db()).get(server["id"])
    assert account["private_key"] not in row.secrets and "PRIVATE KEY" not in str(server)
    result = c.post(f"/api/mcp/servers/{server['id']}/discover", headers=H(owner["token"])).json()["data"]
    assert result["tools"][0]["name"] == "append_row"
    assert result["tools"][0]["input_schema"]["properties"]["values"]["maxItems"] == 6
    assert not external.calls
    svc = mcp_service()
    for args in [{"values": [1]}, {"values": VALUES, "spreadsheet_id": "another"}, {"values": [*VALUES[:5], {}]}]:
        with pytest.raises(AppError) as caught: svc.call(owner["id"], server["id"], "append_row", args, operation_key="bad")
        assert caught.value.code == "MCP_ARGUMENT_INVALID"
    assert not external.calls


def test_known_sheet_write_reuses_result_and_raw_values(c, external, account):
    owner = user(c); server = create(c, owner, account); svc = mcp_service()
    first = svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="stable-key")
    second = svc.call(owner["id"], server["id"], "append_row", {"values": json.dumps(VALUES)}, operation_key="stable-key")
    assert first == second and first["outcome"] == "confirmed"
    assert external.rows == [[*VALUES, "stable-key"]]
    assert len([call for call in external.calls if call[1].endswith(":append")]) == 1
    assert "PRIVATE KEY" not in str(first) and "fixture-access-token" not in str(first)
    with pytest.raises(AppError) as caught:
        svc.call(owner["id"], server["id"], "append_row", {"values": ["different", *VALUES[1:]]}, operation_key="stable-key")
    assert caught.value.code == "MANAGED_OPERATION_CONFLICT" and len(external.rows) == 1


def test_timeout_after_sheet_acceptance_reconciles_without_append(c, external, account):
    owner = user(c); server = create(c, owner, account); svc = mcp_service(); external.append_mode = "timeout"
    with pytest.raises(AppError) as caught:
        svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="lost-response")
    assert caught.value.code == "MANAGED_OUTCOME_UNKNOWN" and "fixture-access-token" not in str(caught.value)
    [operation] = svc.operations(owner["id"], server["id"])
    assert operation["outcome"] == "unknown"
    response = c.post(f"/api/mcp/servers/{server['id']}/operations/{operation['operation_id']}/reconcile", headers=H(owner["token"]))
    assert response.json()["data"]["outcome"] == "confirmed" and response.json()["data"]["reconciled"]
    assert len(external.rows) == 1 and len([call for call in external.calls if call[1].endswith(":append")]) == 1
    assert svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="lost-response")["outcome"] == "confirmed"


@pytest.mark.parametrize("mode", ["server_error", "request_timeout", "malformed"])
def test_uncertain_provider_responses_require_read_only_reconciliation(c, external, account, mode):
    owner = user(c); server = create(c, owner, account); external.append_mode = mode; svc = mcp_service()
    with pytest.raises(AppError) as caught:
        svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="provider-response")
    assert caught.value.code == "MANAGED_OUTCOME_UNKNOWN"
    result = mcp_service().call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="provider-response")
    assert result["reconciled"] and len(external.rows) == 1


def test_pending_intent_after_crash_blocks_even_when_no_row_exists(c, external, account, monkeypatch):
    owner = user(c); server = create(c, owner, account); svc = mcp_service()
    adapter = svc.managed.adapter("google_sheets")
    def crash(*_): raise KeyboardInterrupt("simulated process loss before request")
    monkeypatch.setattr(adapter, "execute", crash)
    with pytest.raises(KeyboardInterrupt): svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="crash")
    assert svc.operations(owner["id"], server["id"])[0]["outcome"] == "pending"
    with pytest.raises(AppError) as caught:
        mcp_service().call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="crash")
    assert caught.value.code == "MANAGED_OUTCOME_UNKNOWN" and external.rows == []


def test_concurrent_call_does_not_repeat_in_flight_append(c, external, account):
    owner = user(c); server = create(c, owner, account); external.append_mode = "block"
    def call(): return mcp_service().call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="concurrent")
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(call); assert external.entered.wait(5)
        second = pool.submit(call)
        try: assert second.result(5)["outcome"] == "confirmed"
        finally: external.release.set()
        assert first.result(5)["outcome"] == "confirmed"
    assert len(external.rows) == 1


def test_crash_after_write_before_local_result_is_reconciled(c, external, account, monkeypatch):
    owner = user(c); server = create(c, owner, account); svc = mcp_service()
    def crash(*_): raise KeyboardInterrupt("lost before local acknowledgement")
    monkeypatch.setattr(svc.managed.operations, "finish", crash)
    with pytest.raises(KeyboardInterrupt):
        svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="after-write")
    assert len(external.rows) == 1
    result = mcp_service().call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="after-write")
    assert result["reconciled"] and len(external.rows) == 1


def test_rejected_sheet_write_is_not_reported_as_success_or_repeated(c, external, account):
    owner = user(c); server = create(c, owner, account); svc = mcp_service(); external.append_mode = "reject"
    for _ in range(2):
        with pytest.raises(AppError) as caught:
            svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="rejected")
        assert caught.value.code == "MCP_TOOL_FAILED"
    assert not external.rows and len([call for call in external.calls if call[1].endswith(":append")]) == 1
    assert svc.operations(owner["id"], server["id"])[0]["outcome"] == "failed"


def test_personal_telegram_source_cannot_be_delegated_to_other_owner(c, external):
    owner, stranger = user(c), user(c); server = create(c, owner)
    response = c.post("/api/mcp/servers", headers=H(stranger["token"]), json={"name": "Forbidden", "transport": "managed", "adapter": "telegram", "settings": server["settings"]})
    assert response.json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    svc = mcp_service(); row = svc.repo.get(server["id"]); row.scope = "org"; svc.repo.save(row)
    try:
        with pytest.raises(AppError) as caught:
            svc.call(stranger["id"], server["id"], "send_message", {"text": "Forbidden"}, operation_key="forbidden")
        assert caught.value.code == "CHANNEL_NOT_FOUND" and not external.calls
    finally:
        row.scope = "user"; svc.repo.save(row)


def test_private_managed_connection_cannot_bypass_runners_org_channel_policy(c, external):
    owner = user(c); server = create(c, owner); svc = mcp_service()
    channels = svc.managed.adapter("telegram").channels
    channel = channels.repo.channel(server["settings"]["channel_id"]); channel.scope = "org"; channels.repo.save_channel(channel)
    try:
        with pytest.raises(AppError) as caught:
            svc.call(owner["id"], server["id"], "send_message", {"text": "Forbidden"}, org_allowed=False, operation_key="indirect-org")
        assert caught.value.code == "CHANNEL_NOT_FOUND" and not external.calls
    finally:
        channel.scope = "user"; channels.repo.save_channel(channel)


def test_managed_transport_pins_checked_host_and_blocks_private_addresses(monkeypatch):
    from app.services.managed_tools import base
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "0")
    with pytest.raises(AppError) as caught: base.request("GET", "http://127.0.0.1/test")
    assert caught.value.code == "MCP_URL_INVALID"
    seen = []
    def fake(request): seen.append(request); return httpx.Response(200, json={"ok": True})
    monkeypatch.setattr(base, "public_address", lambda url, *args: (url, "93.184.216.34"))
    monkeypatch.setattr(base, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(fake), follow_redirects=False))
    base.request("POST", "https://sheets.googleapis.com/test", headers={"Authorization": "Bearer fixture"}, json={"values": []})
    assert seen[0].url.host == "93.184.216.34" and seen[0].headers["host"] == "sheets.googleapis.com"
    assert seen[0].headers["authorization"] == "Bearer fixture"


def test_managed_schema_upgrade_and_downgrade_preserve_existing_mcp_rows(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, select
    from app.models import McpServer
    from app.models.database import Database, MIGRATIONS_DIR
    database = Database(f"sqlite:///{tmp_path / 'managed.db'}"); database.migrate()
    repo = McpServerRepository(database)
    repo.save(McpServer(id="legacy", owner="owner", name="Legacy", transport="http", scope="user", url="https://example.com/mcp", created=1))
    assert {"adapter", "settings"} <= {column["name"] for column in inspect(database.engine).get_columns("mcp_servers")}
    cfg = Config(); cfg.set_main_option("script_location", MIGRATIONS_DIR)
    with database.engine.begin() as connection:
        cfg.attributes["connection"] = connection; command.downgrade(cfg, "0051_chat_app_keys")
    assert "mcp_operations" not in inspect(database.engine).get_table_names()
    assert "adapter" not in {column["name"] for column in inspect(database.engine).get_columns("mcp_servers")}
    with database.session() as session: assert session.scalar(select(McpServer.name).where(McpServer.id == "legacy")) == "Legacy"
    database.migrate()
    assert repo.get("legacy").url == "https://example.com/mcp" and "mcp_operations" in inspect(database.engine).get_table_names()


def test_telegram_fixed_destination_known_replay_and_unknown_block(c, external):
    owner = user(c); server = create(c, owner); svc = mcp_service()
    args = {"text": "Processing", "reply_to_message_id": 101}
    result = svc.call(owner["id"], server["id"], "send_message", args, operation_key="known")
    assert result == svc.call(owner["id"], server["id"], "send_message", args, operation_key="known")
    assert external.messages == [{"chat_id": "-100123", "text": "Processing", "disable_web_page_preview": True,
                                   "reply_parameters": {"message_id": 101, "allow_sending_without_reply": True}}]
    external.send_mode = "timeout"
    for _ in range(2):
        with pytest.raises(AppError) as caught: svc.call(owner["id"], server["id"], "send_message", args, operation_key="uncertain")
        assert caught.value.code == "MANAGED_OUTCOME_UNKNOWN"
    assert len(external.messages) == 2


def test_permissions_dry_run_and_changed_target(c, external, account):
    owner, stranger = user(c), user(c); server = create(c, owner, account); svc = mcp_service()
    with pytest.raises(AppError) as caught: svc.call(stranger["id"], server["id"], "append_row", {"values": VALUES}, operation_key="denied")
    assert caught.value.code == "MCP_SERVER_NOT_FOUND"
    assert svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, dry_run=True) == {"outcome": "dry_run", "tool": "append_row"}
    assert not external.calls and not svc.operations(owner["id"], server["id"])
    with pytest.raises(AppError) as caught: svc.call(owner["id"], server["id"], "append_row", {"values": VALUES})
    assert caught.value.code == "MANAGED_OPERATION_KEY_REQUIRED"
    svc.call(owner["id"], server["id"], "append_row", {"values": VALUES}, operation_key="changed-target")
    row = svc.repo.get(server["id"]); row.settings = json.dumps({**SETTINGS, "sheet_name": "Another"}); svc.repo.save(row)
    operation = svc.operations(owner["id"], server["id"])[0]
    with pytest.raises(AppError) as caught: svc.reconcile(owner["id"], server["id"], operation["operation_id"])
    assert caught.value.code == "MANAGED_OPERATION_CONFLICT"


def test_mcp_and_agent_ports_use_stable_keys_and_dry_runs(c, external):
    owner = user(c); server = create(c, owner); svc = mcp_service()
    ports = Ports(mcp_call=svc.caller(owner["id"]), mcp_effect_call=svc.effect_caller(owner["id"]))
    graph = {"name": "Managed graph", "state": [{"name": "result", "type": "object"}], "nodes": [
        {"id": "s", "type": "start", "data": {}}, {"id": "tool", "type": "mcp", "data": {"server_id": server["id"], "tool": "send_message", "arguments": {"text": "Hi"}, "output_field": "result"}},
        {"id": "e", "type": "end", "data": {}}], "edges": [{"id": "1", "source": "s", "target": "tool"}, {"id": "2", "source": "tool", "target": "e"}]}
    events = list(run_stream(graph, {}, ports=ports, effects=Effects("run-fixture")))
    assert events[-1]["state"]["result"]["outcome"] == "confirmed"
    tool = {"source": "mcp", "server_id": server["id"], "tool": "send_message"}
    assert run_tool("agent-tool", tool, {"text": "Agent"}, {}, ports, Effects("agent-run"))["outcome"] == "confirmed"
    ports.test = True
    assert run_tool("agent-tool", tool, {"text": "Test"}, {}, ports, Effects("test-run"))["outcome"] == "dry_run"
    assert len(external.messages) == 2
    wid = c.post("/api/workflows", headers=H(owner["token"]), json=graph).json()["data"]["id"]
    for language in ("python", "typescript"):
        response = c.get(f"/api/workflows/{wid}/code?language={language}", headers=H(owner["token"]))
        assert response.json()["error"]["code"] == "MANAGED_EXPORT_UNAVAILABLE"
