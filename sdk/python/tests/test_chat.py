"""Same HTTP/socket conversation contract for sync and async clients, using recorded backend v1 frames."""
import asyncio
import copy
import inspect
import io
import json
from collections import deque
from pathlib import Path

import httpx
import pytest

from superstep import (AsyncClient, Client, ChatClient, AsyncChatClient, APIConnectionError, AuthenticationError,
    ConfigError, PermissionDeniedError, mint_chat_token)
from superstep._chat_core import decode
from conftest import env, err

ROOT = Path(__file__).resolve().parents[3]
RECORDED = json.loads((ROOT / "sdk/typescript/test/fixtures/chat-v1-recorded.json").read_text())
SID = "recorded-session"


class Socket:
    def __init__(self, wire, script=None):
        self.wire, self.script, self.closed = wire, script, False
        self.frames, self.sent = deque([RECORDED["frames"][0]]), []
    def recv(self, timeout=None):
        if not self.frames: raise EOFError()
        return json.dumps(self.frames.popleft())
    def send(self, data):
        frame = json.loads(data); self.sent.append(frame)
        if frame["type"] in ("message", "answer"):
            self.wire.writes += 1
            if self.script: self.script(self)
            else: self.wire.saved = True; self.frames.extend(RECORDED["frames"][1:])
        elif frame["type"] == "cancel":
            self.wire.cancels += 1; self.wire.saved = True; self.wire.status = "cancelled"
            self.frames.append(dict(type="done", v=1, seq=100, status="cancelled", run_id="recorded-run"))
    def close(self): self.closed = True


class AsyncSocket:
    def __init__(self, socket): self.socket = socket
    async def send(self, data): self.socket.send(data)
    async def recv(self): await asyncio.sleep(0); return self.socket.recv()
    async def close(self): self.socket.close()


class Wire:
    def __init__(self, asynchronous, scripts=()):
        self.asynchronous, self.scripts = asynchronous, list(scripts)
        self.saved, self.status, self.writes, self.cancels = False, "ok", 0, 0
        self.sockets, self.requests, self.urls, self.options = [], [], [], []
        self.override = None
        kwargs = dict(transport=httpx.MockTransport(self.http), headers={"X-Workflow-Token": "wft-private", "Authorization": "Bearer studio-private"},
                      cookies={"studio-session": "cookie-private"}, auth=("default-user", "default-password"))
        self.http_client = httpx.AsyncClient(**kwargs) if asynchronous else httpx.Client(**kwargs)

    def http(self, request):
        self.requests.append(request)
        if self.override:
            response = self.override(request)
            if response is not None: return response
        path = request.url.path
        visitor = {"visitor_token": "fixture-visitor"} if request.headers.get("X-Chat-Visitor") == "new" else {}
        if path.endswith("/sessions"):
            return env({"sessions": [], **visitor} if request.method == "GET" else {**RECORDED["session"], **visitor})
        if path.endswith("/" + SID): return env({**RECORDED["session"], "turns": RECORDED["session"]["turns"] if self.saved else []})
        if path.endswith("/turns"):
            rows = copy.deepcopy(RECORDED["session"]["turns"]) if self.saved else []
            for turn in rows:
                if turn["role"] == "assistant": turn["status"] = self.status
            after = request.url.params.get("after")
            if after in [turn["id"] for turn in rows]: rows = rows[next(i for i, turn in enumerate(rows) if turn["id"] == after) + 1:]
            return env(dict(turns=rows))
        if path.endswith("/attachments"): return env(dict(id="file-fixture", name="note.txt", size=3))
        if "/attachments/" in path and request.method == "GET": return httpx.Response(200, content=b"abc")
        if request.method == "DELETE": return env(dict(ok=True))
        if path.endswith("/rating"): return env(json.loads(request.content))
        return env(dict(slug="sdk-fixture", title="SDK fixture"))

    def connect(self, url, **kwargs):
        self.urls.append(url); self.options.append(kwargs)
        socket = Socket(self, self.scripts[len(self.sockets)] if len(self.sockets) < len(self.scripts) else None)
        self.sockets.append(socket)
        return socket

    async def async_connect(self, url, **kwargs): return AsyncSocket(self.connect(url, **kwargs))

    def client(self, **kwargs):
        cls = AsyncChatClient if self.asynchronous else ChatClient
        return cls("sdk-fixture", base_url="https://superstep.test", http_client=self.http_client,
            websocket_connect=self.async_connect if self.asynchronous else self.connect,
            **({"visitor_token": "fixture-visitor"} if not kwargs else kwargs))


