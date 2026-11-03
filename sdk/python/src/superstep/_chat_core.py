"""Shared v1 request/protocol logic; sync and async clients only differ in I/O."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from ._errors import APIConnectionError, ConfigError, error_for

DONE = {"ok", "error", "waiting", "cancelled", "timeout"}
TYPES = {"ready", "run_started", "token", "step", "question", "turn", "done", "error"}


def segment(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,200}", value):
        raise ConfigError("Invalid chat resource identifier", code="CONFIG_INVALID")
    return value


def token_value(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 8192 or re.search(r"[\x00-\x20\x7f]", value):
        raise ConfigError("Invalid chat authentication token", code="CONFIG_INVALID")
    return value


def base_url(value: str) -> str:
    try:
        url = urlsplit(value)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment: raise ValueError()
        _ = url.port
    except (ValueError, TypeError): raise ConfigError("base_url must be an absolute HTTP URL without credentials, query or fragment", code="CONFIG_INVALID") from None
    return value.rstrip("/")


def bad(message: str = "Invalid chat response") -> APIConnectionError:
    return APIConnectionError(message, code="BAD_RESPONSE")


class Interrupted(APIConnectionError):
    def __init__(self, run_id: Optional[str] = None):
        super().__init__("Chat connection ended before a terminal result; the message was not resent", code="CHAT_STREAM_INTERRUPTED")
        self.run_id = run_id


def json_text(value: Any) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        encoded.encode("utf-8")
        return encoded
    except (ValueError, TypeError, UnicodeError, RecursionError): raise ConfigError("Chat values must be UTF-8 JSON", code="CONFIG_INVALID") from None


def decode(data: Any) -> Optional[Dict[str, Any]]:
    def invalid_constant(_): raise ValueError()
    try:
        if not isinstance(data, str) or len(data) > 4 * 1024 * 1024: raise ValueError()
        frame = json.loads(data, parse_constant=invalid_constant)
        if not isinstance(frame, dict) or not isinstance(frame.get("type"), str): raise ValueError()
        kind = frame["type"]
        if kind not in TYPES: return None
        if type(frame.get("v")) is not int or frame["v"] != 1 or type(frame.get("seq")) is not int or frame["seq"] < 0: raise ValueError()
        if kind == "ready" and frame.get("protocol") != "superstep-chat": raise ValueError()
        if kind == "run_started" and not isinstance(frame.get("run_id"), str): raise ValueError()
        if kind == "token" and not isinstance(frame.get("delta"), str): raise ValueError()
        if kind == "step" and (not isinstance(frame.get("node"), str) or frame.get("event") not in ("started", "finished", "error")): raise ValueError()
        if kind == "turn" and (not isinstance(frame.get("turn_id"), str) or frame.get("role") != "assistant"): raise ValueError()
        if kind == "done" and frame.get("status") not in DONE: raise ValueError()
        if kind == "error" and (not isinstance(frame.get("error"), dict) or not all(isinstance(frame["error"].get(k), str) for k in ("code", "message"))): raise ValueError()
        return frame
    except (ValueError, TypeError, KeyError, RecursionError): raise bad("Invalid chat socket frame") from None


@dataclass(frozen=True)
class ChatResult:
    session_id: str
    status: str
    text: str
    run_id: Optional[str] = None
    turn_id: Optional[str] = None
    turns: List[Dict[str, Any]] = field(default_factory=list)
    question: Optional[Dict[str, Any]] = None
    recovered: bool = False


class FrameState:
    def __init__(self):
        self.seq, self.sent = -1, False
        self.run_id = self.turn_id = self.question = self.done = None
        self.text = ""

    def take(self, data):
        frame = decode(data)
        if frame is None or frame["seq"] <= self.seq: return None
        self.seq = frame["seq"]
        kind = frame["type"]
        if kind == "run_started": self.run_id = frame["run_id"]
        elif kind == "token":
            self.text += frame["delta"]
            if len(self.text) > 8 * 1024 * 1024: raise APIConnectionError("Chat answer exceeds the client text limit", code="CHAT_RESPONSE_TOO_LARGE")
        elif kind == "turn": self.turn_id = frame["turn_id"]
        elif kind == "question": self.question = frame
        elif kind == "done":
            self.done = frame
            self.run_id = frame.get("run_id") or self.run_id
        return frame


class History:
    def __init__(self, before, after):
        if not isinstance(before, dict) or not isinstance(before.get("turns"), list): raise bad()
        self.known = {turn["id"] for turn in before["turns"]}
        self.cursor = after or (before["turns"][-1]["id"] if before["turns"] else None)
        self.turns, self.saved = [], None

    def add(self, page, run_id):
        if not isinstance(page, dict) or not isinstance(page.get("turns"), list): raise bad()
        rows = page["turns"]
        if rows:
            self.turns.extend(rows); self.cursor = rows[-1]["id"]
            self.saved = next((turn for turn in rows if turn["id"] not in self.known and turn.get("role") == "assistant" and run_id and turn.get("run_id") == run_id and turn.get("status") in DONE), None)
        return rows

    def result(self, sid, state, interrupted):
        saved = self.saved or {}
        if not state.done and not saved: raise Interrupted(state.run_id)
        return ChatResult(session_id=sid, status=saved.get("status") or state.done["status"], text=saved.get("text", state.text),
            run_id=state.run_id, turn_id=saved.get("id", state.turn_id), turns=self.turns, question=state.question, recovered=interrupted)


def stream_limits(timeout, attempts, interval):
    if timeout is not None and (not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0): raise ValueError("timeout must be positive or None")
    if type(attempts) is not int or not 0 <= attempts <= 100 or not math.isfinite(interval) or interval < 0: raise ValueError("Invalid recovery limits")


def request_frame(kind, sid, value, node=None, attachments=None, locale=None):
    frame = {"type": kind, "chat_session_id": segment(sid)}
    if kind == "message":
        if not isinstance(value, str): raise ConfigError("Chat text must be a string", code="CONFIG_INVALID")
        frame["text"] = value
        if attachments: frame["attachments"] = [segment(item) for item in attachments]
    else:
        if value is None: raise ConfigError("An answer needs text, form values or an approval", code="CONFIG_INVALID")
        frame["response"] = value
        if node: frame["node"] = node
    if locale:
        if locale not in ("en", "vi"): raise ConfigError("Unsupported chat locale", code="CONFIG_INVALID")
        frame["locale"] = locale
    json_text(frame)
    return frame


class ChatConfig:
    def __init__(self, slug, base, token, visitor_token, origin):
        self.base, self.root = base_url(base), f"/api/public/v1/chat/{segment(slug)}"
        self.token, self.visitor, self.origin = token, token_value(visitor_token or "new"), origin
        if token is not None and visitor_token is not None: raise ConfigError("Use token or visitor_token, not both", code="CONFIG_INVALID")
        if token is not None and not callable(token): token_value(token)
        url = urlsplit(self.base + f"/ws/public/v1/chat/{segment(slug)}")
        self.socket_url = urlunsplit(("wss" if url.scheme == "https" else "ws", url.netloc, url.path, "", ""))

    def headers(self, auth):
        headers = {"Accept": "application/json"}
        if "token" in auth: headers["Authorization"] = f"Bearer {auth['token']}"
        else: headers["X-Chat-Visitor"] = auth["visitor"]
        if self.origin: headers["Origin"] = self.origin
        return headers

    def capture(self, data):
        if self.token is None and isinstance(data, dict) and data.get("visitor_token") is not None:
            self.visitor = token_value(data["visitor_token"])
        return data


def upload_file(file, filename, content_type):
    name = filename or getattr(file, "name", "upload.bin")
    if not isinstance(name, str): name = "upload.bin"
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    try: position = file.tell() if hasattr(file, "tell") and hasattr(file, "seek") else None
    except (OSError, ValueError): position = None
    def build(attempt):
        if attempt and position is not None: file.seek(position)
        if attempt and position is None and not isinstance(file, bytes): raise ConfigError("A file must be rewindable to retry after expiry", code="CONFIG_INVALID")
        return {"file": (name, file, content_type or "application/octet-stream")}
    return build


def socket_options(origin, timeout):
    return dict(origin=origin, proxy=None, open_timeout=min(timeout, 10) if timeout is not None else 10,
                close_timeout=1, max_size=4 * 1024 * 1024, max_queue=16)


def sync_connect(*args, **kwargs):
    try: from websockets.sync.client import connect
    except ImportError: raise ConfigError("Install superstep[chat] for socket streaming", code="CONFIG_MISSING") from None
    return connect(*args, **kwargs)


def async_connect(*args, **kwargs):
    try: from websockets.asyncio.client import connect
    except ImportError: raise ConfigError("Install superstep[chat] for socket streaming", code="CONFIG_MISSING") from None
    return connect(*args, **kwargs)
