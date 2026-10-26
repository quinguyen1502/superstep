from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from ..constants import STORAGE_DB_PATH, TASK_ROOT, TASK_STATES
from .base import TaskRecord, TaskStore, UsageRecord
from .folder import FolderTaskStore, StoreError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SqliteTaskStore(TaskStore):
    """Self-contained SQLite store; seeds from markdown tasks if present."""

    def __init__(self, project_dir: Path, db_path: Optional[Path] = None) -> None:
        self.project_dir = Path(project_dir)
        self.db_path = Path(db_path) if db_path else self.project_dir / STORAGE_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_gitignored()
        self._connect_and_migrate()
        self._seed_if_empty()

    def _ensure_gitignored(self) -> None:
        """Keep the local SQLite mirror out of git; it is rebuilt from files."""
        gitignore = self.db_path.parent / ".gitignore"
        patterns = [f"{self.db_path.name}", f"{self.db_path.name}-wal", f"{self.db_path.name}-shm"]
        existing = (
            gitignore.read_text(encoding="utf-8").splitlines()
            if gitignore.is_file()
            else []
        )
        missing = [pattern for pattern in patterns if pattern not in existing]
        if not missing:
            return
        lines = existing + missing if existing else patterns
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection that is committed and *closed* on exit.

        ``with sqlite3.connect(...)`` only manages the transaction, not the
        connection lifetime, so the connection must be closed explicitly to
        avoid ResourceWarning leaks.
        """
        # `timeout` and busy_timeout make writers wait for a lock instead of
        # failing immediately; WAL lets readers and a writer work concurrently.
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _connect_and_migrate(self) -> None:
        with self._conn() as connection:
            connection.execute(
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    ref TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    recorded_at TEXT NOT NULL,
                    note TEXT
                )
                """
            )

    def _seed_if_empty(self) -> None:
        with self._conn() as connection:
            count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count:
            return
        if not (self.project_dir / TASK_ROOT).is_dir():
            return
        records = FolderTaskStore(self.project_dir).list_tasks()
        with self._conn() as connection:
            for record in records:
                connection.execute(
                    "INSERT OR IGNORE INTO tasks (task_id, title, state, body, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (record.task_id, record.title, record.state, record.body, _now()),
                )

    # -- tasks ---------------------------------------------------------------

    def list_tasks(self) -> List[TaskRecord]:
        with self._conn() as connection:
            rows = connection.execute(
                "SELECT task_id, title, state, body FROM tasks ORDER BY task_id"
            ).fetchall()
        return [
            TaskRecord(
                task_id=row["task_id"],
                title=row["title"],
                state=row["state"],
                path=None,
                body=row["body"],
            )
            for row in rows
        ]

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        with self._conn() as connection:
            rows = connection.execute(
                "SELECT task_id, title, state, body FROM tasks WHERE task_id LIKE ? "
                "ORDER BY task_id",
                (f"{task_id}%",),
            ).fetchall()
        if not rows:
            return None
        if len(rows) > 1:
            joined = ", ".join(row["task_id"] for row in rows)
            raise StoreError(f"Task ID is ambiguous: {joined}")
        row = rows[0]
        return TaskRecord(
            task_id=row["task_id"],
            title=row["title"],
            state=row["state"],
            path=None,
            body=row["body"],
        )

    def create_task(self, task_id: str, title: str, state: str) -> TaskRecord:
        from ..renderers import render_task

        if state not in TASK_STATES:
            raise StoreError(f"Invalid task state: {state}")
        if self.get_task(task_id) is not None:
            raise StoreError(f"Task already exists: {task_id}")
        body = render_task(
            project=self.project_dir.name,
            task_id=task_id,
            title=title,
            status=state,
            objective=title,
            expected_outputs=("Define task-scoped outputs.",),
            validation_plan=("Define task-scoped validation.",),
        )
        with self._conn() as connection:
            connection.execute(
                "INSERT INTO tasks (task_id, title, state, body, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
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
            connection.execute(
                "UPDATE tasks SET state = ?, updated_at = ? WHERE task_id = ?",
                (target_state, _now(), record.task_id),
            )
        record.state = target_state
        return record

    def forget(self, task_ids) -> None:
        if not task_ids:
            return
        with self._conn() as connection:
            connection.executemany(
                "DELETE FROM tasks WHERE task_id = ?", [(tid,) for tid in task_ids]
            )

    # -- usage metrics -------------------------------------------------------

    def record_usage(self, record: UsageRecord) -> None:
        with self._conn() as connection:
            connection.execute(
                "INSERT INTO usage (scope, ref, tool_id, input_tokens, output_tokens, "
                "cost_usd, recorded_at, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
            clauses.append("scope = ?")
            params.append(scope)
        if ref is not None:
            clauses.append("ref = ?")
            params.append(ref)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        with self._conn() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            UsageRecord(
                scope=row["scope"],
                ref=row["ref"],
                tool_id=row["tool_id"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cost_usd=row["cost_usd"],
                recorded_at=row["recorded_at"],
                note=row["note"],
            )
            for row in rows
        ]