async def maybe(value): return await value if inspect.isawaitable(value) else value


@pytest.mark.parametrize("action", ["edit", "regenerate"])
async def test_edit_uses_branch_and_repeated_intent_recovers_without_another_socket(mode, action):
    operation = "edits" if action == "edit" else "regenerations"
    wire = Wire(mode); chat = wire.client(); branch = "edited-session"
    def respond(request):
        if request.url.path.endswith("/" + SID):
            return env({**RECORDED["session"], "capabilities": {"edit": True, "regenerate": True}})
        if request.url.path.endswith("/" + operation):
            body = json.loads(request.content)
            if action == "regenerate": assert "message" not in body
            assert body["operation_id"] == "intent-12345678" and body["expected_last_turn_id"] == "recorded-answer"
            return env(dict(session={**RECORDED["session"], "id": branch}, operation_id=body["operation_id"],
                            run_id="recorded-run", message="Edited text", attachment_ids=[], state="finished" if wire.saved else "prepared"))
        if request.url.path.endswith("/" + branch):
            return env({**RECORDED["session"], "id": branch, "turns": RECORDED["session"]["turns"] if wire.saved else []})
    wire.override = respond
    options = dict(operation_id="intent-12345678", expected_last_turn_id="recorded-answer", recovery_interval=0)
    revise = lambda: chat.edit(SID, "recorded-user", "Edited text", **options) if action == "edit" else chat.regenerate(SID, "recorded-answer", **options)
    stream = await maybe(revise())
    await drain(stream)
    assert stream.result.session_id == branch and stream.result.status == "ok"
    frame = wire.sockets[0].sent[1]
    assert frame["chat_session_id"] == branch and frame["edit_operation_id"] == options["operation_id"]
    repeated = await maybe(revise())
    await drain(repeated)
    assert repeated.result.recovered and len(wire.sockets) == wire.writes == 1


@pytest.mark.parametrize("action", ["edit", "regenerate"])
async def test_revision_recovery_after_later_branch_messages_does_not_write(mode, action):
    wire = Wire(mode); wire.saved = True; chat = wire.client(); branch = "continued-branch"
    rows = [*RECORDED["session"]["turns"],
            {**RECORDED["session"]["turns"][0], "id": "later-root", "run_id": "later-run"},
            {**RECORDED["session"]["turns"][1], "id": "later-answer", "run_id": "later-run"}]
    def respond(request):
        if request.url.path.endswith("/" + SID): return env({**RECORDED["session"], "capabilities": {"edit": True, "regenerate": True}})
        if request.url.path.endswith("/edits") or request.url.path.endswith("/regenerations"):
            return env(dict(session={**RECORDED["session"], "id": branch}, operation_id="old-intent", run_id="recorded-run", message="text", attachment_ids=[], state="finished"))
        if request.url.path.endswith("/" + branch): return env({**RECORDED["session"], "id": branch, "turns": rows})
        if request.url.path.endswith("/turns"):
            after = request.url.params.get("after")
            i = next((i for i, turn in enumerate(rows) if turn["id"] == after), -1)
            return env({"turns": rows[i + 1:]})
    wire.override = respond
    opts = dict(operation_id="old-intent", expected_last_turn_id="recorded-answer", recovery_interval=0)
    stream = await maybe(chat.edit(SID, "recorded-user", "text", **opts) if action == "edit" else chat.regenerate(SID, "recorded-answer", **opts))
    await drain(stream)
    assert stream.result.run_id == "recorded-run" and stream.result.text == RECORDED["session"]["turns"][1]["text"]
    assert stream.result.recovered and wire.writes == len(wire.sockets) == 0


@pytest.mark.parametrize("action", ["edit", "regenerate"])
async def test_revision_refuses_old_servers_before_posting(mode, action):
    wire = Wire(mode); chat = wire.client()
    with pytest.raises(ConfigError) as error:
        opts = dict(operation_id="intent-1234", expected_last_turn_id="answer")
        await maybe(chat.prepare_edit(SID, "root", "text", **opts) if action == "edit" else chat.prepare_regenerate(SID, "answer", **opts))
    assert error.value.code == ("CHAT_EDIT_UNSUPPORTED" if action == "edit" else "CHAT_REGENERATE_UNSUPPORTED")
    assert not any(request.method == "POST" for request in wire.requests) and wire.writes == 0


async def drain(stream, callback=None):
    events = []
    if hasattr(stream, "__aiter__"):
        async with stream:
            async for event in stream:
                events.append(event)
                if callback: await maybe(callback(event))
    else:
        with stream:
            for event in stream:
                events.append(event)
                if callback: await maybe(callback(event))
    return events


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def mode(request): return request.param


