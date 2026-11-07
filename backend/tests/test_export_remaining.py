"""REQ-0090: per-node model slots, approval extras and managed connections in the exported file.

The generated file is executed. Model calls are the local resolve_model. Telegram is a local HTTP server.
No paid call, and no Studio id or secret value is written into the file."""
import json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import project_export as P, python_export as X
from test_python_export import KEYS, N, E, F

SLOT = {"name": "Slots", "state": [F("message"), F("answer")],
        "nodes": [N("start", "start"),
                  N("m", "llm", prompt="{{state.message}}", model="first", output_field="answer",
                    credential_id="primary-SECRET", fallback={"credential_id": "backup-SECRET", "model": "second"}),
                  N("end", "end")],
        "edges": [E("start", "m"), E("m", "end")]}

POLICY = {"mode": "auto", "max_per_day": 3, "min_confidence": 0.9,
          "rules": [{"field": "state.message", "op": "equals", "value": "rm", "effect": "reject"}],
          "judge": {"credential_id": "judge-SECRET", "model": "gpt-4o-mini", "instructions": "be careful"}}
APPROVAL = {"name": "Approval", "state": [F("message"), F("verdict")],
            "nodes": [N("start", "start"),
                      N("ask", "human", prompt="OK {{state.message}}?", output_field="verdict",
                        approval={"channel": "telegram", "channel_id": "ch-SECRET", "approvers": ["boss-SECRET@x.io"], "auto": POLICY},
                        deadline={"after": "2m", "on_timeout": "escalate", "escalate_to": ["esc-SECRET@x.io"]}),
                      N("end", "end")],
            "edges": [E("start", "ask"), E("ask", "end")]}

DEADLINE = {"name": "Deadline", "state": [F("message"), F("verdict")],
            "nodes": [N("start", "start"),
                      N("ask", "human", prompt="OK?", output_field="verdict",
                        deadline={"after": "1m", "on_timeout": "approve"}),
                      N("end", "end")],
            "edges": [E("start", "ask"), E("ask", "end")]}

MANAGED = {"name": "Managed", "state": [F("message"), F("out", "object")],
           "nodes": [N("start", "start"),
                     N("tg", "mcp", tool="send_message", arguments={"text": "{{state.message}}"}, output_field="out",
                       server_id="srv-SECRET", _managed_export="telegram"),
                     N("end", "end")],
           "edges": [E("start", "tg"), E("tg", "end")]}


def load(code, tmp_path, name):
    path = tmp_path / name
    path.write_text(code)
    ns = {"__name__": name[:-3], "__file__": str(path)}
    exec(compile(code, str(path), "exec"), ns)
    return ns


def test_llm_slots_hide_ids_and_fall_back(tmp_path, monkeypatch):
    for key in (*KEYS, "LLM_CRED_1_PROVIDER", "LLM_CRED_1_API_KEY", "LLM_CRED_1_BASE_URL", "LLM_CRED_2_PROVIDER"):
        monkeypatch.delenv(key, raising=False)
    code = X.to_python(SLOT, "Slots").code
    assert "primary-SECRET" not in code and "backup-SECRET" not in code
    assert 'slot="LLM_CRED_1"' in code and 'fallback_slot="LLM_CRED_2"' in code
    names = P._env_vars(code, P.PY_ENV)
    assert {"LLM_CRED_1_PROVIDER", "LLM_CRED_1_API_KEY", "LLM_CRED_2_PROVIDER", "LLM_CRED_2_API_KEY"} <= set(names)
    offline = load(code, tmp_path, "slots_off.py")
    assert offline["resolve_model"](None, "LLM_CRED_1") == (None, {})
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    live = load(code, tmp_path, "slots_live.py")
    assert live["resolve_model"](None, "LLM_CRED_1")[0] == "openai"
    monkeypatch.setenv("LLM_CRED_1_PROVIDER", "anthropic")
    with pytest.raises(RuntimeError, match="LLM_CRED_1_API_KEY"):
        live["resolve_model"](None, "LLM_CRED_1")
    monkeypatch.setenv("LLM_CRED_1_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_CRED_1_BASE_URL", "https://example.test/v1")
    chosen, kwargs = live["resolve_model"]("openai", "LLM_CRED_1")
    assert chosen == "anthropic" and kwargs == {"api_key": "sk-test", "base_url": "https://example.test/v1"}


def test_approval_rejects_on_a_rule_and_hides_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSTEP_APPROVAL_STATE", str(tmp_path / "approval.json"))
    code = X.to_python(APPROVAL, "Approval").code
    for secret in ("judge-SECRET", "ch-SECRET", "boss-SECRET", "esc-SECRET"):
        assert secret not in code
    assert 'request["channel"] = "telegram"' in code and '"on_timeout": "escalate"' in code and "review_approval(request)" in code
    assert "APPROVAL_TELEGRAM_BOT_TOKEN" in code and "APPROVAL_TELEGRAM_CHAT_ID" in code
    ns = load(code, tmp_path, "approval.py")
    request = {"node": "ask", "question": "rm?", "state": {"message": "rm"},
               "policy": {"mode": "auto", "max_per_day": 3, "min_confidence": 0.9, "rules": POLICY["rules"],
                          "judge": {"model": "gpt-4o-mini", "instructions": "be careful"}}}
    assert ns["review_approval"](request) == "rejected"
    request["policy"] = {**request["policy"], "mode": "suggest"}
    assert ns["review_approval"](request) is None


