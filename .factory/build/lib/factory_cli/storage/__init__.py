from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import TaskRecord, TaskStore, UsageAggregate, UsageRecord
from .folder import FolderTaskStore, StoreError
from .hybrid import HybridTaskStore

if TYPE_CHECKING:  # pragma: no cover
    from ..models import FactoryConfig

__all__ = [
    "TaskRecord",
    "TaskStore",
    "UsageAggregate",
    "UsageRecord",
    "FolderTaskStore",
    "HybridTaskStore",
    "StoreError",
    "open_store",
]


def open_store(
    project_dir: Path,
    config: Optional["FactoryConfig"] = None,
) -> TaskStore:
    """Return the configured storage backend for a project.

    Defaults to the folder backend so existing projects behave unchanged. The
    hybrid backends keep the folder files authoritative and add a database
    mirror for fast queries and shared (Postgres) metrics.
    """
    backend = getattr(config, "storage_backend", "folder") if config else "folder"
    folder = FolderTaskStore(project_dir)
    if backend == "folder":
        return folder
    if backend == "folder+sqlite":
        from .sqlite import SqliteTaskStore

        return HybridTaskStore(folder, SqliteTaskStore(project_dir))
    if backend == "folder+postgres":
        from .postgres import PostgresTaskStore

        dsn = getattr(config, "storage_dsn", None) if config else None
        return HybridTaskStore(folder, PostgresTaskStore(dsn or ""))
    raise StoreError(f"Unsupported storage backend: {backend}")
