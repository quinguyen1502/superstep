from typing import Optional
from sqlalchemy import delete, func, select, update
from ..models import ChatAttachment
from ..models.database import Database

META = (ChatAttachment.id, ChatAttachment.session_id, ChatAttachment.turn_id, ChatAttachment.name, ChatAttachment.kind,
        ChatAttachment.mime, ChatAttachment.size, ChatAttachment.text, ChatAttachment.text_cut, ChatAttachment.created)


class ChatAttachmentRepository:
    """The files of chat messages (TASK-0174, DEC-0072). Reads without `data` unless the bytes are asked for."""
    def __init__(self, db: Database): self.db = db

    def add(self, row: ChatAttachment) -> ChatAttachment:
        with self.db.session() as s: s.add(row); s.commit(); s.refresh(row); return row

    def get(self, aid: str) -> Optional[ChatAttachment]:
        """One file with its bytes."""
        with self.db.session() as s: return s.get(ChatAttachment, aid)

    def meta(self, ids: list[str]) -> list:
        """Files without their bytes, in the order of `ids` (missing ones left out)."""
        if not ids: return []
        with self.db.session() as s:
            rows = {r.id: r for r in s.execute(select(*META).where(ChatAttachment.id.in_(ids)))}
        return [rows[i] for i in ids if i in rows]

    def unsent_count(self, sid: str) -> int:
        with self.db.session() as s:
            return s.scalar(select(func.count()).select_from(ChatAttachment).where(ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))) or 0

    def link(self, ids: list[str], sid: str, tid: str) -> int:
        """Gives unsent files of session `sid` to turn `tid`; the number linked."""
        if not ids: return 0
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(ChatAttachment.id.in_(ids), ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))
                          .values(turn_id=tid)).rowcount
            s.commit(); return n

    def delete_unsent(self, aid: str, sid: str) -> int:
        with self.db.session() as s:
            n = s.execute(delete(ChatAttachment).where(ChatAttachment.id == aid, ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))).rowcount
            s.commit(); return n

    def delete_stale(self, before: float) -> int:
        """Unsent files uploaded before `before` (never sent with a message)."""
        with self.db.session() as s:
            n = s.execute(delete(ChatAttachment).where(ChatAttachment.turn_id.is_(None), ChatAttachment.created < before)).rowcount
            s.commit(); return n

    def count(self) -> int:
        with self.db.session() as s: return s.scalar(select(func.count()).select_from(ChatAttachment)) or 0
