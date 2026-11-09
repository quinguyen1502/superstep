"""Owner/admin chat server credentials. Rotation creates a second key, then revokes the old one."""
from __future__ import annotations
import json, secrets, time, uuid
from ..core import crypto
from ..core.errors import AppError
from ..models import ChatAppKey
from ..repositories.chat_app_keys import ChatAppKeyRepository
from .chat_session_service import origin_of, ORIGINS_MAX


class ChatAppKeyService:
    def __init__(self, keys: ChatAppKeyRepository, triggers, workflows, access, audit):
        self.keys, self.triggers, self.workflows, self.access, self.audit = keys, triggers, workflows, access, audit

    def _manage(self, wid: str, uid: str):
        w = self.workflows.get(wid)
        if w is None: raise AppError("WORKFLOW_NOT_FOUND")
        if w.owner != uid and self.access.role(uid) != "admin": raise AppError("WORKFLOW_FORBIDDEN")
        t = self.triggers.web(wid)
        if t is None: raise AppError("CHAT_TRIGGER_NOT_FOUND")
        return t

    @staticmethod
    def public(k: ChatAppKey) -> dict:
        return {"key_id": k.key_id, "label": k.label, "origins": json.loads(k.origins), "created_at": k.created_at,
                "created_by": k.created_by, "revoked_at": k.revoked_at, "last_used_at": k.last_used_at}

    def list(self, wid: str, uid: str) -> list[dict]:
        t = self._manage(wid, uid)
        return [self.public(k) for k in self.keys.list(t.id)]

    def create(self, wid: str, uid: str, label: str, origins: list[str]) -> dict:
        t = self._manage(wid, uid)
        label = label.strip()
        if not label or len(label) > 80: raise AppError("CHAT_SETTINGS_INVALID", field="label")
        checked = []
        if len(origins) > ORIGINS_MAX: raise AppError("CHAT_SETTINGS_INVALID", field="origins")
        for raw in origins:
            value = origin_of(raw)
            if value is None: raise AppError("CHAT_EMBED_ORIGIN_INVALID", origin=raw[:100])
            if value not in checked: checked.append(value)
        secret = secrets.token_urlsafe(32)
        row = self.keys.create(ChatAppKey(id=uuid.uuid4().hex, trigger_id=t.id, key_id="ck_" + secrets.token_hex(16),
            secret_enc=crypto.encrypt(secret), label=label, origins=json.dumps(checked), created_by=uid, created_at=time.time()))
        self.audit.record(uid, "chat_app_key.create", "workflow", wid, label, key_id=row.key_id)
        return {**self.public(row), "secret": secret}

    def revoke(self, wid: str, kid: str, uid: str) -> dict:
        t = self._manage(wid, uid)
        if self.keys.revoke(t.id, kid, time.time()):
            self.audit.record(uid, "chat_app_key.revoke", "workflow", wid, key_id=kid)
        return {"ok": True}
