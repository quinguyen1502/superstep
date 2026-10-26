from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from ..constants import TASK_STATES
from .base import TaskRecord, TaskStore, UsageRecord
from .folder import StoreError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _import_driver():
    """Lazily import a psycopg driver; never a hard dependency."""
    try:
        import psycopg  # type: ignore

        return psycopg, "psycopg"
    except ImportError:
        pass
    try:
        import psycopg2  # type: ignore

        return psycopg2, "psycopg2"
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise StoreError(
            "Postgres storage backend requires the 'psycopg' (or 'psycopg2') driver. "
            "Install it into the project environment, or use the sqlite/folder backend."
        ) from exc


class PostgresTaskStore(TaskStore):
    """Postgres-backed store sharing the SQLite schema; driver is optional."""

    def __init__(self, dsn: str) -> None:
        if not (dsn or "").strip():
            raise StoreError("Postgres storage backend requires storage_dsn.")
        self._driver, _ = _import_driver()
        self.dsn = dsn
        self._migrate()

    def _connect(self):
        return self._driver.connect(self.dsn)

    @contextmanager
    def _conn(self) -> Iterator[object]:
        """Yield a connection that is committed and closed on exit."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        state TEXT NOT NULL,
                        body TEXT,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usage (
                        id SERIAL PRIMARY KEY,
                        scope TEXT NOT NULL,
                        ref TEXT NOT NULL,
                        tool_id TEXT NOT NULL,
                        input_tokens INTEGER NOT NULL DEFAULT 0,
                        output_tokens INTEGER NOT NULL DEFAULT 0,
                        cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
                        recorded_at TEXT NOT NULL,
                        note TEXT
                    )
                    """
                )

    def list_tasks(self) -> List[TaskRecord]:
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT task_id, title, state, body FROM tasks ORDER BY task_id"
                )
                rows = cursor.fetchall()
        return [
            TaskRecord(task_id=r[0], title=r[1], state=r[2], path=None, body=r[3])
            for r in rows
        ]

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT task_id, title, state, body FROM tasks "
                    "WHERE task_id LIKE %s ORDER BY task_id",
                    (f"{task_id}%",),
                )
                rows = cursor.fetchall()
        if not rows:
            return None
        if len(rows) > 1:
            raise StoreError("Task ID is ambiguous: " + ", ".join(r[0] for r in rows))
        r = rows[0]
        return TaskRecord(task_id=r[0], title=r[1], state=r[2], path=None, body=r[3])

    def create_task(self, task_id: str, title: str, state: str) -> TaskRecord:
        from ..renderers import render_task

        if state not in TASK_STATES:
            raise StoreError(f"Invalid task state: {state}")
        if self.get_task(task_id) is not None:
            raise StoreError(f"Task already exists: {task_id}")
        body = render_task(
            project="",
            task_id=task_id,
            title=title,
            status=state,
            objective=title,
            expected_outputs=("Define task-scoped outputs.",),
            validation_plan=("Define task-scoped validation.",),
        )
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tasks (task_id, title, state, body, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (task_id, title, state, body, _now()),
                )
        return TaskRecord(task_id=task_id, title=title, state=state, path=None, body=body)

    def move_task(self, task_id: str, target_state: str) -> TaskRecord:
        if target_state not in TASK_STATES:
            raise StoreError(f"Invalid task state: {target_state}")
        record = self.get_task(task_id)
        if record is None:
            raise StoreError(f"No task found for ID or prefix: {task_id}")
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE tasks SET state = %s, updated_at = %s WHERE task_id = %s",
                    (target_state, _now(), record.task_id),
                )
        record.state = target_state
        return record

    def forget(self, task_ids) -> None:
        if not task_ids:
            return
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "DELETE FROM tasks WHERE task_id = %s",
                    [(tid,) for tid in task_ids],
                )

    def record_usage(self, record: UsageRecord) -> None:
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usage (scope, ref, tool_id, input_tokens, output_tokens, "
                    "cost_usd, recorded_at, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        record.scope,
                        record.ref,
                        record.tool_id,
                        int(record.input_tokens),
                        int(record.output_tokens),
                        float(record.cost_usd),
                        record.recorded_at or _now(),
                        record.note,
                    ),
                )

    def list_usage(
        self,
        scope: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> List[UsageRecord]:
        query = (
            "SELECT scope, ref, tool_id, input_tokens, output_tokens, cost_usd, "
            "recorded_at, note FROM usage"
        )
        clauses: List[str] = []
        params: List[object] = []
        if scope is not None:
            clauses.append("scope = %s")
            params.append(scope)
        if ref is not None:
            clauses.append("ref = %s")
            params.append(ref)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        with self._conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
        return [
            UsageRecord(
                scope=r[0],
                ref=r[1],
                tool_id=r[2],
                input_tokens=r[3],
                output_tokens=r[4],
                cost_usd=r[5],
                recorded_at=r[6],
                note=r[7],
            )
            for r in rows
        ]
