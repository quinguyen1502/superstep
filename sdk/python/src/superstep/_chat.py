"""Headless chat v1. HTTP has no optional dependency; sockets load superstep[chat] lazily."""
from __future__ import annotations

import asyncio
import inspect
import threading
from typing import Optional

import httpx

from ._base import DEFAULT_TIMEOUT, unwrap
from ._chat_core import ChatConfig, async_connect, bad, request_frame, segment, sync_connect, token_value, upload_file
from ._errors import APIConnectionError, ConfigError, SuperstepError


def _data(response):
    try: return response.json()
    except ValueError: return None


def _session(sid): return f"/sessions/{segment(sid)}"
def _rating(sid, tid): return _session(sid) + f"/turns/{segment(tid)}/rating"
def _attachment(sid, aid=None): return _session(sid) + "/attachments" + (f"/{segment(aid)}" if aid is not None else "")
def _expired(error, attempt, token): return attempt == 0 and callable(token) and error.status == 401 and error.code == "CHAT_TOKEN_EXPIRED"


def _revision_body(action, view, turn_id, text, operation_id, expected_last_turn_id):
    if not view.get("capabilities", {}).get(action):
        raise ConfigError("This server does not support this chat action", code="CHAT_EDIT_UNSUPPORTED" if action == "edit" else "CHAT_REGENERATE_UNSUPPORTED")
    body = dict(turn_id=segment(turn_id), operation_id=segment(operation_id), expected_last_turn_id=segment(expected_last_turn_id))
    if action == "edit": body["message"] = text
    return body


class _Common:
    def __init__(self, slug, base_url, token, visitor_token, origin, websocket_connect):
        self._config = ChatConfig(slug, base_url, token, visitor_token, origin)
        self._connect = websocket_connect
        self._active = set()
        self._closed = False

    @property
    def visitor_token(self):
        value = self._config.visitor
        return value if self._config.token is None and value != "new" else None

    def _request(self, method, path, auth, attempt, body, files):
        if self._closed: raise ConfigError("This chat client is closed", code="CHAT_CLIENT_CLOSED")
        # Construct independently: never inherit workflow auth, cookies, default params or headers.
        return httpx.Request(method, self._config.base + self._config.root + path, headers=self._config.headers(auth),
            json=body, files=files(attempt) if files else None)

    def _read(self, response, binary):
        if binary and response.is_success: return response
        return self._config.capture(unwrap(response.status_code, dict(response.headers), _data(response)))

    def _stream(self, stream_type, kind, sid, value, *, node=None, attachments=None, locale=None, edit_operation_id=None, **options):
        frame = request_frame(kind, sid, value, node, attachments, locale)
        if edit_operation_id is not None: frame["edit_operation_id"] = segment(edit_operation_id)
        if self._closed: raise ConfigError("This chat client is closed", code="CHAT_CLIENT_CLOSED")
        stream = stream_type(self, sid, frame, **options)
        self._active.add(stream)
        return stream

    def _revision_stream(self, stream_type, revision, options):
        return self._stream(stream_type, "message", revision["session"]["id"], revision["message"], attachments=revision["attachment_ids"],
                            edit_operation_id=revision["operation_id"], prepared_edit=revision, **options)


