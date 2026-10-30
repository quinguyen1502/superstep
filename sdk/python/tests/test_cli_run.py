"""run and runs (TASK-0169). The socket is a fake; nothing here needs a server."""
import asyncio
import io
import json
import logging
import sys
from pathlib import Path

import httpx
import pytest

from superstep.cli import run

TOKEN = "pat_should-not-leak"
URL = "http://studio.example"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SUPERSTEP_URL", raising=False)
    monkeypatch.delenv("SUPERSTEP_TOKEN", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)


def invoke(argv, client=None, connect=None):
    out, err = io.StringIO(), io.StringIO()
    from contextlib import redirect_stderr, redirect_stdout
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client, connect=connect)
    return code, out.getvalue(), err.getvalue()


def envelope(data, status=200):
    if status >= 400:
        return httpx.Response(status, json={"success": False, "data": None, "error": data})
    return httpx.Response(status, json={"success": True, "data": data, "error": None})


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def sign_in(monkeypatch):
    monkeypatch.setenv("SUPERSTEP_URL", URL)
    monkeypatch.setenv("SUPERSTEP_TOKEN", TOKEN)


class _CM:
    def __init__(self, sock):
        self.sock = sock

    async def __aenter__(self):
        return self.sock

    async def __aexit__(self, *_exc):
        return False


class FakeSocket:
    """Async iterator of server events. `sent` captures the text frames the CLI writes."""

    def __init__(self, events, sent, block):
        self._events = list(events)
        self.sent = sent
        self.block = block
        self._index = 0

    async def send(self, message):
        self.sent.append(message)

    async def recv(self):
        if self._index >= len(self._events):
            if self.block:
                await asyncio.sleep(30)
            raise StopAsyncIteration
        event = self._events[self._index]
        self._index += 1
        return event

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.recv()


class Connect:
    def __init__(self, events, block=False):
        self.events = events
        self.block = block
        self.sent = []
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        return _CM(FakeSocket(self.events, self.sent, self.block))


def workflows(extra=None):
    """GET /api/workflows returns Inbox. Anything else is a 404 with the given error code."""
    def handler(request: httpx.Request):
        assert request.headers.get("authorization") == "Bearer " + TOKEN
        if request.method == "GET" and request.url.path == "/api/workflows":
            return envelope([{"id": "wf1", "name": "Inbox"}])
        code = extra or "NOT_FOUND"
        return envelope({"code": code, "message": "no"}, status=404)
    return client_for(handler)


def ok_events(state=None):
    return [
        {"type": "run_started", "run_id": "run-1"},
        {"type": "node_started", "node": "step-1", "label": "Greet"},
        {"type": "run_finished", "state": {"answer": "ok"} if state is None else state},
        {"type": "run_summary", "run_id": "run-1", "status": "ok"},
    ]


def test_websockets_pin_is_only_on_the_cli_extra():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    base, _extra = text.split("[project.optional-dependencies]", 1)
    assert "websockets" not in base
    assert 'cli = ["websockets==15.0.1"]' in text


