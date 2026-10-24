from typing import Optional
from sqlalchemy import delete, select, update
from ..models import AgentThread, AgentThreadRun
from ..models.database import Database


class AgentThreadRepository:
    def __init__(self, db: Database): self.db = db

    def add(self, t: AgentThread) -> AgentThread:
        with self.db.session() as s:
            s.add(t); s.commit(); s.refresh(t); s.expunge(t); return t

    def get(self, tid: str) -> Optional[AgentThread]:
        with self.db.session() as s:
            return s.get(AgentThread, tid)

    def search(self, owner: str, token_id: Optional[str], limit: int, offset: int) -> list[AgentThread]:
        """Threads of `owner` created with `token_id` (None: signed-in, not through a token), newest first."""
        q = select(AgentThread).where(AgentThread.owner == owner,
                                      AgentThread.token_id == token_id if token_id else AgentThread.token_id.is_(None))
        with self.db.session() as s:
            return list(s.scalars(q.order_by(AgentThread.updated.desc()).limit(limit).offset(offset)))

    def set_fields(self, tid: str, **values) -> None:
        with self.db.session() as s:
            s.execute(update(AgentThread).where(AgentThread.id == tid).values(**values)); s.commit()

    def delete(self, tid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(AgentThreadRun).where(AgentThreadRun.thread_id == tid))
            s.execute(delete(AgentThread).where(AgentThread.id == tid)); s.commit()

    def add_run(self, r: AgentThreadRun) -> None:
        with self.db.session() as s:
            s.add(r); s.commit()

    def runs(self, tid: str, limit: int = 100, offset: int = 0) -> list[AgentThreadRun]:
        """Runs of the thread, newest first."""
        with self.db.session() as s:
            return list(s.scalars(select(AgentThreadRun).where(AgentThreadRun.thread_id == tid)
                                  .order_by(AgentThreadRun.created.desc()).limit(limit).offset(offset)))

    def run(self, rid: str) -> Optional[AgentThreadRun]:
        with self.db.session() as s:
            return s.get(AgentThreadRun, rid)
