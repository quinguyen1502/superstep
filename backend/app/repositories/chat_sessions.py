from typing import Optional
from sqlalchemy import case, delete, func, select, update
from ..models import ChatRating, ChatSession, ChatTurn
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

    def set_fields(self, sid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(ChatSession).where(ChatSession.id == sid).values(**values)); s.commit()

    def add_turn(self, t: ChatTurn) -> ChatTurn:
        with self.db.session() as s:
            s.add(t); s.execute(update(ChatSession).where(ChatSession.id == t.session_id).values(updated=t.created)); s.commit(); s.refresh(t); return t

    def turns(self, sid: str) -> list[ChatTurn]:
        with self.db.session() as s:
            return list(s.scalars(select(ChatTurn).where(ChatTurn.session_id == sid).order_by(ChatTurn.created, ChatTurn.id)))

    def turn(self, tid: str) -> Optional[ChatTurn]:
        with self.db.session() as s: return s.get(ChatTurn, tid)

    def ratings_of(self, sid: str) -> list[ChatRating]:
        with self.db.session() as s:
            return list(s.scalars(select(ChatRating).where(ChatRating.session_id == sid)))

    def rating(self, tid: str) -> Optional[ChatRating]:
        with self.db.session() as s: return s.get(ChatRating, tid)

    def upsert_rating(self, row: ChatRating) -> ChatRating:
        """Insert or replace the one rating of a turn. `created` and `feedback_id` stay on a later write."""
        with self.db.session() as s:
            cur = s.get(ChatRating, row.turn_id)
            if cur is None:
                s.add(row); s.commit(); s.refresh(row); return row
            cur.value, cur.comment, cur.updated = row.value, row.comment, row.updated
            cur.session_id, cur.workflow_id = row.session_id, row.workflow_id
            s.commit(); s.refresh(cur); return cur

    def set_rating_feedback(self, tid: str, feedback_id: str) -> None:
        with self.db.session() as s:
            s.execute(update(ChatRating).where(ChatRating.turn_id == tid).values(feedback_id=feedback_id)); s.commit()

    def delete_rating(self, tid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(ChatRating).where(ChatRating.turn_id == tid)); s.commit()

    def rating_counts(self, wid: str, since: float) -> dict:
        """How many up and down ratings of one workflow were updated since `since`."""
        with self.db.session() as s:
            up = func.sum(case((ChatRating.value == "up", 1), else_=0))
            down = func.sum(case((ChatRating.value == "down", 1), else_=0))
            row = s.execute(select(up, down).where(ChatRating.workflow_id == wid, ChatRating.updated >= since)).one()
            return {"up": int(row[0] or 0), "down": int(row[1] or 0)}

    def down_sessions(self, ids: list[str]) -> set[str]:
        if not ids: return set()
        with self.db.session() as s:
            q = select(ChatRating.session_id).where(ChatRating.session_id.in_(ids), ChatRating.value == "down").distinct()
            return set(s.scalars(q))

    def list_public(self, trigger_id: str, owner: Optional[str] = None, visitor: Optional[str] = None, limit: int = 50, thumbs_down: bool = False) -> list[ChatSession]:
        """The published page's chats (DEC-0067): one visitor's (the studio user for signed_in, else the visitor id), or all.
        `thumbs_down` keeps chats that have at least one thumbs down (DEC-0070)."""
        with self.db.session() as s:
            q = select(ChatSession).where(ChatSession.trigger_id == trigger_id, ChatSession.channel.in_(("web", "embed")))
            if owner or visitor: q = q.where(ChatSession.owner == owner if owner else ChatSession.visitor == visitor)
            if thumbs_down:
                downs = select(ChatRating.session_id).where(ChatRating.value == "down")
                q = q.where(ChatSession.id.in_(downs))
            return list(s.scalars(q.order_by(ChatSession.updated.desc()).limit(limit)))

    def _drop_session(self, s, ids) -> None:
        s.execute(delete(ChatRating).where(ChatRating.session_id.in_(ids)))
        s.execute(delete(ChatTurn).where(ChatTurn.session_id.in_(ids)))

    def delete(self, sid: str) -> None:
        with self.db.session() as s:
            self._drop_session(s, [sid]); s.execute(delete(ChatSession).where(ChatSession.id == sid)); s.commit()

    def delete_idle(self, trigger_id: str, before: float) -> int:
        """Sessions of one chat with no turn since `before` (the retention window), with their turns and ratings."""
        with self.db.session() as s:
            ids = list(s.scalars(select(ChatSession.id).where(ChatSession.trigger_id == trigger_id, ChatSession.updated < before)))
            if ids:
                self._drop_session(s, ids); s.execute(delete(ChatSession).where(ChatSession.id.in_(ids))); s.commit()
            return len(ids)

    def delete_for_workflow(self, wid: str) -> None:
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.workflow_id == wid)
            self._drop_session(s, ids); s.execute(delete(ChatSession).where(ChatSession.workflow_id == wid)); s.commit()

    def delete_for_owner(self, owner: str) -> None:
        """Every chat of one studio user, with the turns and ratings (a demo visitor's, when it expires)."""
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.owner == owner)
            self._drop_session(s, ids); s.execute(delete(ChatSession).where(ChatSession.owner == owner)); s.commit()
