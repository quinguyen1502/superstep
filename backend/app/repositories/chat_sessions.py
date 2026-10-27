from typing import Optional
from sqlalchemy import delete, select, update
from ..models import ChatSession, ChatTurn
from ..models.database import Database


class ChatSessionRepository:
    """Chat sessions and their turns (TASK-0084)."""
    def __init__(self, db: Database): self.db = db

    def add(self, row: ChatSession) -> ChatSession:
        with self.db.session() as s: s.add(row); s.commit(); s.refresh(row); return row

    def get(self, sid: str) -> Optional[ChatSession]:
        with self.db.session() as s: return s.get(ChatSession, sid)

    def list_for(self, wid: str, owner: str, limit: int = 50) -> list[ChatSession]:
        with self.db.session() as s:
            q = select(ChatSession).where(ChatSession.workflow_id == wid, ChatSession.owner == owner).order_by(ChatSession.updated.desc()).limit(limit)
            return list(s.scalars(q))

    def list_public(self, trigger_id: str, owner: Optional[str] = None, visitor: Optional[str] = None, limit: int = 50) -> list[ChatSession]:
        """A visitor's chats on the published page (DEC-0067): by the studio user for signed_in, else by the visitor id."""
        with self.db.session() as s:
            who = ChatSession.owner == owner if owner else ChatSession.visitor == visitor
            q = (select(ChatSession).where(ChatSession.trigger_id == trigger_id, ChatSession.channel.in_(("web", "embed")), who)
                 .order_by(ChatSession.updated.desc()).limit(limit))
            return list(s.scalars(q))

    def set_fields(self, sid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(ChatSession).where(ChatSession.id == sid).values(**values)); s.commit()

    def add_turn(self, t: ChatTurn) -> ChatTurn:
        with self.db.session() as s:
            s.add(t); s.execute(update(ChatSession).where(ChatSession.id == t.session_id).values(updated=t.created)); s.commit(); s.refresh(t); return t

    def turns(self, sid: str) -> list[ChatTurn]:
        with self.db.session() as s:
            return list(s.scalars(select(ChatTurn).where(ChatTurn.session_id == sid).order_by(ChatTurn.created, ChatTurn.id)))

    def delete(self, sid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(ChatTurn).where(ChatTurn.session_id == sid)); s.execute(delete(ChatSession).where(ChatSession.id == sid)); s.commit()

    def delete_idle(self, trigger_id: str, before: float) -> int:
        """Sessions of one chat with no turn since `before` (the retention window), with their turns."""
        with self.db.session() as s:
            ids = list(s.scalars(select(ChatSession.id).where(ChatSession.trigger_id == trigger_id, ChatSession.updated < before)))
            if ids:
                s.execute(delete(ChatTurn).where(ChatTurn.session_id.in_(ids))); s.execute(delete(ChatSession).where(ChatSession.id.in_(ids))); s.commit()
            return len(ids)

    def delete_for_workflow(self, wid: str) -> None:
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.workflow_id == wid)
            s.execute(delete(ChatTurn).where(ChatTurn.session_id.in_(ids))); s.execute(delete(ChatSession).where(ChatSession.workflow_id == wid)); s.commit()

    def delete_for_owner(self, owner: str) -> None:
        """Every chat of one studio user, with the turns (a demo visitor's, when it expires)."""
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.owner == owner)
            s.execute(delete(ChatTurn).where(ChatTurn.session_id.in_(ids))); s.execute(delete(ChatSession).where(ChatSession.owner == owner)); s.commit()