def test_help_examples():
    code, out, err = invoke(["run", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep run inbox --input sample.json --follow" in err
    code, out, err = invoke(["--lang", "vi", "run", "--help"])
    assert "Ví dụ: superstep run inbox --input sample.json --follow" in err
    code, out, err = invoke(["runs", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep runs list" in err
    code, out, err = invoke(["--lang", "vi", "runs", "--help"])
    assert "Ví dụ: superstep runs list" in err


def test_run_follow_sends_the_file_and_hides_the_token(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    sign_in(monkeypatch)
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps({"question": "hello"}), encoding="utf-8")
    connect = Connect(ok_events())
    code, out, err = invoke(["run", "wf1", "--input", str(sample), "--follow"], client=workflows(), connect=connect)
    assert code == 0 and out == ""
    assert json.loads(connect.sent[0]) == {"workflow_id": "wf1", "input": {"question": "hello"}}
    assert "Started run-1" in err
    assert "node_started step-1" in err
    assert connect.urls and "/ws/run?token=" in connect.urls[0]
    assert "ws://" not in out and "ws://" not in err and "wss://" not in err
    assert TOKEN not in out and TOKEN not in err and TOKEN not in caplog.text


def test_without_follow_trace_lines_are_absent(monkeypatch):
    sign_in(monkeypatch)
    # No run_summary: the socket closing is the end, and a finished run is still ok.
    connect = Connect(ok_events()[:-1])
    code, out, err = invoke(["run", "wf1"], client=workflows(), connect=connect)
    assert code == 0 and out == "" and err == ""
    assert json.loads(connect.sent[0])["input"] == {}
    assert "Started" not in err and "node_started" not in err and "step-1" not in err


def test_json_is_one_final_object(monkeypatch):
    sign_in(monkeypatch)
    connect = Connect(ok_events({"answer": 1}))
    code, out, err = invoke(["run", "wf1", "--json"], client=workflows(), connect=connect)
    assert code == 0 and err == "" and out.count("\n") == 1
    assert json.loads(out) == {"ok": True, "run_id": "run-1", "status": "ok", "final_state": {"answer": 1}}


@pytest.mark.parametrize("status, code, event", [
    ("error", 1, {"type": "error", "node": "step-1", "error": {"message": "boom"}}),
    ("waiting", 2, {"type": "run_waiting", "node": "ask", "prompt": "What is your name?"}),
    ("cancelled", 4, {"type": "run_cancelled"}),
    ("paused", 0, {"type": "run_paused", "node": "next"}),
])
def test_exit_code_follows_the_final_status(monkeypatch, status, code, event):
    sign_in(monkeypatch)
    events = [{"type": "run_started", "run_id": "run-1"}, event, {"type": "run_summary", "run_id": "run-1", "status": status}]
    connect = Connect(events)
    exit_code, out, err = invoke(["run", "wf1"], client=workflows(), connect=connect)
    assert exit_code == code and out == ""
    assert len(connect.sent) == 1
    assert "Started" not in err and "node_started" not in err
    if status == "waiting":
        assert "What is your name?" in err
        assert "Waiting at" not in err
    if status == "paused":
        assert exit_code == 0


def test_local_timeout_sends_cancel_and_exits_3(monkeypatch):
    sign_in(monkeypatch)
    connect = Connect([{"type": "run_started", "run_id": "run-1"}], block=True)
    code, out, err = invoke(["run", "wf1", "--timeout", "0"], client=workflows(), connect=connect)
    assert code == 3 and out == ""
    assert [json.loads(body) for body in connect.sent] == [
        {"workflow_id": "wf1", "input": {}},
        {"type": "cancel"},
    ]
    assert TOKEN not in err


def test_server_timeout_exits_3_without_a_cancel(monkeypatch):
    sign_in(monkeypatch)
    events = [
        {"type": "run_started", "run_id": "run-1"},
        {"type": "error", "status": "timeout", "error": {"message": "timed out"}},
        {"type": "run_summary", "run_id": "run-1", "status": "timeout"},
    ]
    connect = Connect(events)
    code, out, err = invoke(["run", "wf1", "--json"], client=workflows(), connect=connect)
    assert code == 3 and len(connect.sent) == 1
    assert json.loads(out)["ok"] is False and json.loads(out)["status"] == "timeout"


def test_stdin_input_is_one_object(monkeypatch):
    sign_in(monkeypatch)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"q": 1}'))
    connect = Connect(ok_events())
    code, _out, _err = invoke(["run", "wf1", "--input", "-"], client=workflows(), connect=connect)
    assert code == 0
    assert json.loads(connect.sent[0])["input"] == {"q": 1}


def test_runs_list_show_and_cancel(monkeypatch):
    sign_in(monkeypatch)
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.method, request.url.path))
        assert request.headers.get("authorization") == "Bearer " + TOKEN
        if request.url.path == "/api/runs/pending":
            return envelope([{"id": "p1", "workflow_id": "wf1", "workflow_name": "Inbox", "node": "ask", "prompt": "Go?"}])
        if request.url.path == "/api/workflows":
            return envelope([{"id": "wf1", "name": "Inbox"}, {"id": "wf2", "name": "Other"}])
        if request.url.path == "/api/workflows/wf1/runs":
            return envelope([{"id": "h1", "status": "ok", "workflow_id": "wf1"}])
        if request.url.path == "/api/runs/h1" and request.method == "GET":
            return envelope({"id": "h1", "status": "cancelled", "workflow_id": "wf1"})
        if request.url.path == "/api/runs/h1/cancel" and request.method == "POST":
            return envelope({"run_id": "h1", "cancel_requested": True})
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)

    http = client_for(handler)
    code, out, err = invoke(["runs", "list"], client=http)
    assert code == 0 and out == ""
    assert "p1" in err and "Inbox" in err and "Go?" in err
    assert ("GET", "/api/runs/pending") in seen

    code, out, err = invoke(["runs", "list", "--workflow", "Inbox"], client=http)
    assert code == 0 and out == ""
    assert "h1" in err and "ok" in err
    assert ("GET", "/api/workflows/wf1/runs") in seen
    assert not any(path.endswith("/Inbox/runs") for _method, path in seen)

    code, out, err = invoke(["runs", "cancel", "h1", "--json"], client=http)
    assert code == 0 and err == ""
    assert json.loads(out) == {"ok": True, "run_id": "h1", "cancel_requested": True}
    assert ("POST", "/api/runs/h1/cancel") in seen

    code, out, err = invoke(["runs", "show", "h1"], client=http)
    assert code == 0 and out == ""
    assert "h1" in err and "cancelled" in err
    assert ("GET", "/api/runs/h1") in seen


def test_two_workflows_with_the_same_name_are_ambiguous(monkeypatch):
    sign_in(monkeypatch)
    connect = Connect([])

    def handler(request: httpx.Request):
        if request.url.path == "/api/workflows":
            return envelope([{"id": "a", "name": "Same"}, {"id": "b", "name": "Same"}])
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)

    http = client_for(handler)
    for argv in (["run", "Same", "--json"], ["runs", "list", "--workflow", "Same", "--json"]):
        code, out, err = invoke(argv, client=http, connect=connect)
        assert code == 1 and err == ""
        body = json.loads(out)
        assert body["ok"] is False and body["error"]["code"] == "AMBIGUOUS"
        assert "id" in body["error"]["message"]
    assert connect.urls == []


def test_missing_workflow_uses_the_server_code(monkeypatch):
    sign_in(monkeypatch)

    def handler(request: httpx.Request):
        if request.url.path == "/api/workflows":
            return envelope([{"id": "wf1", "name": "Inbox"}])
        assert request.url.path == "/api/workflows/missing"
        return envelope({"code": "WORKFLOW_NOT_FOUND", "message": "Workflow not found"}, status=404)

    code, out, err = invoke(["run", "missing", "--json"], client=client_for(handler))
    assert code == 1 and err == ""
    assert json.loads(out)["error"]["code"] == "WORKFLOW_NOT_FOUND"


def test_run_requires_a_token(monkeypatch):
    monkeypatch.setenv("SUPERSTEP_URL", URL)
    connect = Connect([])
    code, out, err = invoke(["run", "wf1"], connect=connect)
    assert code == 1 and out == "" and "superstep login" in err
    assert connect.urls == [] and TOKEN not in err
