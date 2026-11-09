"""Browser metadata uses existing MCP owner/org APIs and encrypted secret store."""
import uuid

import pytest

from app.api.deps import get_db, mcp_service
from app.core.errors import AppError
from app.repositories import McpServerRepository
from tests.test_chat_trigger_runs import c, api, user, H

ORIGINS = {"allowed_origins": ["https://example.com"]}


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "1")


def create(c, owner, **extra):
    settings = {**ORIGINS, **extra.pop("settings", {})}
    return c.post(
        "/api/mcp/servers",
        headers=H(owner["token"]),
        json={"name": "Browser " + uuid.uuid4().hex[:8], "transport": "managed", "adapter": "browser", "settings": settings, **extra},
    )


def test_metadata_discovery_no_network_and_owner_scope(c):
    owner, stranger = user(c), user(c)
    response = create(c, owner)
    assert response.status_code == 200, response.text
    server = response.json()["data"]
    assert server["settings"]["allowed_origins"] == ["https://example.com"]
    assert "url" not in server["settings"]
    found = c.post(f"/api/mcp/servers/{server['id']}/discover", headers=H(owner["token"]))
    assert found.status_code == 200
    names = {tool["name"] for tool in found.json()["data"]["tools"]}
    assert names == {"navigate", "snapshot", "click", "fill", "extract", "screenshot"}
    assert server["id"] not in str(c.get("/api/mcp/servers", headers=H(stranger["token"])).json())
    for method, path in [("post", "/discover"), ("put", ""), ("delete", "")]:
        kwargs = {"json": {"name": "stolen"}} if method == "put" else {}
        denied = getattr(c, method)(f"/api/mcp/servers/{server['id']}{path}", headers=H(stranger["token"]), **kwargs)
        assert denied.status_code == 404
        assert denied.json()["error"]["code"] == "MCP_SERVER_NOT_FOUND"
    assert c.delete(f"/api/mcp/servers/{server['id']}", headers=H(owner["token"])).status_code == 200


def test_empty_whitelist_rejected(c):
    owner = user(c)
    response = create(c, owner, settings={"allowed_origins": []})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MCP_CONFIG_INVALID"


def test_nine_tools_when_connection_allows_file_and_js(c):
    owner = user(c)
    response = create(
        c,
        owner,
        settings={
            "allowed_origins": ["https://example.com"],
            "allow_upload": True,
            "allow_download": True,
            "allow_evaluate_js": True,
        },
    )
    assert response.status_code == 200, response.text
    found = c.post(f"/api/mcp/servers/{response.json()['data']['id']}/discover", headers=H(owner["token"]))
    names = {tool["name"] for tool in found.json()["data"]["tools"]}
    assert names == {
        "navigate",
        "snapshot",
        "click",
        "fill",
        "extract",
        "screenshot",
        "upload",
        "download",
        "evaluate",
    }


def test_proxy_secrets_encrypted_masked_keep_remove_and_invalid_edits(c):
    owner = user(c)
    settings = {
        "provider": "browserless",
        "allowed_origins": ["https://example.com"],
        "proxy": {"mode": "custom", "server": "http://proxy.example:8080", "auth": "basic"},
    }
    secrets = {
        "browserless_token": "fixture-browserless-token",
        "proxy_username": "fixture-user",
        "proxy_password": "fixture-password",
    }
    response = create(c, owner, settings=settings, secrets=secrets)
    assert response.status_code == 200, response.text
    server = response.json()["data"]
    sid = server["id"]
    assert server["secrets"] == {key: "••••" for key in secrets}
    row = McpServerRepository(get_db()).get(sid)
    for secret in secrets.values():
        assert secret not in row.secrets and secret not in response.text
    changed = c.put(
        f"/api/mcp/servers/{sid}",
        headers=H(owner["token"]),
        json={"name": "Changed", "secrets": {key: None for key in secrets}},
    )
    assert changed.status_code == 200 and mcp_service()._stored(McpServerRepository(get_db()).get(sid)) == secrets
    bad = c.put(
        f"/api/mcp/servers/{sid}",
        headers=H(owner["token"]),
        json={"name": "Changed", "secrets": {"proxy_password": "new-secret"}},
    )
    assert bad.status_code == 400 and "new-secret" not in bad.text
    assert mcp_service()._stored(McpServerRepository(get_db()).get(sid)) == secrets
    removed = c.put(
        f"/api/mcp/servers/{sid}",
        headers=H(owner["token"]),
        json={"name": "Local", "settings": {"allowed_origins": ["https://example.com"]}, "secrets": {}},
    )
    assert removed.status_code == 200 and removed.json()["data"]["secrets"] == {}
    assert McpServerRepository(get_db()).get(sid).secrets is None


