import time
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from ..models import NodeResult, Run
from ..models.database import Database
from .runs import StaleLease


class NodeResultRepository:
    """Node-result ledger. `put` is fenced: only the worker holding the run's current lease may write."""
    def __init__(self, db: Database): self.db = db

    def get(self, run_id: str, node_id: str, iteration: int) -> Optional[NodeResult]:
        with self.db.session() as s: return s.get(NodeResult, (run_id, node_id, iteration))

    def put(self, run_id: str, node_id: str, iteration: int, delta: str, key: str, fence: Optional[int] = None) -> bool:
        """Record a finished node once. False if it was already recorded (first writer wins)."""
        with self.db.session() as s:
            if fence is not None and s.scalar(select(Run.lease_gen).where(Run.id == run_id)) != fence: raise StaleLease(run_id)
            s.add(NodeResult(run_id=run_id, node_id=node_id, iteration=iteration, delta=delta, idempotency_key=key, created=time.time()))
            try: s.commit(); return True
            except IntegrityError: s.rollback(); return False

    def for_run(self, run_id: str) -> list[NodeResult]:
        with self.db.session() as s: return list(s.scalars(select(NodeResult).where(NodeResult.run_id == run_id)))

    def purge(self, run_id: str) -> None:
        with self.db.session() as s: s.execute(delete(NodeResult).where(NodeResult.run_id == run_id)); s.commit()
