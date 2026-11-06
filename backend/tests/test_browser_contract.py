"""Browser boundary tests: untrusted tool arguments cannot supply worker authority."""
import json

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.engine.browser_contract import (
    ARGUMENT_MODELS,
    MUTATING_OPERATIONS,
    READ_OPERATIONS,
    BrowserSettings,
    ExecutionContext,
    Observation,
    WorkerCommand,
    WorkerResult,
    tool_definitions,
)


def context():
    return {
        "principal_id": "visitor:one",
        "conversation_id": "chat-one",
        "run_id": "run-one",
        "group_id": "agent-one",
        "connection_id": "connection-one",
        "configuration": "a" * 64,
        "lease_generation": 1,
    }


def command(**extra):
    return {
        "context": context(),
        "session_id": "session-one",
        "generation": 1,
        "sequence": 0,
        "command_id": "command-one",
        "operation": "navigate",
        "arguments": {"url": "https://example.com"},
        **extra,
    }


def settings(**extra):
    return {"allowed_origins": ["https://example.com"], **extra}


def test_contract_round_trip_and_nine_tools_with_whitelist():
    value = WorkerCommand.model_validate(command())
    assert WorkerCommand.model_validate_json(value.model_dump_json()) == value
    parsed = BrowserSettings.model_validate(settings())
    assert parsed.proxy.mode == "direct"
    assert parsed.require_mutating_approval is False
    assert parsed.idle_timeout_s == 1800
    assert parsed.provider == "local"
    assert "url" not in BrowserSettings.model_json_schema()["properties"]
    definitions = {item["name"]: item["input_schema"] for item in tool_definitions()}
    assert set(definitions) == set(ARGUMENT_MODELS)
    assert set(definitions) == READ_OPERATIONS | MUTATING_OPERATIONS
    assert definitions["navigate"]["required"] == ["url"]
    for schema in definitions.values():
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
    gated = {item["name"] for item in tool_definitions(settings=parsed)}
    assert gated == {"navigate", "snapshot", "click", "fill", "extract", "screenshot"}
    opened = BrowserSettings.model_validate(
        settings(allow_upload=True, allow_download=True, allow_evaluate_js=True)
    )
    assert {item["name"] for item in tool_definitions(settings=opened)} == set(ARGUMENT_MODELS)


@pytest.mark.parametrize(
    "operation,args",
    [
        ("navigate", {"url": "https://example.com"}),
        ("snapshot", {}),
        ("click", {"observation_id": "o1", "element_id": "e1"}),
        ("fill", {"observation_id": "o1", "element_id": "e1", "value": "text"}),
        ("extract", {"observation_id": "o1", "fields": {"title": "e1"}}),
        ("screenshot", {}),
        ("upload", {"observation_id": "o1", "element_id": "e1", "source_kind": "attachment", "source_id": "att-1"}),
        ("download", {"observation_id": "o1", "element_id": "e1"}),
        ("evaluate", {"observation_id": "o1", "expression": "document.title"}),
    ],
)
def test_no_tool_accepts_authority_fields(operation, args):
    schema = next(item["input_schema"] for item in tool_definitions() if item["name"] == operation)
    assert Draft202012Validator(schema).is_valid(args)
    for field in (
        "context",
        "run_id",
        "principal_id",
        "session_id",
        "generation",
        "sequence",
        "proxy",
        "profile",
        "connection_id",
        "lease_generation",
        "approved",
        "javascript",
        "conversation_id",
    ):
        injected = {**args, field: "override"}
        assert not Draft202012Validator(schema).is_valid(injected)
        with pytest.raises(ValidationError):
            ARGUMENT_MODELS[operation].model_validate(injected)


@pytest.mark.parametrize(
    "extra",
    [
        {"version": 2},
        {"version": True},
        {"sequence": -1},
        {"generation": 0},
        {"timeout_ms": 60001},
        {"context": {**context(), "lease_generation": 0}},
        {"arguments": {"url": "file:///etc/passwd"}},
        {"arguments": {"url": "https://user:password@example.com"}},
        {"arguments": {"url": "https://example.com\\@private"}},
        {"arguments": {"url": "https://example.com\n"}},
        {"operation": "shell"},
    ],
)
def test_invalid_worker_commands(extra):
    with pytest.raises(ValidationError):
        WorkerCommand.model_validate(command(**extra))


