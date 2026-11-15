"""Per-run model usage rows (run_usage): replaced as a whole for one run, so a re-finish never duplicates them."""
import uuid
from typing import Optional
from sqlalchemy import delete, exists, select
from ..models import Run
from ..models.database import Database
from ..models.run_usage import RunUsage

TERMINAL = ("ok", "error", "timeout", "cancelled", "expired")


class RunUsageRepository:
    def __init__(self, db: Database): self.db = db

    def replace(self, run_id: str, workflow_id: str, owner: Optional[str], created: float, rows: list[dict]) -> int:
        """Delete the run's rows and write `rows` in one transaction (idempotent on recovery or re-finish)."""
        with self.db.session() as s:
            s.execute(delete(RunUsage).where(RunUsage.run_id == run_id))
            for r in rows:
                s.add(RunUsage(id=uuid.uuid4().hex[:12], run_id=run_id, workflow_id=workflow_id, owner=owner, created=created, **r))
            s.commit()
        return len(rows)

    def for_run(self, run_id: str) -> list[RunUsage]:
        with self.db.session() as s:
            return list(s.scalars(select(RunUsage).where(RunUsage.run_id == run_id).order_by(RunUsage.node_id, RunUsage.kind, RunUsage.model)))

    def runs_without_rows(self, since: float, limit: int, strict: bool = False) -> list[tuple]:
        """(id, workflow_id, owner, events JSON, ended) of finished runs ended at or after `since` (after it when
        `strict`) that have no usage rows, oldest first (backfill)."""
        q = (select(Run.id, Run.workflow_id, Run.owner, Run.events, Run.ended)
             .where(Run.status.in_(TERMINAL), Run.ended > since if strict else Run.ended >= since, ~exists().where(RunUsage.run_id == Run.id))
             .order_by(Run.ended).limit(limit))
        with self.db.session() as s: return [tuple(r) for r in s.execute(q).all()]
