"""Opt-in model failover: permission boundary, bounded attempts, cancellation and buffered output."""
from concurrent.futures import CancelledError
import copy
import pytest
from langgraph.errors import NodeTimeoutError
from app.core.errors import AppError
from app.engine import model_policy, nodes
from app.engine.ports import Ports
from app.engine.providers import ProviderError
from app.engine.runtime import run_stream
from app.engine.templates import sanitize
from app.engine.validator import validate
from app.engine.python_export import to_python
from app.engine.typescript_export import to_typescript
from tests.test_llm_providers import c, H, user

DATA = {"credential_id": "primary", "model": "first", "output_field": "answer", "prompt": "{{state.message}}",
        "fallback": {"credential_id": "backup", "model": "second"}}
CREDS = {"primary": {"provider": "openrouter", "api_key": "test-only-secret"}, "backup": {"provider": "ollama", "api_key": ""}}


def graph(data=None):
    return {"name": "Fallback", "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}],
        "nodes": [{"id": "s", "type": "start", "data": {}}, {"id": "m", "type": "llm", "data": copy.deepcopy(data if data is not None else DATA)},
                  {"id": "e", "type": "end", "data": {}}],
        "edges": [{"id": "1", "source": "s", "target": "m"}, {"id": "2", "source": "m", "target": "e"}]}


def test_primary_success_does_not_call_alternate_and_trace_has_no_secret(monkeypatch):
    calls = []
    def invoke(prompt, model, cred, report, on_token, **kwargs):
        calls.append((model, on_token)); return "primary answer"
    monkeypatch.setattr(nodes, "call_llm", invoke)
    events = list(run_stream(graph(), {"message": "hello"}, resolve=CREDS.__getitem__))
    assert events[-1]["state"]["answer"] == "primary answer"
    assert calls == [("first", None)]
    finished = next(e for e in events if e["type"] == "node_finished" and e["node"] == "m")
    assert finished["model_attempts"] == [{"attempt": 1, "provider": "openrouter", "model": "first", "status": "ok"}]
    assert "test-only-secret" not in str(events)


def test_fallback_publishes_only_successful_answer_and_records_attempts(monkeypatch):
    calls = []
    def invoke(prompt, model, cred, report, on_token, **kwargs):
        calls.append(model)
        assert on_token is None  # partial failed output cannot reach the socket
        if model == "first": raise ProviderError("PROVIDER_UNREACHABLE", "openrouter")
        return "complete fallback answer"
    monkeypatch.setattr(nodes, "call_llm", invoke)
    events = list(run_stream(graph(), {"message": "hello"}, resolve=CREDS.__getitem__))
    assert calls == ["first", "second"] and events[-1]["state"]["answer"] == "complete fallback answer"
    assert "".join(e["delta"] for e in events if e["type"] == "node_token") == "complete fallback answer"
    attempts = next(e["model_attempts"] for e in events if e["type"] == "node_finished" and e["node"] == "m")
    assert [a["status"] for a in attempts] == ["error", "ok"] and attempts[0]["code"] == "PROVIDER_UNREACHABLE"


@pytest.mark.parametrize("code,expected", [("PROVIDER_AUTH_FAILED", 1), ("PROVIDER_BAD_RESPONSE", 2), ("MODEL_NOT_FOUND", 2)])
def test_failure_policy_is_bounded_and_auth_is_not_hidden(monkeypatch, code, expected):
    calls = []
    def invoke(prompt, model, cred, report, on_token, **kwargs):
        calls.append(model); raise ProviderError(code, cred["provider"], "test failure", model=model)
    monkeypatch.setattr(nodes, "call_llm", invoke)
    events = list(run_stream(graph(), {"message": "hello"}, resolve=CREDS.__getitem__))
    assert events[-1]["type"] == "error" and len(calls) == expected
    assert len(events[-1]["model_attempts"]) == expected
    assert not [e for e in events if e["type"] == "node_token"]


