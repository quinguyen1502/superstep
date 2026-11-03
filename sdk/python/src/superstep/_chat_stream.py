"""Pull-based, bounded v1 streams. One socket per message; history recovery never replays a write."""
from __future__ import annotations

import asyncio
import time

from ._chat_core import FrameState, History, json_text, socket_options, stream_limits
from ._errors import APIConnectionError, ConfigError, error_for


def _error(frame):
    error = frame["error"]
    return error_for(401 if error["code"] == "CHAT_TOKEN_EXPIRED" else 400, error["code"], error["message"], error.get("details"))


class _Common:
    def __init__(self, chat, session_id, frame, *, timeout=300.0, after=None, recovery_attempts=20, recovery_interval=0.25, prepared_edit=None):
        stream_limits(timeout, recovery_attempts, recovery_interval)
        self.chat, self.session_id, self.frame = chat, session_id, frame
        self.timeout, self.after = timeout, after
        self.recovery_attempts, self.recovery_interval = recovery_attempts, recovery_interval
        self.result, self._socket, self._closed = None, None, False
        self._deadline = None
        self.prepared_edit = prepared_edit

    def _history(self, before):
        if self.prepared_edit:
            first = next((i for i, t in enumerate(before["turns"]) if t.get("run_id") == self.prepared_edit["run_id"]), len(before["turns"]))
            before = {**before, "turns": before["turns"][:first]}
        return History(before, None if self.prepared_edit else self.after)

    def _edit_recovery(self, frame):
        return bool(self.prepared_edit and frame["type"] == "error" and frame["error"]["code"] == "CHAT_EDIT_STARTED")

    def _left(self):
        if self._deadline is None: return None
        left = self._deadline - time.monotonic()
        if left <= 0: raise APIConnectionError("Chat socket deadline exceeded", code="CHAT_STREAM_TIMEOUT")
        return left

    def _refresh(self, frame, state, attempt):
        return frame["type"] == "error" and frame["error"]["code"] == "CHAT_TOKEN_EXPIRED" and not state.run_id and attempt == 0 and callable(self.chat._config.token)

class ChatStream(_Common):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._iterator = self._run()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed: raise StopIteration
        return next(self._iterator)

    def cancel(self):
        if self._socket is None:
            self.close()
            return
        try: self._socket.send('{"type":"cancel"}')
        except Exception: self._socket.close()

    def _close_socket(self):
        if self._socket is not None:
            try: self._socket.close()
            except Exception: pass
            self._socket = None

    def close(self):
        if self._closed: return
        self._closed = True
        if self._socket is not None:
            try: self._socket.send('{"type":"cancel"}')
            except Exception: pass
        self._close_socket()
        if not self._iterator.gi_running: self._iterator.close()
        self.chat._active.discard(self)

    def __enter__(self): return self
    def __exit__(self, *exc): self.close()

    def _run(self):
        state, interrupted = FrameState(), False
        try:
            history = self._history(self.chat.get(self.session_id))
            if self._closed: return
            self._deadline = None if self.timeout is None else time.monotonic() + self.timeout
            for attempt in range(0 if self.prepared_edit and self.prepared_edit["state"] != "prepared" else 2):
                auth, state, retry = self.chat._auth(), FrameState(), False
                if self._closed: return
                try:
                    try: self._socket = self.chat._connect(self.chat._config.socket_url, **socket_options(self.chat._config.origin, self._left()))
                    except (ConfigError, APIConnectionError): raise
                    except Exception: interrupted = True; break
                    while not self._closed:
                        try: raw = self._socket.recv(timeout=self._left())
                        except TimeoutError: raise APIConnectionError("Chat socket deadline exceeded", code="CHAT_STREAM_TIMEOUT") from None
                        except APIConnectionError: raise
                        except Exception: interrupted = True; break
                        frame = state.take(raw)
                        if frame is None: continue
                        if self._refresh(frame, state, attempt): retry = True; break
                        if self._edit_recovery(frame): interrupted = True; break
                        yield frame
                        if frame["type"] == "error": raise _error(frame)
                        if frame["type"] == "ready" and not state.sent:
                            try:
                                self._socket.send(json_text(auth)); self._socket.send(json_text(self.frame))
                                state.sent = True
                            except Exception: interrupted = True; break
                        if state.done: break
                finally:
                    if self._socket is not None and state.sent and not state.done and not retry and not interrupted:
                        try: self._socket.send('{"type":"cancel"}')
                        except Exception: pass
                    self._close_socket()
                if not retry: break
            if self._closed: return
            if self.prepared_edit:
                state.run_id = state.run_id or self.prepared_edit["run_id"]
                interrupted = interrupted or self.prepared_edit["state"] != "prepared"
            for i in range(self.recovery_attempts):
                rows = history.add(self.chat.turns(self.session_id, after=history.cursor), state.run_id)
                if rows: yield dict(type="history", turns=rows)
                if history.saved or not state.run_id: break
                if i + 1 < self.recovery_attempts: time.sleep(self.recovery_interval)
            self.result = history.result(self.session_id, state, interrupted)
            yield dict(type="result", result=self.result)
        finally:
            self._close_socket(); self._closed = True; self.chat._active.discard(self)