@pytest.mark.parametrize(
    "payload",
    [
        {"start_url": "https://example.com"},
        {"stealth": True},
        {"version": True},
        {"version": 2},
        {"proxy": {"mode": "direct", "server": "http://proxy.example"}},
        {"proxy": {"mode": "operator_default", "auth": "basic"}},
        {"proxy": {"mode": "custom"}},
        {"proxy": {"mode": "custom", "server": "socks5://proxy.example:1080"}},
        {"proxy": {"mode": "custom", "server": "http://user:password@proxy.example"}},
        {"allowed_origins": []},
        {"allowed_origins": ["https://example.com/path"]},
        {"allowed_origins": ["https://example.com?token=secret"]},
        {"max_actions": True},
        {"max_actions": 201},
        {"lifetime_s": 120, "idle_timeout_s": 1800},
        {
            "allowed_origins": ["https://one.example"],
            "profile": {"name": "one", "origins": ["https://two.example"]},
        },
        {"provider": "controlled_cdp"},
        {"provider": "browserless", "stealth": "maybe"},
    ],
)
def test_invalid_connection_policy(payload):
    body = dict(payload)
    if "allowed_origins" not in body:
        body["allowed_origins"] = ["https://example.com"]
    with pytest.raises(ValidationError):
        BrowserSettings.model_validate(body)


def test_empty_whitelist_rejected_and_browserless_stealth_allowed():
    with pytest.raises(ValidationError):
        BrowserSettings.model_validate({"allowed_origins": []})
    with pytest.raises(ValidationError):
        BrowserSettings.model_validate({})
    local_stealth = settings(stealth=True)
    with pytest.raises(ValidationError):
        BrowserSettings.model_validate(local_stealth)
    ok = BrowserSettings.model_validate(settings(provider="browserless", stealth=True))
    assert ok.stealth is True and ok.provider == "browserless"


def test_observations_and_results_are_bounded_no_raw_artifacts_or_control_urls():
    observation = {
        "observation_id": "o1",
        "page_generation": 1,
        "origin": "https://example.com",
        "text": "page",
    }
    result = {
        "command_id": "c1",
        "generation": 1,
        "sequence": 0,
        "elapsed_ms": 20,
        "status": "confirmed",
        "observation": observation,
        "artifact_id": "artifact-one",
    }
    assert WorkerResult.model_validate_json(json.dumps(result)).observation.origin == "https://example.com"
    for extra in (
        {"screenshot_base64": "image"},
        {"cookies": []},
        {"remote_endpoint": "wss://control.example"},
        {"status": "success"},
        {"elapsed_ms": -1},
        {"artifact_id": "https://secret.example?token=secret"},
    ):
        with pytest.raises(ValidationError):
            WorkerResult.model_validate({**result, **extra})
    for extra in (
        {"text": "x" * 16001},
        {"origin": "https://example.com?token=secret"},
        {"elements": [{"element_id": "e1", "role": "button", "text": "b"}] * 201},
    ):
        with pytest.raises(ValidationError):
            Observation.model_validate({**observation, **extra})
    with pytest.raises(ValidationError):
        ExecutionContext.model_validate({**context(), "configuration": "not-a-snapshot"})


def test_utf8_response_byte_budget_catches_multibyte_content():
    element = {"element_id": "e1", "role": "button", "text": "😀" * 1000}
    value = {
        "command_id": "c1",
        "generation": 1,
        "sequence": 0,
        "elapsed_ms": 20,
        "status": "confirmed",
        "observation": {
            "observation_id": "o1",
            "page_generation": 1,
            "origin": "https://example.com",
            "elements": [element] * 200,
        },
    }
    with pytest.raises(ValidationError):
        WorkerResult.model_validate(value)