def test_permission_error_is_checked_before_any_paid_call():
    calls = []
    def deny(_): raise AppError("CREDENTIAL_NOT_FOUND")
    with pytest.raises(AppError, match="Credential"):
        model_policy.run(DATA, CREDS["primary"], deny, lambda *args: calls.append(args), None, lambda _: None)
    assert calls == []


def test_cancellation_and_timeout_do_not_start_fallback(monkeypatch):
    cancelled, calls = [False], []
    def invoke(model, _):
        calls.append(model); cancelled[0] = True
        raise ProviderError("PROVIDER_UNREACHABLE", "openrouter")
    with pytest.raises(CancelledError):
        model_policy.run(DATA, CREDS["primary"], CREDS.__getitem__, invoke, None, lambda _: None, lambda: cancelled[0])
    assert calls == ["first"]
    times = iter([0, 0, 6]); calls.clear()
    monkeypatch.setattr(model_policy.time, "monotonic", lambda: next(times))
    with pytest.raises(NodeTimeoutError):
        model_policy.run({**DATA, "timeout": 5}, CREDS["primary"], CREDS.__getitem__, invoke, None, lambda _: None)
    assert calls == ["first"]


@pytest.mark.parametrize("policy", [{}, [], True, {"credential_id": "backup"}, {"credential_id": "backup", "model": " "},
    {"credential_id": "primary", "model": "first"}, {"credential_id": "backup", "model": "second", "secret": "no"}])
def test_invalid_policy_is_a_translatable_validation_issue(policy):
    issues = validate(graph({**DATA, "fallback": policy}))
    assert any(getattr(e, "code", None) == "MODEL_FALLBACK_INVALID" for e in issues)


def test_no_policy_keeps_live_streaming_and_mock_never_resolves_credentials(monkeypatch):
    data = {k: v for k, v in DATA.items() if k != "fallback"}
    def invoke(prompt, model, cred, report, on_token, **kwargs):
        assert on_token is not None; on_token("live"); return "live"
    monkeypatch.setattr(nodes, "call_llm", invoke)
    events = list(run_stream(graph(data), {"message": "hello"}, resolve=CREDS.__getitem__))
    assert events[-1]["state"]["answer"] == "live"
    monkeypatch.undo()
    def deny(_): raise AssertionError("offline test must not read credentials")
    events = list(run_stream(graph(), {"message": "hello"}, resolve=deny, ports=Ports(mock_models=True)))
    assert events[-1]["type"] == "run_finished" and "[mock:" in events[-1]["state"]["answer"]


def test_non_chat_credential_is_rejected_and_templates_clear_alternate_reference():
    def resolve(_): return {"provider": "smtp"}
    with pytest.raises(Exception, match="chat model"):
        model_policy.run(DATA, CREDS["primary"], resolve, lambda *_: "must not call", None, lambda _: None)
    clean = sanitize(graph())
    assert clean["nodes"][1]["data"]["fallback"] == {"credential_id": "", "model": "second"}
    for export in (to_python, to_typescript):  #: exported with the fallback model name, never a credential id
        code = export(graph(), "example").code
        assert '"second"' in code and "backup" not in code and "primary" not in code.replace("primary model", "").replace("primary mock", "")


def test_another_users_alternate_cannot_be_used_by_a_saved_run(monkeypatch):
    a, b = user(), user()
    def cred(owner, name):
        return c.post("/api/credentials", headers=H(owner), json={"name": name, "provider": "ollama"}).json()["data"]["id"]
    primary, other = cred(a, "own"), cred(b, "other")
    wf = graph({**DATA, "credential_id": primary, "fallback": {"credential_id": other, "model": "second"}})
    saved = c.post("/api/workflows", headers=H(a), json=wf).json()["data"]["id"]
    monkeypatch.setattr(nodes, "call_llm", lambda *_args, **_kwargs: pytest.fail("permission must be checked before calling"))
    with c.websocket_connect(f"/ws/run?token={a}") as ws:
        ws.send_json({"workflow_id": saved, "input": {"message": "hello"}})
        while (event := ws.receive_json())["type"] not in ("error", "run_finished"): pass
    assert event["type"] == "error" and event["error"]["code"] == "CREDENTIAL_NOT_FOUND"