class ChatClient(_Common):
    """Sync chat client. token is a user JWT or a zero-argument refresh callback, never an app-key secret."""
    def __init__(self, slug: str, *, base_url: str, token=None, visitor_token: Optional[str] = None,
                 origin: Optional[str] = None, http_client: Optional[httpx.Client] = None,
                 timeout: float = DEFAULT_TIMEOUT, websocket_connect=None):
        super().__init__(slug, base_url, token, visitor_token, origin, websocket_connect or sync_connect)
        self._http, self._owns_http = http_client or httpx.Client(timeout=timeout), http_client is None
        self._bootstrap_lock = threading.Lock()
        self.attachments, self.ratings = Attachments(self), Ratings(self)

    def _auth(self):
        token = self._config.token
        if token is None: return dict(type="auth", visitor=self._config.visitor)
        value = token() if callable(token) else token
        if inspect.isawaitable(value):
            if inspect.iscoroutine(value): value.close()
            raise ConfigError("Use AsyncChatClient for an async token callback", code="CONFIG_INVALID")
        return dict(type="auth", token=token_value(value))

    def _send(self, method, path, body=None, files=None, binary=False):
        for attempt in range(2):
            request = self._request(method, path, self._auth(), attempt, body, files)
            try: response = self._http.send(request, auth=None, follow_redirects=False)
            except httpx.HTTPError: raise APIConnectionError("The request could not reach the Superstep server", code="CONNECTION_ERROR") from None
            try: return self._read(response, binary)
            except SuperstepError as error:
                if not _expired(error, attempt, self._config.token): raise
        raise AssertionError("unreachable")

    def _identity(self):
        if self._config.token is not None or self._config.visitor != "new": return None
        with self._bootstrap_lock:
            if self._config.visitor != "new": return None
            data = self._send("GET", "/sessions")
            if not isinstance(data, dict) or not isinstance(data.get("sessions"), list) or not self.visitor_token: raise bad()
            return data

    def info(self): return self._send("GET", "")

    def start(self, *, embed=False):
        self._identity()
        return self._send("POST", "/sessions", dict(embed=embed))

    def list(self):
        initial = self._identity()
        return initial if initial is not None else self._send("GET", "/sessions")

    def get(self, session_id):
        self._identity()
        return self._send("GET", _session(session_id))

    def turns(self, session_id, *, after=None):
        self._identity()
        return self._send("GET", _session(session_id) + "/turns" + (f"?after={segment(after)}" if after else ""))

    def send(self, session_id, text, **options):
        from ._chat_stream import ChatStream
        return self._stream(ChatStream, "message", session_id, text, **options)

    def prepare_edit(self, session_id, turn_id, text, *, operation_id, expected_last_turn_id):
        """Create a branch without executing. Keep operation_id when recovering the same intent."""
        body = _revision_body("edit", self.get(session_id), turn_id, text, operation_id, expected_last_turn_id)
        return self._send("POST", _session(session_id) + "/edits", body)

    def prepare_regenerate(self, session_id, turn_id, *, operation_id, expected_last_turn_id):
        body = _revision_body("regenerate", self.get(session_id), turn_id, None, operation_id, expected_last_turn_id)
        return self._send("POST", _session(session_id) + "/regenerations", body)

    def regenerate(self, session_id, turn_id, *, operation_id, expected_last_turn_id, **options):
        """Fresh workflow execution after confirmation; Human answers are asked again."""
        from ._chat_stream import ChatStream
        revision = self.prepare_regenerate(session_id, turn_id, operation_id=operation_id, expected_last_turn_id=expected_last_turn_id)
        return self._revision_stream(ChatStream, revision, options)

    def edit(self, session_id, turn_id, text, *, operation_id, expected_last_turn_id, **options):
        """Execute an edit after confirming that external actions may repeat. Duplicate intents only recover history."""
        from ._chat_stream import ChatStream
        edit = self.prepare_edit(session_id, turn_id, text, operation_id=operation_id, expected_last_turn_id=expected_last_turn_id)
        return self._revision_stream(ChatStream, edit, options)

    def answer(self, session_id, response, **options):
        from ._chat_stream import ChatStream
        return self._stream(ChatStream, "answer", session_id, response, **options)

    def cancel(self, session_id=None):
        for stream in tuple(self._active):
            if session_id is None or session_id == stream.session_id: stream.cancel()

    def close(self):
        if self._closed: return
        for stream in tuple(self._active): stream.close()
        self._closed = True
        if self._owns_http: self._http.close()

    def __enter__(self): return self
    def __exit__(self, *exc): self.close()


