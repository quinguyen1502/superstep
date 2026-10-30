import time
from typing import Optional
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from ..models import ChatAttachment, ChatRating, ChatSession, ChatTurn
from ..models.database import Database

_PENDING = "pending:"  # one worker owns the LangSmith create; not a real feedback id
_PENDING_TTL = 60.0


def feedback_is_pending(value: str) -> bool:
    return (value or "").startswith(_PENDING)


def _pending_stale(value: str) -> bool:
    try:
        started = float(value[len(_PENDING):])
    except ValueError:
        return True
    return time.time() - started > _PENDING_TTL


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
        """Insert or replace the one rating of a turn. The last write wins. `created` and `feedback_id` stay."""
        with self.db.session() as s:
            cur = s.get(ChatRating, row.turn_id)
            if cur is not None:
                return self._replace_rating(s, cur, row)
            try:
                s.add(row); s.commit(); s.refresh(row); return row
            except IntegrityError:
                s.rollback()
        with self.db.session() as s:
            cur = s.get(ChatRating, row.turn_id)
            if cur is None:
                s.add(row); s.commit(); s.refresh(row); return row
            return self._replace_rating(s, cur, row)

    def _replace_rating(self, s, cur: ChatRating, row: ChatRating) -> ChatRating:
        cur.value, cur.comment, cur.updated = row.value, row.comment, row.updated
        cur.session_id, cur.workflow_id = row.session_id, row.workflow_id
        s.commit(); s.refresh(cur); return cur

    def claim_feedback(self, tid: str) -> str:
        """'create' if this caller sends the first feedback, 'busy' if another send is in flight,
        'gone' if the rating was removed, otherwise the LangSmith id to update.

        A claim older than a minute is stolen. A worker that died mid-create must not block every later send.
        """
        with self.db.session() as s:
            row = s.get(ChatRating, tid)
            if row is None:
                return "gone"
            current = row.feedback_id or ""
            if feedback_is_pending(current) and not _pending_stale(current):
                return "busy"
            if current and not feedback_is_pending(current):
                return current
            token = f"{_PENDING}{time.time()}"
            n = s.execute(update(ChatRating).where(ChatRating.turn_id == tid, ChatRating.feedback_id == current)
                          .values(feedback_id=token)).rowcount
            s.commit()
            return "create" if n == 1 else "busy"

    def release_feedback_claim(self, tid: str) -> None:
        """A create that did not store an id may be tried again on a later rating."""
        with self.db.session() as s:
            row = s.get(ChatRating, tid)
            if row is not None and feedback_is_pending(row.feedback_id or ""):
                s.execute(update(ChatRating).where(ChatRating.turn_id == tid, ChatRating.feedback_id == row.feedback_id)
                          .values(feedback_id=""))
                s.commit()

    def set_rating_feedback(self, tid: str, feedback_id: str) -> None:
        with self.db.session() as s:
            s.execute(update(ChatRating).where(ChatRating.turn_id == tid).values(feedback_id=feedback_id)); s.commit()

    def delete_rating(self, tid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(ChatRating).where(ChatRating.turn_id == tid)); s.commit()

    def _feedback_ids(self, s, *where) -> list[str]:
        q = select(ChatRating.feedback_id).where(ChatRating.feedback_id != "", *where)
        return [fid for fid in s.scalars(q) if fid and not feedback_is_pending(fid)]

    def feedback_ids_for_session(self, sid: str) -> list[str]:
        with self.db.session() as s: return self._feedback_ids(s, ChatRating.session_id == sid)

    def feedback_ids_idle(self, trigger_id: str, before: float) -> list[str]:
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.trigger_id == trigger_id, ChatSession.updated < before)
            return self._feedback_ids(s, ChatRating.session_id.in_(ids))

    def feedback_ids_for_workflow(self, wid: str) -> list[str]:
        with self.db.session() as s: return self._feedback_ids(s, ChatRating.workflow_id == wid)

    def feedback_ids_for_owner(self, owner: str) -> list[str]:
        with self.db.session() as s:
            ids = select(ChatSession.id).where(ChatSession.owner == owner)
            return self._feedback_ids(s, ChatRating.session_id.in_(ids))

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
        s.execute(delete(ChatAttachment).where(ChatAttachment.session_id.in_(ids)))  # a file goes with its session (TASK-0174)
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