class AsyncChatStream(_Common):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._iterator = self._run()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed: raise StopAsyncIteration
        return await self._iterator.__anext__()

    async def cancel(self):
        if self._socket is None:
            await self.aclose()
            return
        try: await self._socket.send('{"type":"cancel"}')
        except Exception: await self._socket.close()

    async def _close_socket(self):
        if self._socket is not None:
            try: await self._socket.close()
            except Exception: pass
            self._socket = None

    async def aclose(self):
        if self._closed: return
        self._closed = True
        if self._socket is not None:
            try: await self._socket.send('{"type":"cancel"}')
            except Exception: pass
        await self._close_socket()
        if not self._iterator.ag_running: await self._iterator.aclose()
        self.chat._active.discard(self)

    async def __aenter__(self): return self
    async def __aexit__(self, *exc): await self.aclose()

    async def _run(self):
        state, interrupted = FrameState(), False
        try:
            history = self._history(await self.chat.get(self.session_id))
            if self._closed: return
            self._deadline = None if self.timeout is None else time.monotonic() + self.timeout
            for attempt in range(0 if self.prepared_edit and self.prepared_edit["state"] != "prepared" else 2):
                auth, state, retry = await self.chat._auth(), FrameState(), False
                if self._closed: return
                try:
                    try: self._socket = await self.chat._connect(self.chat._config.socket_url, **socket_options(self.chat._config.origin, self._left()))
                    except (ConfigError, APIConnectionError): raise
                    except Exception: interrupted = True; break
                    while not self._closed:
                        try: raw = await asyncio.wait_for(self._socket.recv(), timeout=self._left())
                        except asyncio.TimeoutError: raise APIConnectionError("Chat socket deadline exceeded", code="CHAT_STREAM_TIMEOUT") from None
                        except APIConnectionError: raise
                        except Exception: interrupted = True; break
                        frame = state.take(raw)
                        if frame is None: continue
                        if self._refresh(frame, state, attempt): retry = True; break
                        if self._edit_recovery(frame): interrupted = True; break
                        yield frame
                        if frame["type"] == "error": raise _error(frame)
                        if frame["type"] == "ready" and not state.sent:
                            try:
                                await self._socket.send(json_text(auth)); await self._socket.send(json_text(self.frame))
                                state.sent = True
                            except Exception: interrupted = True; break
                        if state.done: break
                finally:
                    if self._socket is not None and state.sent and not state.done and not retry and not interrupted:
                        try: await self._socket.send('{"type":"cancel"}')
                        except Exception: pass
                    await self._close_socket()
                if not retry: break
            if self._closed: return
            if self.prepared_edit:
                state.run_id = state.run_id or self.prepared_edit["run_id"]
                interrupted = interrupted or self.prepared_edit["state"] != "prepared"
            for i in range(self.recovery_attempts):
                rows = history.add(await self.chat.turns(self.session_id, after=history.cursor), state.run_id)
                if rows: yield dict(type="history", turns=rows)
                if history.saved or not state.run_id: break
                if i + 1 < self.recovery_attempts: await asyncio.sleep(self.recovery_interval)
            self.result = history.result(self.session_id, state, interrupted)
            yield dict(type="result", result=self.result)
        finally:
            await self._close_socket(); self._closed = True; self.chat._active.discard(self)