async def test_recorded_stream_result_and_private_transport(mode):
    wire = Wire(mode); chat = wire.client()
    stream = chat.send(SID, "Hello", recovery_interval=0)
    events = await drain(stream)
    assert [e["type"] for e in events if "v" in e] == [e["type"] for e in RECORDED["frames"]]
    assert stream.result.status == "ok" and stream.result.turn_id == "recorded-answer" and not stream.result.recovered
    assert stream.result.text == RECORDED["session"]["turns"][1]["text"]
    assert events[-1]["result"] is stream.result and all(s.closed for s in wire.sockets)
    assert wire.writes == 1 and wire.sockets[0].sent[0] == dict(type="auth", visitor="fixture-visitor")
    for request in wire.requests:
        assert "authorization" not in request.headers and "cookie" not in request.headers and "x-workflow-token" not in request.headers
        assert b"private" not in str(request.url).encode()
    await maybe(chat.aclose() if mode else chat.close())
    assert not wire.http_client.is_closed  # borrowed transport belongs to the parent
    await maybe(wire.http_client.aclose() if mode else wire.http_client.close())


async def test_sessions_files_ratings_and_identity_bootstrap(mode):
    wire = Wire(mode); chat = wire.client(visitor_token=None)
    assert (await maybe(chat.start()))["id"] == SID and chat.visitor_token == "fixture-visitor"
    assert (await maybe(chat.list()))["sessions"] == []
    assert (await maybe(chat.info()))["slug"] == "sdk-fixture"
    file = await maybe(chat.attachments.upload(SID, io.BytesIO(b"abc"), filename="note.txt", content_type="text/plain"))
    assert file["id"] == "file-fixture" and b'filename="note.txt"' in wire.requests[-1].content
    assert (await maybe(chat.attachments.download(SID, file["id"]))).content == b"abc"
    assert await maybe(chat.attachments.delete(SID, file["id"])) == dict(ok=True)
    assert await maybe(chat.ratings.put(SID, "recorded-answer", "down", comment="More context")) == dict(value="down", comment="More context")
    assert await maybe(chat.ratings.delete(SID, "recorded-answer")) == dict(ok=True)
    assert sum(r.headers.get("x-chat-visitor") == "new" for r in wire.requests) == 1


async def test_http_expiry_once_without_default_workflow_or_studio_auth(mode):
    wire = Wire(mode); tokens = []
    def token(): tokens.append(1); return "short-token"
    wire.override = lambda r: err("CHAT_TOKEN_EXPIRED", 401) if len(wire.requests) == 1 else None
    chat = wire.client(token=token)
    await maybe(chat.info())
    assert len(tokens) == 2
    assert all(r.headers["authorization"] == "Bearer short-token" and "cookie" not in r.headers and "x-workflow-token" not in r.headers for r in wire.requests)
    wire.override = lambda r: err("CHAT_TOKEN_EXPIRED", 401)
    with pytest.raises(AuthenticationError): await maybe(chat.start())
    assert len(tokens) == 4


@pytest.mark.parametrize("code,status,cls", [("CHAT_APP_KEY_REVOKED", 401, AuthenticationError), ("CHAT_ORIGIN_FORBIDDEN", 403, PermissionDeniedError)])
async def test_refusals_never_refresh(mode, code, status, cls):
    wire = Wire(mode); calls = []
    def token(): calls.append(1); return "short-token"
    wire.override = lambda r: err(code, status)
    with pytest.raises(cls): await maybe(wire.client(token=token).list())
    assert len(calls) == 1


async def test_socket_expiry_only_retries_before_execution(mode):
    reject = lambda s: s.frames.append(dict(type="error", v=1, seq=1, error=dict(code="CHAT_TOKEN_EXPIRED", message="expired")))
    wire = Wire(mode, [reject]); stream = wire.client(token=lambda: "short-token").send(SID, "Hello", recovery_interval=0)
    await drain(stream)
    assert stream.result.status == "ok" and len(wire.sockets) == 2
    assert wire.urls == ["wss://superstep.test/ws/public/v1/chat/sdk-fixture"] * 2
    assert all(s.sent[0] == dict(type="auth", token="short-token") for s in wire.sockets)
    def started_then_expired(s):
        s.frames.append(dict(type="run_started", v=1, seq=1, run_id="recorded-run"))
        s.frames.append(dict(type="error", v=1, seq=2, error=dict(code="CHAT_TOKEN_EXPIRED", message="expired")))
    wire = Wire(mode, [started_then_expired])
    with pytest.raises(AuthenticationError): await drain(wire.client(token=lambda: "short-token").send(SID, "Hello"))
    assert wire.writes == 1


