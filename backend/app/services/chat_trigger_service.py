"""Chat triggers (TASK-0074, REQ-0044, DEC-0046): a command word that starts a workflow from a Slack or Telegram message.

A trigger names an approval connection (DEC-0019), the place it listens (a Slack channel, a Telegram chat, or "dm" for
direct messages to the bot) and a command word, unique per connection and place. Managing triggers needs the workflow's
share right (owner or admin), like schedules: a trigger spends the owner's resources when someone writes in a chat.
Messages, runs and replies are TASK-0075.
"""
import json, re, time, uuid
from typing import Optional
from ..core import permissions as P
from ..core.errors import AppError
from ..models import WorkflowChatTrigger
from ..repositories import ChatTriggerRepository, WorkflowRepository
from .channel_service import ChannelService
from . import event_bindings

MAX_PER_WORKFLOW = 20
DM = "dm"
COMMAND = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
FIELDS = ("name", "channel_id", "place", "command", "input_field", "reply_field", "enabled")


class ChatTriggerService:
    def __init__(self, triggers: ChatTriggerRepository, workflows: WorkflowRepository, channels: ChannelService, access=None):
        self.triggers, self.workflows, self.channels, self.access = triggers, workflows, channels, access

    def _manage(self, wid: str, uid: str) -> None:
        if self.access is not None: self.access.workflow(wid, uid, P.SHARE); return
        if self.workflows.get_owned(wid, uid) is None: raise AppError("WORKFLOW_NOT_FOUND")

    def _own(self, wid: str, tid: str, uid: str) -> WorkflowChatTrigger:
        self._manage(wid, uid); t = self.triggers.get(tid)
        if t is None or t.workflow_id != wid: raise AppError("CHAT_TRIGGER_NOT_FOUND")
        return t

    def public(self, t: WorkflowChatTrigger) -> dict:
        c = self.channels.repo.channel(t.channel_id)
        return {"id": t.id, "name": t.name, "channel_id": t.channel_id, "kind": c.kind if c else None, "channel_name": c.name if c else None,
                "place": t.place, "command": t.command, "input_field": t.input_field, "reply_field": t.reply_field, "enabled": t.enabled,
                "note": t.note, "last_message": t.last_message, "last_run_id": t.last_run_id, "created": t.created, "event": event_bindings.settings(t)}

    # ---- validation ----
    def _fields(self, wid: str) -> set[str]:
        w = self.workflows.get(wid)
        try: state = (json.loads(w.data or "{}").get("state") or []) if w else []
        except (ValueError, AttributeError): state = []
        return {f["name"] for f in state if isinstance(f, dict) and isinstance(f.get("name"), str)}

    def _check(self, wid: str, uid: str, v: dict, tid: Optional[str] = None) -> dict:
        """Normalise and validate the merged settings; returns them ready to store."""
        def bad(field): return AppError("CHAT_TRIGGER_CONFIG_INVALID", field=field)
        c = self.channels.repo.channel(str(v.get("channel_id") or ""))
        if not self.channels.usable(uid, c) or (c.scope == "org" and not self.channels.org_allowed(uid)): raise AppError("CHANNEL_NOT_FOUND")
        a = self.channels.adapters.get(c.kind)
        if a is None or not a.chat: raise bad("channel_id")
        place = str(v.get("place") or "").strip()
        if place != DM and not re.fullmatch(a.place_pattern, place): raise bad("place")
        fields = self._fields(wid)
        policy = v.get("event")
        if policy is not None:
            if c.kind not in ("telegram", "webhook"): raise bad("channel_id")
            policy = event_bindings.validate(policy, fields)
            command = "*"
        else:
            if a.events_only: raise bad("event")
            command = str(v.get("command") or "").strip().lstrip("/").lower()
            if not COMMAND.fullmatch(command): raise bad("command")
            for f in ("input_field", "reply_field"):
                if v.get(f) not in fields: raise bad(f)
        if v.get("enabled", True):
            missing = self.channels.missing_scopes(c)
            if missing: raise AppError("CHAT_TRIGGER_SCOPE_MISSING", scopes=", ".join(missing))
        other = self.triggers.find(c.id, place, command)
        if other is not None and other.id != tid: raise AppError("CHAT_TRIGGER_COMMAND_TAKEN", command=command)
        return {"channel_id": c.id, "place": place, "command": command, "input_field": v.get("input_field") or "", "reply_field": v.get("reply_field") or "",
                "settings": json.dumps({"event": policy}) if policy is not None else None,
                "name": str(v.get("name") or "").strip()[:80] or (policy["type"] if policy else command), "enabled": bool(v.get("enabled", True))}

    # ---- owner API ----
    def list(self, wid: str, uid: str) -> list[dict]:
        self._manage(wid, uid); return [self.public(t) for t in self.triggers.list_for_workflow(wid)]

    def create(self, wid: str, uid: str, body: dict) -> dict:
        self._manage(wid, uid)
        if self.triggers.count_for_workflow(wid) >= MAX_PER_WORKFLOW: raise AppError("CHAT_TRIGGER_LIMIT", max=MAX_PER_WORKFLOW)
        v = self._check(wid, uid, body)
        t = self.triggers.add(WorkflowChatTrigger(id=uuid.uuid4().hex[:10], workflow_id=wid, owner=uid, created=time.time(), **v))
        return self.public(t)

    def update(self, wid: str, tid: str, uid: str, patch: dict) -> dict:
        """Change any setting; the merged settings are checked again (the connection may have changed since)."""
        t = self._own(wid, tid, uid)
        merged = {**{f: getattr(t, f) for f in FIELDS}, **{k: v for k, v in patch.items() if k in FIELDS and v is not None}}
        merged["event"] = patch["event"] if "event" in patch else event_bindings.settings(t)
        v = self._check(wid, uid, merged, tid)
        if v["enabled"]: v["note"] = None
        self.triggers.set_fields(tid, **v)
        return self.public(self.triggers.get(tid))

    def delete(self, wid: str, tid: str, uid: str) -> dict:
        self._own(wid, tid, uid); self.triggers.delete(tid); return {"ok": True}

    # ---- used by message handling (TASK-0075) ----
    def stop(self, t: WorkflowChatTrigger, note: str) -> None:
        """Turn a trigger off and say why: access (creator lost the share right), channel (connection deleted), scopes."""
        self.triggers.set_fields(t.id, enabled=False, note=note)
