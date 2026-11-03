"""Drive managed operations against the HTTP double: folder admission, auth and safe creation recovery."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.api.deps import mcp_service, get_db
from app.core.errors import AppError
from app.repositories import McpServerRepository
from app.services.managed_tools import drive
from tests.test_chat_trigger_runs import c, api, user, H
from tests.test_managed_tools import account
from tests.test_managed_http_api import error
from tests.fixtures.drive_provider import DriveProvider, FOLDER_ID, OAUTH, TOKEN


@pytest.fixture
def remote(monkeypatch, account):
    fake = DriveProvider(account)
    monkeypatch.setattr(drive, "request", fake.request)
    return fake


def create(c, owner, credentials=None, folder=FOLDER_ID):
    response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "Drive fixture", "transport": "managed", "adapter": "google_drive",
        "settings": {"folder_id": folder}, "secrets": {"google_credentials": json.dumps(credentials or OAUTH)}})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_personal_oauth_create_read_metadata_and_known_replay(c, remote):
    remote.shared = False
    owner = user(c); server = create(c, owner, {**OAUTH, "token_uri": "https://evil.invalid/token"}); svc = mcp_service(); sid = server["id"]
    assert OAUTH["refresh_token"] not in json.dumps(server) and server["secrets"]["google_credentials"] == "••••"
    assert OAUTH["client_secret"] not in McpServerRepository(get_db()).get(sid).secrets
    assert {tool["name"] for tool in svc.discover(sid, owner["id"])["tools"]} == {"list_files", "get_file", "read_text_file", "create_text_file"}
    assert not remote.calls
    args = {"name": "receipt.txt", "content": "Chi phí 50.000đ\r\n"}
    result = svc.call(owner["id"], sid, "create_text_file", args, operation_key="create")
    assert result["outcome"] == "confirmed" and remote.uploads == 1
    fid = result["file"]["id"]; assert remote.files[fid]["content"] == args["content"].encode()
    props = remote.files[fid]["metadata"]["appProperties"]
    assert props == {"studio_operation": drive.sha(b"create"), "studio_sha256": drive.sha(args["content"].encode())}
    assert all(len((key + value).encode()) <= 124 for key, value in props.items())
    before = len(remote.calls)
    assert svc.call(owner["id"], sid, "create_text_file", args, operation_key="create") == result and len(remote.calls) == before
    with error("MANAGED_OPERATION_CONFLICT"): svc.call(owner["id"], sid, "create_text_file", {**args, "content": "different"}, operation_key="create")
    read = svc.call(owner["id"], sid, "read_text_file", {"file_id": fid}, operation_key="read")
    assert read["content"] == args["content"] and read["encoding"] == "utf-8"
    assert svc.call(owner["id"], sid, "get_file", {"file_id": fid}, operation_key="metadata")["file"]["name"] == "receipt.txt"
    assert all("evil.invalid" not in url for _, url, _ in remote.calls)


def test_service_account_shared_drive_scope_and_personal_storage_refusal(c, remote, account):
    owner = user(c); credentials = {key: value for key, value in account.items() if key != "public_key"}
    server = create(c, owner, {**credentials, "subject": "not-delegated@example.test", "token_uri": "https://evil.invalid"}); svc = mcp_service()
    svc.call(owner["id"], server["id"], "create_text_file", {"name": "shared.txt", "content": "shared"}, operation_key="shared")
    assert remote.uploads == 1
    query = next(options["params"] for method, url, options in remote.calls if method == "GET" and url == drive.API)
    assert query["corpora"] == "drive" and query["driveId"] == "fixture-shared-drive-123"
    remote.shared = False
    with error("MCP_CONFIG_INVALID"): svc.call(owner["id"], server["id"], "create_text_file", {"name": "personal.txt", "content": "no ownership"}, operation_key="personal")
    assert remote.uploads == 1
    remote.files.clear(); remote.add()
    assert svc.call(owner["id"], server["id"], "read_text_file", {"file_id": "fixture-text-123"}, operation_key="personal-read")["content"] == "Synthetic text"


def test_list_escaped_query_pagination_and_native_doc_export(c, remote):
    remote.add(); remote.add("fixture-google-doc-123", mime=drive.DOC, content="Nội dung Google Doc".encode())
    owner = user(c); server = create(c, owner); svc = mcp_service(); sid = server["id"]
    remote.lookup_mode = "next_page"
    result = svc.call(owner["id"], sid, "list_files", {"name_contains": "O'Reilly\\Reports", "page_size": "10", "page_token": "opaque-page-token"}, operation_key="list")
    assert len(result["files"]) == 2 and result["next_page_token"] == "fixture-next-page"
    query = next(options["params"] for _, url, options in remote.calls if url == drive.API)
    assert query["q"] == "'fixture-folder-123' in parents and trashed = false and name contains 'O\\'Reilly\\\\Reports'"
    assert query["pageToken"] == "opaque-page-token" and query["pageSize"] == 10
    result = svc.call(owner["id"], sid, "read_text_file", {"file_id": "fixture-google-doc-123"}, operation_key="export")
    assert result["content"] == "Nội dung Google Doc"
    assert remote.calls[-1][1].endswith("/export")


@pytest.mark.parametrize("kind", ["outside", "trashed", "other_drive", "shortcut", "binary"])
def test_file_scope_and_unsupported_content_never_download(c, remote, kind):
    metadata = remote.add()
    if kind == "outside": metadata["parents"] = ["another-folder-123"]
    if kind == "trashed": metadata["trashed"] = True
    if kind == "other_drive": metadata["driveId"] = "another-shared-drive-123"
    if kind == "shortcut": metadata["mimeType"] = "application/vnd.google-apps.shortcut"
    if kind == "binary": metadata["mimeType"] = "application/pdf"
    owner = user(c); server = create(c, owner); svc = mcp_service()
    with error("MCP_ARGUMENT_INVALID" if kind in {"shortcut", "binary"} else "MCP_TOOL_FAILED"):
        svc.call(owner["id"], server["id"], "read_text_file", {"file_id": metadata["id"]}, operation_key="blocked")
    assert not any(options.get("params", {}).get("alt") == "media" for _, _, options in remote.calls)


@pytest.mark.parametrize("mode", ["timeout", "server", "malformed", "wrong_checksum"])
def test_lost_or_invalid_create_ack_reconciles_by_actual_bytes_without_upload(c, remote, mode):
    owner = user(c); server = create(c, owner); svc = mcp_service(); remote.write_mode = mode
    args = {"name": "receipt.txt", "content": "Valid creation"}
    with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], server["id"], "create_text_file", args, operation_key="lost")
    [operation] = svc.operations(owner["id"], server["id"])
    result = svc.reconcile(owner["id"], server["id"], operation["operation_id"])
    assert result["outcome"] == "confirmed" and result["reconciled"] and remote.uploads == 1
    assert svc.call(owner["id"], server["id"], "create_text_file", args, operation_key="lost") == result and remote.uploads == 1


@pytest.mark.parametrize("mode", ["missing", "duplicate", "incomplete", "next_page", "outside", "changed_content"])
def test_uncertain_lookup_never_confirms_or_uploads_again(c, remote, mode):
    owner = user(c); server = create(c, owner); svc = mcp_service(); remote.write_mode = "timeout"
    args = {"name": "receipt.txt", "content": "Original content"}
    with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], server["id"], "create_text_file", args, operation_key="unknown")
    if mode == "changed_content":
        entry = next(iter(remote.files.values())); entry["content"] = b"Externally changed"
        entry["metadata"].update(size=str(len(entry["content"])), md5Checksum=drive.md5(entry["content"]))
    else: remote.lookup_mode = mode
    for _ in range(2):
        with error("MANAGED_OUTCOME_UNKNOWN"): svc.call(owner["id"], server["id"], "create_text_file", args, operation_key="unknown")
    assert remote.uploads == 1


@pytest.mark.parametrize("mode,uploads", [("crash_before", 0), ("crash_after", 1)])
def test_worker_crash_requires_read_only_recovery(c, remote, mode, uploads):
    owner = user(c); server = create(c, owner); svc = mcp_service(); remote.write_mode = mode
    args = {"name": "receipt.txt", "content": "Crash recovery"}
    with pytest.raises(KeyboardInterrupt): svc.call(owner["id"], server["id"], "create_text_file", args, operation_key="crash")
    [operation] = svc.operations(owner["id"], server["id"]); assert operation["outcome"] == "pending"
    if uploads: assert svc.reconcile(owner["id"], server["id"], operation["operation_id"])["reconciled"]
    else:
        with error("MANAGED_OUTCOME_UNKNOWN"): svc.reconcile(owner["id"], server["id"], operation["operation_id"])
    assert remote.uploads == uploads


@pytest.mark.parametrize("mode", ["oversized", "invalid_utf8"])
def test_read_boundaries_and_credentials_never_leak(c, remote, mode):
    remote.add(content=(TOKEN + " " + OAUTH["refresh_token"] + " " + OAUTH["client_secret"]).encode())
    owner = user(c); server = create(c, owner); svc = mcp_service()
    result = svc.call(owner["id"], server["id"], "read_text_file", {"file_id": "fixture-text-123"}, operation_key="redacted")
    assert "[redacted]" in result["content"] and all(value not in json.dumps(result) for value in (TOKEN, OAUTH["refresh_token"], OAUTH["client_secret"]))
    remote.read_mode = mode
    with error("MCP_TOOL_FAILED"): svc.call(owner["id"], server["id"], "read_text_file", {"file_id": "fixture-text-123"}, operation_key="bad-content")
    assert all(value not in json.dumps(svc.operations(owner["id"], server["id"])) for value in (TOKEN, OAUTH["refresh_token"], OAUTH["client_secret"]))


def test_permissions_dry_run_argument_validation_and_changed_folder(c, remote):
    owner, stranger = user(c), user(c); server = create(c, owner); svc = mcp_service(); sid = server["id"]
    args = {"name": "receipt.txt", "content": "data"}
    with error("MCP_SERVER_NOT_FOUND"): svc.call(stranger["id"], sid, "create_text_file", args, operation_key="forbidden")
    assert svc.call(owner["id"], sid, "create_text_file", args, dry_run=True)["outcome"] == "dry_run" and not remote.calls
    for bad in [{**args, "folder_id": "another-folder-123"}, {**args, "content": chr(0xD800)}, {**args, "content": "đ" * 40000}]:
        with error("MCP_ARGUMENT_INVALID"): svc.call(owner["id"], sid, "create_text_file", bad, operation_key="invalid")
    assert remote.uploads == 0
    svc.call(owner["id"], sid, "create_text_file", args, operation_key="fixed")
    svc.update(sid, owner["id"], "Moved fixture", settings={"folder_id": "fixture-folder-other"})
    with error("MANAGED_OPERATION_CONFLICT"): svc.call(owner["id"], sid, "create_text_file", args, operation_key="fixed")
    row = svc.repo.get(sid); row.scope = "org"; svc.repo.save(row)
    try:
        with error("ORG_RESOURCE_NOT_ALLOWED"): svc.call(owner["id"], sid, "list_files", {}, org_allowed=False, operation_key="org-policy")
    finally:
        row.scope = "user"; svc.repo.save(row)


@pytest.mark.parametrize("mode", ["timeout", "reject", "malformed"])
def test_token_failure_and_provider_rejection_do_not_upload(c, remote, mode):
    owner = user(c); server = create(c, owner); svc = mcp_service(); remote.token_mode = mode
    with error("MCP_TOOL_FAILED"): svc.call(owner["id"], server["id"], "create_text_file", {"name": "no.txt", "content": "not sent"}, operation_key="auth-failure")
    assert remote.uploads == 0


def test_no_folder_write_permission_and_concurrent_call(c, remote):
    owner = user(c); server = create(c, owner); svc = mcp_service(); sid = server["id"]; args = {"name": "one.txt", "content": "one"}
    remote.can_write = False
    with error("MCP_TOOL_FAILED"): svc.call(owner["id"], sid, "create_text_file", args, operation_key="no-write")
    assert remote.uploads == 0
    remote.can_write = True; remote.write_mode = "block"
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(svc.call, owner["id"], sid, "create_text_file", args, operation_key="concurrent")
        assert remote.entered.wait(5)
        try:
            result = svc.call(owner["id"], sid, "create_text_file", args, operation_key="concurrent")
            assert result["reconciled"]
        finally: remote.release.set()
        assert future.result()["outcome"] == "confirmed"
    assert remote.uploads == 1


@pytest.mark.parametrize("value", ["not JSON", "{}", '{"type":"service_account","private_key":"not a key"}', '{"type":"authorized_user","client_id":"x"}'])
def test_invalid_credentials_and_folder_are_sanitised(c, value):
    owner = user(c)
    response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "Invalid Drive", "transport": "managed", "adapter": "google_drive",
        "settings": {"folder_id": FOLDER_ID}, "secrets": {"google_credentials": value}})
    assert response.status_code == 400 and response.json()["error"]["code"] == "MCP_CONFIG_INVALID"
    response = c.post("/api/mcp/servers", headers=H(owner["token"]), json={"name": "Invalid Drive", "transport": "managed", "adapter": "google_drive",
        "settings": {"folder_id": "root"}, "secrets": {"google_credentials": json.dumps(OAUTH)}})
    assert response.status_code == 400


def test_bad_folder_provider_rejection_and_invalid_metadata_are_safe(c, remote):
    owner = user(c); server = create(c, owner); svc = mcp_service(); sid = server["id"]; args = {"name": "new.txt", "content": "data"}
    remote.folder_valid = False
    with error("MCP_TOOL_FAILED"): svc.call(owner["id"], sid, "create_text_file", args, operation_key="not-folder")
    assert remote.uploads == 0
    remote.folder_valid = True; remote.write_mode = "reject"
    for _ in range(2):
        with error("MCP_TOOL_FAILED"): svc.call(owner["id"], sid, "create_text_file", args, operation_key="rejected")
    assert remote.uploads == 0
    remote.add(name=chr(0xD800))
    with error("MCP_TOOL_FAILED"): svc.call(owner["id"], sid, "get_file", {"file_id": "fixture-text-123"}, operation_key="bad-name")
