"""The chat socket protocol v1 (TASK-0216, REQ-0082, DEC-0078): typed frames on /ws/public/v1/chat/{slug}.

The client sends at most one `auth`, then one `message` or `answer` (one message per connection, decision 6 of PLAN-0002),
and may send `cancel`. The server sends `ready`, then the run as `run_started`, `token`, `step`, `question`, `turn`, and
`done` or `error`; every server frame carries `v: 1` and a per-connection `seq`. The JSON Schema of both sides is in
`app/api/schemas/chat_ws_v1/` and the AsyncAPI document in docs/asyncapi/chat-v1.yaml.

This module only translates: a v1 client frame into the request `PublicChatService.plan_message` takes, and a
`public_event` (already cut down to the steps mode) into a v1 server frame. The unversioned socket keeps its untyped
frames and `node_token`.
"""
from __future__ import annotations
from typing import Optional
from ..core.errors import AppError

VERSION = 1
PROTOCOL = "superstep-chat"
CLIENT_TYPES = ("auth", "message", "answer", "cancel")
STEP_EVENTS = {"node_started": "started", "node_finished": "finished", "error": "error"}
FIELDS = {"auth": {"type", "visitor", "token"}, "message": {"type", "chat_session_id", "text", "attachments", "locale"},
          "answer": {"type", "chat_session_id", "node", "response", "locale"}, "cancel": {"type"}}


def invalid(reason: str) -> AppError: return AppError("CHAT_FRAME_INVALID", reason=reason)


def client_frame(frame) -> dict:
    """The frame, checked: a known `type` and only its fields, else CHAT_FRAME_INVALID."""
    if not isinstance(frame, dict): raise invalid("not an object")
    t = frame.get("type")
    if t not in CLIENT_TYPES: raise invalid(f"unknown type {t!r}" if isinstance(t, str) else "missing type")
    extra = set(frame) - FIELDS[t]
    if extra: raise invalid(f"unknown field {sorted(extra)[0]!r}")
    if t in ("message", "answer") and not isinstance(frame.get("chat_session_id"), str): raise invalid("chat_session_id")
    if t == "message" and not isinstance(frame.get("text"), str): raise invalid("text")
    if t == "message" and not isinstance(frame.get("attachments", []), list): raise invalid("attachments")
    if t == "answer" and "response" not in frame: raise invalid("response")
    if t == "auth" and not all(isinstance(frame.get(k, ""), str) for k in ("visitor", "token")): raise invalid("auth")
    return frame


def plan_request(frame: dict) -> dict:
    """A `message` or `answer` frame as the request of `PublicChatService.plan_message`."""
    req: dict = {"chat_session_id": frame["chat_session_id"]}
    if frame["type"] == "message":
        req["message"] = frame["text"]
        if frame.get("attachments"): req["attachment_ids"] = frame["attachments"]
    else:
        req["response"] = frame["response"]
        if frame.get("node"): req["node"] = frame["node"]
    if frame.get("locale"): req["locale"] = frame["locale"]
    return req


def server_frame(ev: dict) -> Optional[dict]:
    """A public event as a v1 frame (without `v` and `seq`), or None. `run_summary` becomes `done`; `run_cancelled` and
    `run_timeout` are folded into it (the socket sends one `done`)."""
    t = ev.get("type")
    if t == "run_started": return {"type": t, "run_id": ev.get("run_id"), "ts": ev.get("ts")}
    if t == "node_token": return {**{k: ev.get(k) for k in ("node", "field", "iteration", "delta", "ts")}, "type": "token"}
    if t == "run_waiting": return {**{k: v for k, v in ev.items() if k != "type" and k != "node_type"}, "type": "question"}
    if t == "error" and "error" in ev and not ev.get("node"):
        return {"type": "error", "error": ev["error"], "ts": ev.get("ts")}
    if t in STEP_EVENTS:
        out = {k: v for k, v in ev.items() if k != "type"}
        return {**out, "type": "step", "event": STEP_EVENTS[t]}
    if t == "run_summary": return {"type": "done", "run_id": ev.get("run_id"), "status": ev.get("status"), "ts": ev.get("ts")}
    return None


class Frames:
    """Numbers the frames of one connection: `v` and a monotonic `seq` from 0."""
    def __init__(self): self.seq = 0

    def __call__(self, frame: dict) -> dict:
        out = {**frame, "v": VERSION, "seq": self.seq}; self.seq += 1
        return out