class AsyncChatClient(_Common):
    """Async counterpart. Use async with on clients and streams for deterministic early-exit cleanup."""
    def __init__(self, slug: str, *, base_url: str, token=None, visitor_token: Optional[str] = None,
                 origin: Optional[str] = None, http_client: Optional[httpx.AsyncClient] = None,
                 timeout: float = DEFAULT_TIMEOUT, websocket_connect=None):
        super().__init__(slug, base_url, token, visitor_token, origin, websocket_connect or async_connect)
        self._http, self._owns_http = http_client or httpx.AsyncClient(timeout=timeout), http_client is None
        self._bootstrap_lock = None
        self.attachments, self.ratings = AsyncAttachments(self), AsyncRatings(self)

    async def _auth(self):
        token = self._config.token
        if token is None: return dict(type="auth", visitor=self._config.visitor)
        value = token() if callable(token) else token
        if inspect.isawaitable(value): value = await value
        return dict(type="auth", token=token_value(value))

    async def _send(self, method, path, body=None, files=None, binary=False):
        for attempt in range(2):
            request = self._request(method, path, await self._auth(), attempt, body, files)
            try: response = await self._http.send(request, auth=None, follow_redirects=False)
            except httpx.HTTPError: raise APIConnectionError("The request could not reach the Superstep server", code="CONNECTION_ERROR") from None
            try: return self._read(response, binary)
            except SuperstepError as error:
                if not _expired(error, attempt, self._config.token): raise
        raise AssertionError("unreachable")

    async def _identity(self):
        if self._config.token is not None or self._config.visitor != "new": return None
        if self._bootstrap_lock is None: self._bootstrap_lock = asyncio.Lock()
        async with self._bootstrap_lock:
            if self._config.visitor != "new": return None
            data = await self._send("GET", "/sessions")
            if not isinstance(data, dict) or not isinstance(data.get("sessions"), list) or not self.visitor_token: raise bad()
            return data

    async def info(self): return await self._send("GET", "")

    async def start(self, *, embed=False):
        await self._identity()
        return await self._send("POST", "/sessions", dict(embed=embed))

    async def list(self):
        initial = await self._identity()
        return initial if initial is not None else await self._send("GET", "/sessions")

    async def get(self, session_id):
        await self._identity()
        return await self._send("GET", _session(session_id))

    async def turns(self, session_id, *, after=None):
        await self._identity()
        return await self._send("GET", _session(session_id) + "/turns" + (f"?after={segment(after)}" if after else ""))

    def send(self, session_id, text, **options):
        from ._chat_stream import AsyncChatStream
        return self._stream(AsyncChatStream, "message", session_id, text, **options)

    async def prepare_edit(self, session_id, turn_id, text, *, operation_id, expected_last_turn_id):
        body = _revision_body("edit", await self.get(session_id), turn_id, text, operation_id, expected_last_turn_id)
        return await self._send("POST", _session(session_id) + "/edits", body)

    async def prepare_regenerate(self, session_id, turn_id, *, operation_id, expected_last_turn_id):
        body = _revision_body("regenerate", await self.get(session_id), turn_id, None, operation_id, expected_last_turn_id)
        return await self._send("POST", _session(session_id) + "/regenerations", body)

    async def regenerate(self, session_id, turn_id, *, operation_id, expected_last_turn_id, **options):
        from ._chat_stream import AsyncChatStream
        revision = await self.prepare_regenerate(session_id, turn_id, operation_id=operation_id, expected_last_turn_id=expected_last_turn_id)
        return self._revision_stream(AsyncChatStream, revision, options)

    async def edit(self, session_id, turn_id, text, *, operation_id, expected_last_turn_id, **options):
        from ._chat_stream import AsyncChatStream
        edit = await self.prepare_edit(session_id, turn_id, text, operation_id=operation_id, expected_last_turn_id=expected_last_turn_id)
        return self._revision_stream(AsyncChatStream, edit, options)

    def answer(self, session_id, response, **options):
        from ._chat_stream import AsyncChatStream
        return self._stream(AsyncChatStream, "answer", session_id, response, **options)

    async def cancel(self, session_id=None):
        for stream in tuple(self._active):
            if session_id is None or session_id == stream.session_id: await stream.cancel()

    async def aclose(self):
        if self._closed: return
        for stream in tuple(self._active): await stream.aclose()
        self._closed = True
        if self._owns_http: await self._http.aclose()

    async def __aenter__(self): return self
    async def __aexit__(self, *exc): await self.aclose()


class Attachments:
    def __init__(self, chat): self._chat = chat
    def upload(self, session_id, file, *, filename=None, content_type=None):
        self._chat._identity()
        return self._chat._send("POST", _attachment(session_id), files=upload_file(file, filename, content_type))
    def download(self, session_id, attachment_id):
        self._chat._identity()
        return self._chat._send("GET", _attachment(session_id, attachment_id), binary=True)
    def delete(self, session_id, attachment_id):
        self._chat._identity()
        return self._chat._send("DELETE", _attachment(session_id, attachment_id))


class AsyncAttachments:
    def __init__(self, chat): self._chat = chat
    async def upload(self, session_id, file, *, filename=None, content_type=None):
        await self._chat._identity()
        return await self._chat._send("POST", _attachment(session_id), files=upload_file(file, filename, content_type))
    async def download(self, session_id, attachment_id):
        await self._chat._identity()
        return await self._chat._send("GET", _attachment(session_id, attachment_id), binary=True)
    async def delete(self, session_id, attachment_id):
        await self._chat._identity()
        return await self._chat._send("DELETE", _attachment(session_id, attachment_id))


class Ratings:
    def __init__(self, chat): self._chat = chat
    def put(self, session_id, turn_id, value, *, comment=None):
        self._chat._identity()
        return self._chat._send("PUT", _rating(session_id, turn_id), dict(value=value, **({"comment": comment} if comment is not None else {})))
    def delete(self, session_id, turn_id):
        self._chat._identity()
        return self._chat._send("DELETE", _rating(session_id, turn_id))


class AsyncRatings:
    def __init__(self, chat): self._chat = chat
    async def put(self, session_id, turn_id, value, *, comment=None):
        await self._chat._identity()
        return await self._chat._send("PUT", _rating(session_id, turn_id), dict(value=value, **({"comment": comment} if comment is not None else {})))
    async def delete(self, session_id, turn_id):
        await self._chat._identity()
        return await self._chat._send("DELETE", _rating(session_id, turn_id))
