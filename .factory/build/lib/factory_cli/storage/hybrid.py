from __future__ import annotations

from typing import List, Optional

from .base import TaskRecord, TaskStore, UsageRecord


class HybridTaskStore(TaskStore):
    """File is the source of truth; a database mirrors tasks and owns usage.

    - Tasks are read from and written to the folder store, so the board,
      orchestrator, and git always agree. Each task write is mirrored to the
      database on a best-effort basis (the file remains authoritative).
    - Usage metrics live in the database, where they can be queried and
      aggregated efficiently and, with Postgres, shared across a team.
    """

    def __init__(self, folder_store: TaskStore, db_store: TaskStore) -> None:
        self.folder = folder_store
        self.db = db_store

    # -- tasks: read/write through the folder (authoritative) ----------------

    def list_tasks(self) -> List[TaskRecord]:
        return self.folder.list_tasks()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self.folder.get_task(task_id)

    def create_task(self, task_id: str, title: str, state: str) -> TaskRecord:
        record = self.folder.create_task(task_id, title, state)
        self._mirror(lambda: self.db.create_task(task_id, title, state))
        return record

    def move_task(self, task_id: str, target_state: str) -> TaskRecord:
        record = self.folder.move_task(task_id, target_state)
        self._mirror(lambda: self.db.move_task(record.task_id, target_state))
        return record

    # -- usage: owned by the database ----------------------------------------

    def forget(self, task_ids) -> None:
        self._mirror(lambda: self.db.forget(task_ids))

    def record_usage(self, record: UsageRecord) -> None:
        self.db.record_usage(record)

    def list_usage(
        self,
        scope: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> List[UsageRecord]:
        return self.db.list_usage(scope=scope, ref=ref)

    @staticmethod
    def _mirror(operation) -> None:
        """Apply a database mirror write; never let it break the file write."""
        try:
            operation()
        except Exception:  # noqa: BLE001 - the file write already succeeded
            pass