@pytest.mark.parametrize("known,saved", [(True, True), (True, False), (False, True)])
async def test_interruption_recovers_only_confirmed_new_turn_without_resend(mode, known, saved):
    def dropped(s):
        s.wire.saved = saved
        if known: s.frames.append(dict(type="run_started", v=1, seq=1, run_id="recorded-run"))
    wire = Wire(mode, [dropped]); stream = wire.client().send(SID, "Hello", after="last-seen", recovery_attempts=2, recovery_interval=0)
    if known and saved:
        events = await drain(stream)
        assert stream.result.recovered and stream.result.turn_id == "recorded-answer"
        assert any(e["type"] == "history" for e in events)
        assert any(r.url.params.get("after") == "last-seen" for r in wire.requests)
    else:
        with pytest.raises(APIConnectionError) as error: await drain(stream)
        assert error.value.code == "CHAT_STREAM_INTERRUPTED" and stream.result is None
    assert wire.writes == 1 and len(wire.sockets) == 1


async def test_unknown_duplicate_frames_and_structured_answer(mode):
    def additive(s):
        s.wire.saved = True
        s.frames.append(dict(type="future_event", seq=0, v=1))
        for frame in RECORDED["frames"][1:]: s.frames.extend([frame, frame])
    wire = Wire(mode, [additive]); stream = wire.client().answer(SID, {"approved": True}, node="ask", recovery_interval=0)
    events = await drain(stream)
    assert sum(e["type"] == "token" for e in events) == sum(e["type"] == "token" for e in RECORDED["frames"])
    assert wire.sockets[0].sent[1] == dict(type="answer", chat_session_id=SID, node="ask", response=dict(approved=True))


async def test_cancel_releases_socket(mode):
    def holding(s): s.frames.append(dict(type="run_started", v=1, seq=1, run_id="recorded-run"))
    wire = Wire(mode, [holding]); chat = wire.client(); stream = chat.send(SID, "Hold", recovery_interval=0)
    def cancel(event):
        if event["type"] == "run_started": return chat.cancel(SID)
    await drain(stream, cancel)
    assert stream.result.status == "cancelled" and wire.cancels == 1 and wire.sockets[0].closed


async def test_invalid_protocol_never_replays(mode):
    wire = Wire(mode, [lambda s: s.frames.append(dict(type="token", v=2, seq=1, delta="bad"))])
    with pytest.raises(APIConnectionError) as error: await drain(wire.client().send(SID, "Hello"))
    assert error.value.code == "BAD_RESPONSE" and wire.writes == 1


def test_signed_token_shared_vectors(monkeypatch):
    vectors = json.loads((ROOT / "sdk/fixtures/chat-token-vectors.json").read_text())["vectors"]
    for vector in vectors:
        monkeypatch.setattr("superstep._chat_token.time.time", lambda: vector["issuedAt"])
        options = vector["options"]
        assert mint_chat_token(options["keyId"], options["secret"], options["slug"], options["userId"], options.get("name"), options.get("ttl", 600), options.get("meta")) == vector["token"]
    for changes in [dict(ttl=True), dict(ttl=0), dict(ttl=3601), dict(user_id=""), dict(user_id="\ud800"), dict(name="a" * 81), dict(meta={"x": float("nan")}), dict(meta={"x": "é" * 512}), dict(meta=[])]:
        with pytest.raises(ConfigError) as error: mint_chat_token(**{**dict(key_id="ck_test", secret="synthetic-secret", slug="test", user_id="a"), **changes})
        assert "synthetic-secret" not in str(error.value)


def test_client_configuration_and_decoding(no_env):
    client = Client(base_url="https://superstep.test")
    assert isinstance(client.chat("sdk-fixture"), ChatClient)
    with pytest.raises(ConfigError): client.run()
    client.close()
    for base in ["https://secret@superstep.test", "https://superstep.test?token=secret", "file:///tmp/api"]:
        with pytest.raises(ConfigError): ChatClient("test", base_url=base)
    for frame in [dict(type="token", v=True, seq=1, delta="bad"), dict(type="done", v=1, seq=True, status="ok")]:
        with pytest.raises(APIConnectionError): decode(json.dumps(frame))