def test_deadline_approves_when_nobody_answers(tmp_path, monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    code = X.to_python(DEADLINE, "Deadline", example={"input": {"message": "hi"}}).code
    assert '"after": 60.0' in code and '"on_timeout": "approve"' in code
    code = code.replace('"after": 60.0', '"after": 0.2', 1)
    path = tmp_path / "deadline.py"
    path.write_text(code)
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    ran = subprocess.run([sys.executable, "-I", str(path)], cwd=tmp_path, env=env, capture_output=True, text=True,
                         timeout=30, stdin=subprocess.DEVNULL)
    assert ran.returncode == 0, ran.stderr[-2000:]
    assert ">> ask: approved" in ran.stdout and '"verdict": "approved"' in ran.stdout


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        self.server.posts.append(self.rfile.read(size))
        raw = self.server.reply
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        return


@pytest.fixture
def telegram(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.posts, server.status, server.reply = [], 200, b'{"ok": true, "result": {"message_id": 7}}'
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_managed_telegram_is_idempotent_and_does_not_retry_unknown(tmp_path, monkeypatch, telegram):
    for key in (*KEYS, "STUDIO_MCP_ALLOW_PRIVATE", "TELEGRAM_API_URL", "MANAGED_1_SETTINGS", "MANAGED_1_SECRETS"):
        monkeypatch.delenv(key, raising=False)
    code = X.to_python(MANAGED, "Managed").code
    assert "srv-SECRET" not in code and "4242424242" not in code and "bot-SECRET-VALUE" not in code
    assert 'managed_operation("send_message"' in code and '"MANAGED_1"' in code and '"telegram"' in code
    assert {"MANAGED_1_SETTINGS", "MANAGED_1_SECRETS"} <= set(P._env_vars(code, P.PY_ENV))
    monkeypatch.setenv("SUPERSTEP_MANAGED_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("SUPERSTEP_RUN_ID", "remaining")
    ns = load(code, tmp_path, "managed.py")
    assert ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")["outcome"] == "dry_run"
    assert telegram.posts == []
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(RuntimeError, match="MANAGED_1_SETTINGS"):
        ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "1")
    monkeypatch.setenv("TELEGRAM_API_URL", f"http://127.0.0.1:{telegram.server_address[1]}")
    monkeypatch.setenv("MANAGED_1_SETTINGS", json.dumps({"chat_id": "4242424242"}))
    monkeypatch.setenv("MANAGED_1_SECRETS", json.dumps({"bot_token": "bot-SECRET-VALUE"}))
    monkeypatch.setenv("SUPERSTEP_MANAGED_STATE", str(tmp_path / "sent.json"))
    first = ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")
    again = ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")
    assert first == again and first["message_id"] == 7 and len(telegram.posts) == 1
    body = json.loads(telegram.posts[0])
    assert body["chat_id"] == "4242424242" and body["text"] == "hello"
    with pytest.raises(RuntimeError, match="conflicts"):
        ns["managed_operation"]("send_message", {"text": "other"}, "MANAGED_1", "telegram")
    assert len(telegram.posts) == 1
    telegram.status, telegram.reply = 500, b'{"ok": false}'
    monkeypatch.setenv("SUPERSTEP_MANAGED_STATE", str(tmp_path / "unknown.json"))
    with pytest.raises(RuntimeError, match="not retried"):
        ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")
    with pytest.raises(RuntimeError, match="not retried"):
        ns["managed_operation"]("send_message", {"text": "hello"}, "MANAGED_1", "telegram")
    assert len(telegram.posts) == 2


def test_approval_telegram_posts_locally_and_names_a_missing_key(tmp_path, monkeypatch, telegram):
    for key in (*KEYS, "APPROVAL_TELEGRAM_BOT_TOKEN", "APPROVAL_TELEGRAM_CHAT_ID", "TELEGRAM_API_URL"):
        monkeypatch.delenv(key, raising=False)
    code = X.to_python(APPROVAL, "Approval").code
    ns = load(code, tmp_path, "notify.py")
    request = {"node": "ask", "channel": "telegram", "question": "Please review"}
    ns["notify_approval"](request)
    assert telegram.posts == []
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(RuntimeError, match="APPROVAL_TELEGRAM_BOT_TOKEN"):
        ns["notify_approval"](request)
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "1")
    monkeypatch.setenv("TELEGRAM_API_URL", f"http://127.0.0.1:{telegram.server_address[1]}")
    monkeypatch.setenv("APPROVAL_TELEGRAM_BOT_TOKEN", "bot-SECRET-VALUE")
    monkeypatch.setenv("APPROVAL_TELEGRAM_CHAT_ID", "4242424242")
    ns["notify_approval"](request)
    assert len(telegram.posts) == 1
    assert json.loads(telegram.posts[0])["chat_id"] == "4242424242"
    assert "bot-SECRET-VALUE" not in code and "4242424242" not in code
