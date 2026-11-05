"""Browser boundary tests: untrusted tool arguments cannot supply worker authority."""
import json

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.engine.browser_contract import (ARGUMENT_MODELS, BrowserSettings, ExecutionContext,
    Observation, WorkerCommand, WorkerResult, tool_definitions)


def context():
    return {"principal_id": "visitor:one", "run_id": "run-one", "group_id": "agent-one",
            "connection_id": "connection-one", "configuration": "a" * 64, "lease_generation": 1}


def command(**extra):
    return {"context": context(), "session_id": "session-one", "generation": 1, "sequence": 0,
            "command_id": "command-one", "operation": "navigate", "arguments": {"url": "https://example.com"}, **extra}


def test_contract_round_trip_and_dynamic_url_only_on_navigation():
    value = WorkerCommand.model_validate(command())
    assert WorkerCommand.model_validate_json(value.model_dump_json()) == value
    assert BrowserSettings.model_validate({}).proxy.mode == "direct"
    assert "url" not in BrowserSettings.model_json_schema()["properties"]
    definitions = {item["name"]: item["input_schema"] for item in tool_definitions()}
    assert set(definitions) == {"navigate", "snapshot", "click", "fill", "extract", "screenshot"}
    assert definitions["navigate"]["required"] == ["url"]
    for schema in definitions.values():
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False


@pytest.mark.parametrize("operation,args", [("navigate", {"url": "https://example.com"}), ("snapshot", {}),
    ("click", {"observation_id": "o1", "element_id": "e1"}),
    ("fill", {"observation_id": "o1", "element_id": "e1", "value": "text"}),
    ("extract", {"observation_id": "o1", "fields": {"title": "e1"}}), ("screenshot", {})])
def test_no_tool_accepts_authority_fields(operation, args):
    schema = next(item["input_schema"] for item in tool_definitions() if item["name"] == operation)
    assert Draft202012Validator(schema).is_valid(args)
    for field in ("context", "run_id", "principal_id", "session_id", "generation", "sequence", "proxy", "profile",
                  "connection_id", "lease_generation", "approved", "javascript", "evaluate"):
        injected = {**args, field: "override"}
        assert not Draft202012Validator(schema).is_valid(injected)
        with pytest.raises(ValidationError): ARGUMENT_MODELS[operation].model_validate(injected)


@pytest.mark.parametrize("extra", [{"version": 2}, {"version": True}, {"sequence": -1}, {"generation": 0}, {"timeout_ms": 60001},
    {"context": {**context(), "lease_generation": 0}}, {"arguments": {"url": "file:///etc/passwd"}},
    {"arguments": {"url": "https://user:password@example.com"}}, {"arguments": {"url": "https://example.com\\@private"}},
    {"arguments": {"url": "https://example.com\n"}}, {"operation": "evaluate"}])
def test_invalid_worker_commands(extra):
    with pytest.raises(ValidationError): WorkerCommand.model_validate(command(**extra))


@pytest.mark.parametrize("settings", [{"start_url": "https://example.com"}, {"stealth": True}, {"stealth": 0}, {"version": True}, {"version": 2},
    {"proxy": {"mode": "direct", "server": "http://proxy.example"}},
    {"proxy": {"mode": "operator_default", "auth": "basic"}}, {"proxy": {"mode": "custom"}},
    {"proxy": {"mode": "custom", "server": "socks5://proxy.example:1080"}},
    {"proxy": {"mode": "custom", "server": "http://user:password@proxy.example"}},
    {"allowed_origins": ["https://example.com/path"]}, {"allowed_origins": ["https://example.com?token=secret"]},
    {"max_actions": True}, {"max_actions": 101}, {"lifetime_s": 30, "idle_timeout_s": 120},
    {"allowed_origins": ["https://one.example"], "profile": {"name": "one", "origins": ["https://two.example"]}}])
def test_invalid_connection_policy(settings):
    with pytest.raises(ValidationError): BrowserSettings.model_validate(settings)


def test_observations_and_results_are_bounded_no_raw_artifacts_or_control_urls():
    observation = {"observation_id": "o1", "page_generation": 1, "origin": "https://example.com", "text": "page"}
    result = {"command_id": "c1", "generation": 1, "sequence": 0, "elapsed_ms": 20,
              "status": "confirmed", "observation": observation, "artifact_id": "artifact-one"}
    assert WorkerResult.model_validate_json(json.dumps(result)).observation.origin == "https://example.com"
    for extra in ({"screenshot_base64": "image"}, {"cookies": []}, {"remote_endpoint": "wss://control.example"},
                  {"status": "success"}, {"elapsed_ms": -1}, {"artifact_id": "https://secret.example?token=secret"}):
        with pytest.raises(ValidationError): WorkerResult.model_validate({**result, **extra})
    for extra in ({"text": "x" * 16001}, {"origin": "https://example.com?token=secret"},
                  {"elements": [{"element_id": "e1", "role": "button", "text": "b"}] * 201}):
        with pytest.raises(ValidationError): Observation.model_validate({**observation, **extra})
    with pytest.raises(ValidationError): ExecutionContext.model_validate({**context(), "configuration": "not-a-snapshot"})


def test_utf8_response_byte_budget_catches_multibyte_content():
    element = {"element_id": "e1", "role": "button", "text": "😀" * 1000}
    value = {"command_id": "c1", "generation": 1, "sequence": 0, "elapsed_ms": 20, "status": "confirmed",
             "observation": {"observation_id": "o1", "page_generation": 1, "origin": "https://example.com", "elements": [element] * 200}}
    with pytest.raises(ValidationError): WorkerResult.model_validate(value)
