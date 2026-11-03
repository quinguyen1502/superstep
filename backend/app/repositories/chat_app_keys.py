"""Chat app-key persistence; creation serialises on the trigger to enforce the two-key cap."""
from __future__ import annotations
from sqlalchemy import select, update
from ..core.errors import AppError
from ..models import ChatAppKey, WorkflowChatTrigger
from ..models.database import Database


class ChatAppKeyRepository:
    def __init__(self, db: Database): self.db = db

    def get(self, kid: str) -> ChatAppKey | None:
        with self.db.session() as s: return s.scalar(select(ChatAppKey).where(ChatAppKey.key_id == kid))

    def used(self, kid: str, at: float) -> bool:
        with self.db.session() as s:
            n = s.execute(update(ChatAppKey).where(ChatAppKey.key_id == kid, ChatAppKey.revoked_at.is_(None)).values(last_used_at=at)).rowcount
            s.commit(); return n == 1

    def list(self, tid: str) -> list[ChatAppKey]:
        with self.db.session() as s:
            return list(s.scalars(select(ChatAppKey).where(ChatAppKey.trigger_id == tid).order_by(ChatAppKey.created_at)))

    def create(self, row: ChatAppKey) -> ChatAppKey:
        with self.db.session() as s:
            # UPDATE locks on both SQLite and Postgres, including when no key rows exist yet.
            found = s.execute(update(WorkflowChatTrigger).where(WorkflowChatTrigger.id == row.trigger_id)
                              .values(enabled=WorkflowChatTrigger.enabled)).rowcount
            if not found: raise AppError("CHAT_TRIGGER_NOT_FOUND")
            active = list(s.scalars(select(ChatAppKey.id).where(ChatAppKey.trigger_id == row.trigger_id, ChatAppKey.revoked_at.is_(None))))
            if len(active) >= 2: raise AppError("CHAT_APP_KEY_LIMIT")
            s.add(row); s.commit(); s.refresh(row); return row

    def revoke(self, tid: str, kid: str, at: float) -> bool:
        with self.db.session() as s:
            row = s.scalar(select(ChatAppKey).where(ChatAppKey.trigger_id == tid, ChatAppKey.key_id == kid))
            if row is None: raise AppError("CHAT_APP_KEY_NOT_FOUND")
            if row.revoked_at is not None: return False
            row.revoked_at = at; s.commit(); return True
