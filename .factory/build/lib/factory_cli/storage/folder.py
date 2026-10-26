from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml

from ..constants import (
    METRICS_USAGE_JSONL,
    METRICS_USAGE_PATH,
    TASK_ROOT,
    TASK_STATES,
)
from .base import (
    TaskRecord,
    TaskStore,
    UsageRecord,
    parse_task_markdown,
    parse_task_owner,
)

# Reading the metadata header (Task ID + In Scope title) never needs the whole
# file, so list operations read only this many bytes per task.
_HEADER_BYTES = 8192


class StoreError(Exception):
    """Raised for storage-level failures surfaced to the CLI."""


class FolderTaskStore(TaskStore):
    """Markdown files under .factory-state/ remain the source of truth."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)

    # -- tasks ---------------------------------------------------------------

    def _task_root(self) -> Path:
        return self.project_dir / TASK_ROOT

    def _ensure_project(self) -> None:
        if not self._task_root().is_dir():
            raise StoreError(f"Not a factory project repository: {self.project_dir}")
        for state in TASK_STATES:
            if not (self._task_root() / state).is_dir():
                raise StoreError(f"Missing task state directory: {TASK_ROOT}/{state}")

    def _find_files(self, task_id: str) -> List[Path]:
        matches: List[Path] = []
        for state in TASK_STATES:
            matches.extend(sorted((self._task_root() / state).glob(f"{task_id}*.md")))
        return matches

    @staticmethod
    def _read_header(path: Path) -> str:
        """Read only the leading bytes needed to parse id and title."""
        with path.open("r", encoding="utf-8") as handle:
            return handle.read(_HEADER_BYTES)

    def list_tasks(self) -> List[TaskRecord]:
        self._ensure_project()
        records: List[TaskRecord] = []
        for state in TASK_STATES:
            for path in sorted((self._task_root() / state).glob("*.md")):
                # Listing only needs id/title/state, so the body is loaded
                # lazily by get_task when a task's detail is opened.
                header = self._read_header(path)
                task_id, title = parse_task_markdown(path.name, header)
                records.append(
                    TaskRecord(
                        task_id=task_id,
                        title=title,
                        state=state,
                        path=str(path.relative_to(self.project_dir)),
                        body=None,
                        owner=parse_task_owner(header),
                    )
                )
        return records

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        self._ensure_project()
        matches = self._find_files(task_id)
        if not matches:
            return None
        if len(matches) > 1:
            joined = ", ".join(
                str(path.relative_to(self.project_dir)) for path in matches
            )
            raise StoreError(f"Task ID is ambiguous: {joined}")
        path = matches[0]
        body = path.read_text(encoding="utf-8")
        parsed_id, title = parse_task_markdown(path.name, body)
        return TaskRecord(
            task_id=parsed_id,
            title=title,
            state=path.parent.name,
            path=str(path.relative_to(self.project_dir)),
            body=body,
        )

    def _lock(self):
        from ..locks import LockTimeout, project_lock

        try:
            return project_lock(self.project_dir)
        except LockTimeout as exc:
            raise StoreError(str(exc)) from exc

    def _claims(self, task_id: str) -> List[Path]:
        """Files already claiming a task ID, in any lifecycle state or archive.

        Any reuse of a number is a collision, whatever the slug or state —
        including archived tasks, whose numbers stay retired.
        """
        from ..constants import ARCHIVE_TASK_ROOT

        matches: List[Path] = []
        for state in TASK_STATES:
            matches.extend(sorted((self._task_root() / state).glob(f"{task_id}-*.md")))
        archive_root = self.project_dir / ARCHIVE_TASK_ROOT
        if archive_root.is_dir():
            matches.extend(sorted(archive_root.glob(f"*/{task_id}-*.md")))
        return matches

    def create_task(self, task_id: str, title: str, state: str) -> TaskRecord:
        # Rendering lives in renderers; imported lazily to avoid import cycles.
        from ..locks import LockTimeout
        from ..project import write_file
        from ..renderers import render_task, slugify

        if state not in TASK_STATES:
            raise StoreError(f"Invalid task state: {state}")
        self._ensure_project()
        filename = f"{task_id}-{slugify(title)}.md"
        body = render_task(
            project=self.project_dir.name,
            task_id=task_id,
            title=title,
            status=state,
            objective=title,
            expected_outputs=("Define task-scoped outputs.",),
            validation_plan=("Define task-scoped validation.",),
        )
        try:
            with self._lock():
                task_path = self._task_root() / state / filename
                existing = self._claims(task_id)
                if existing:
                    raise StoreError(f"Task ID already in use: {existing[0]}")
                write_file(task_path, body)
        except LockTimeout as exc:
            raise StoreError(str(exc)) from exc
        return TaskRecord(
            task_id=task_id,
            title=title,
            state=state,
            path=str(task_path.relative_to(self.project_dir)),
            body=body,
        )

    def move_task(self, task_id: str, target_state: str) -> TaskRecord:
        from ..locks import LockTimeout

        if target_state not in TASK_STATES:
            raise StoreError(f"Invalid task state: {target_state}")
        self._ensure_project()
        try:
            with self._lock():
                matches = self._find_files(task_id)
                if not matches:
                    raise StoreError(f"No task found for ID or prefix: {task_id}")
                if len(matches) > 1:
                    joined = ", ".join(
                        str(path.relative_to(self.project_dir)) for path in matches
                    )
                    raise StoreError(f"Task ID is ambiguous: {joined}")
                source = matches[0]
                destination = self._task_root() / target_state / source.name
                if destination.exists():
                    raise StoreError(f"Target task already exists: {destination}")
                source.replace(destination)
        except LockTimeout as exc:
            raise StoreError(str(exc)) from exc
        body = destination.read_text(encoding="utf-8")
        parsed_id, title = parse_task_markdown(destination.name, body)
        return TaskRecord(
            task_id=parsed_id,
            title=title,
            state=target_state,
            path=str(destination.relative_to(self.project_dir)),
            body=body,
        )

    # -- usage metrics -------------------------------------------------------

    def _usage_yaml_path(self) -> Path:
        return self.project_dir / METRICS_USAGE_PATH

    def _usage_jsonl_path(self) -> Path:
        return self.project_dir / METRICS_USAGE_JSONL

    def record_usage(self, record: UsageRecord) -> None:
        # Append a single line so recording is O(1) instead of rewriting the
        # whole file each time, which matters as the log grows.
        path = self._usage_jsonl_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.to_dict(), ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def list_usage(
        self,
        scope: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> List[UsageRecord]:
        records: List[UsageRecord] = []
        # Legacy YAML records (written before the JSONL log) are still read.
        yaml_path = self._usage_yaml_path()
        if yaml_path.is_file():
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or []
            if not isinstance(data, list):
                raise StoreError(f"Invalid usage metrics file: {yaml_path}")
            records.extend(UsageRecord.from_dict(item) for item in data)
        jsonl_path = self._usage_jsonl_path()
        if jsonl_path.is_file():
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(UsageRecord.from_dict(json.loads(line)))
                except json.JSONDecodeError as exc:
                    raise StoreError(f"Invalid usage metrics line: {exc}") from exc
        if scope is not None:
            records = [item for item in records if item.scope == scope]
        if ref is not None:
            records = [item for item in records if item.ref == ref]
        return records