async def test_upload_retry_rewinds_binary_stream(mode):
    wire = Wire(mode)
    wire.override = lambda r: err("CHAT_TOKEN_EXPIRED", 401) if len(wire.requests) == 1 else None
    chat = wire.client(token=lambda: "short-token")
    await maybe(chat.attachments.upload(SID, io.BytesIO(b"the complete file"), filename="file.txt"))
    assert len(wire.requests) == 2 and all(b"the complete file" in r.content for r in wire.requests)


async def test_context_exit_and_parent_close_cancel_unfinished_stream(mode):
    def holding(s): s.frames.append(dict(type="run_started", v=1, seq=1, run_id="recorded-run"))
    wire = Wire(mode, [holding]); parent = (AsyncClient if mode else Client)(base_url="https://superstep.test", http_client=wire.http_client)
    chat = parent.chat("sdk-fixture", visitor_token="fixture-visitor", websocket_connect=wire.async_connect if mode else wire.connect)
    stream = chat.send(SID, "Hold")
    if mode:
        iterator = stream.__aiter__()
        assert (await iterator.__anext__())["type"] == "ready"
        assert (await iterator.__anext__())["type"] == "run_started"
    else:
        iterator = iter(stream)
        assert next(iterator)["type"] == "ready" and next(iterator)["type"] == "run_started"
    await maybe(parent.aclose() if mode else parent.close())
    assert wire.sockets[0].closed and wire.cancels == 1 and stream.result is None


async def test_deadline_does_not_retry(mode):
    wire = Wire(mode)
    if mode:
        class TimedSocket(AsyncSocket):
            async def recv(self): await asyncio.sleep(60)
        async def connect(*a, **kw): return TimedSocket(wire.connect(*a, **kw))
    else:
        def connect(*a, **kw):
            socket = wire.connect(*a, **kw)
            def recv(**kw): raise TimeoutError()
            socket.recv = recv
            return socket
    chat = wire.client(); chat._connect = connect
    with pytest.raises(APIConnectionError) as error: await drain(chat.send(SID, "Wait", timeout=0.01))
    assert error.value.code == "CHAT_STREAM_TIMEOUT" and wire.writes == 0 and wire.sockets[0].closed


async def test_async_task_cancellation_releases_socket():
    wire = Wire(True)
    received = asyncio.Event()
    class Holding(AsyncSocket):
        async def recv(self):
            if not self.socket.frames: received.set(); await asyncio.sleep(60)
            return self.socket.recv()
    async def connect(*a, **kw):
        socket = wire.connect(*a, **kw)
        socket.script = lambda s: s.frames.append(dict(type="run_started", v=1, seq=1, run_id="recorded-run"))
        return Holding(socket)
    chat = wire.client(); chat._connect = connect
    task = asyncio.create_task(drain(chat.send(SID, "Hold")))
    await asyncio.wait_for(received.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert wire.cancels == 1 and wire.sockets[0].closed and not chat._active


async def test_redirects_cannot_forward_authentication(mode):
    wire = Wire(mode); wire.override = lambda r: httpx.Response(302, headers={"location": "https://other.test/leak"})
    with pytest.raises(APIConnectionError): await maybe(wire.client(token="user-jwt").info())
    assert len(wire.requests) == 1 and wire.requests[0].url.host == "superstep.test"


def test_base_import_does_not_require_socket_extra(tmp_path):
    import subprocess
    import sys
    code = """import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith('websockets'): raise ImportError('optional dependency unavailable')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from superstep import Client, ConfigError, mint_chat_token
from superstep._chat_core import sync_connect
assert mint_chat_token('ck_test', 'synthetic-secret', 'test', 'user')
try: sync_connect('ws://localhost')
except ConfigError as error: assert error.code == 'CONFIG_MISSING'
else: raise AssertionError('missing extra must be actionable')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("stage", ["history", "token"])
async def test_closing_before_dispatch_never_opens_a_socket(mode, stage):
    wire = Wire(mode); chat = wire.client()
    stream = chat.send(SID, "Do not send")
    def before():
        if stage == "history": stream.close()
        return {"turns": []}
    async def async_before():
        if stage == "history": await stream.aclose()
        return {"turns": []}
    def token(): stream.close(); return "short-token"
    async def async_token(): await stream.aclose(); return "short-token"
    chat.get = async_before if mode else before
    if stage == "token": chat._config.token = async_token if mode else token
    # A callback completing after a host close must not open a new connection.
    if mode: async_before_with_id = lambda _sid: async_before(); chat.get = async_before_with_id
    else: chat.get = lambda _sid: before()
    assert await drain(stream) == []
    assert wire.sockets == [] and wire.writes == 0 and not chat._active