@pytest.mark.parametrize(
    "settings,secrets",
    [
        ({"provider": "browserless", "allowed_origins": ["https://example.com"]}, {}),
        ({"allowed_origins": ["https://example.com"]}, {"browserless_token": "token"}),
        ({"allowed_origins": ["https://example.com"]}, {"profile_state": "not-supported-yet"}),
        (
            {"provider": "browserless", "allowed_origins": ["https://example.com"]},
            {"browserless_token": "bad token with space"},
        ),
        (
            {
                "allowed_origins": ["https://example.com"],
                "proxy": {"mode": "custom", "server": "http://proxy.example", "auth": "basic"},
            },
            {},
        ),
        (
            {"allowed_origins": ["https://example.com"], "proxy": {"mode": "direct"}},
            {"proxy_username": "user", "proxy_password": "secret"},
        ),
        ({"allowed_origins": ["https://example.com"], "stealth": True}, {}),
        (
            {
                "allowed_origins": ["https://example.com"],
                "profile": {"name": "profile", "origins": ["https://site.example/path"]},
            },
            {},
        ),
        ({"allowed_origins": []}, {}),
    ],
)
def test_invalid_configuration_uses_shared_envelope(c, settings, secrets):
    response = create(c, user(c), settings=settings, secrets=secrets)
    assert response.status_code in (400, 403), response.text
    assert response.json()["error"]["code"] in {"MCP_CONFIG_INVALID", "BROWSER_PROFILE_DENIED"}



def test_browser_feature_gate_defaults_on(monkeypatch):
    from app.core import config
    monkeypatch.delenv("STUDIO_ENABLE_BROWSER", raising=False)
    assert config.browser_enabled() is True
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "0")
    assert config.browser_enabled() is False
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "1")
    assert config.browser_enabled() is True
    monkeypatch.delenv("STUDIO_ENABLE_BROWSER_RUNTIME", raising=False)
    assert config.browser_runtime_enabled() is False
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER_RUNTIME", "1")
    assert config.browser_runtime_enabled() is True
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "0")
    assert config.browser_runtime_enabled() is False


def test_disabled_gate_hides_adapter_and_denies_saved_connection(c, monkeypatch):
    owner = user(c)
    server = create(c, owner).json()["data"]
    monkeypatch.setenv("STUDIO_ENABLE_BROWSER", "0")
    assert "browser" not in [
        item["id"] for item in c.get("/api/mcp/servers", headers=H(owner["token"])).json()["data"]["managed_adapters"]
    ]
    for response in [create(c, owner), c.post(f"/api/mcp/servers/{server['id']}/discover", headers=H(owner["token"]))]:
        assert response.status_code == 404 and response.json()["error"]["code"] == "BROWSER_DISABLED"
    with pytest.raises(AppError) as caught:
        mcp_service().call(owner["id"], server["id"], "snapshot", {}, dry_run=True)
    assert caught.value.code == "BROWSER_DISABLED"


def test_no_stateless_ledger_or_browser_launch_and_org_policy(c):
    owner = user(c)
    server = create(c, owner).json()["data"]
    svc = mcp_service()
    assert svc.call(owner["id"], server["id"], "navigate", {"url": "https://example.com"}, dry_run=True)["outcome"] == "dry_run"
    for args in ({}, {"session_id": "forged"}):
        with pytest.raises(AppError) as caught:
            svc.call(owner["id"], server["id"], "snapshot", args, operation_key="one")
        assert caught.value.code == ("MCP_ARGUMENT_INVALID" if args else "BROWSER_RUNTIME_UNAVAILABLE")
    assert svc.operations(owner["id"], server["id"]) == []
    denied = create(c, owner, scope="org")
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "MCP_ADMIN_REQUIRED"
    row = svc.repo.get(server["id"])
    row.scope = "org"
    svc.repo.save(row)
    with pytest.raises(AppError) as caught:
        svc.call(owner["id"], server["id"], "snapshot", {}, org_allowed=False, dry_run=True)
    assert caught.value.code == "ORG_RESOURCE_NOT_ALLOWED"
    svc.repo.delete(server["id"])  # shared fixture DB: do not leak an org row into MCP regression tests
