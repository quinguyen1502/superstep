from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import TaskRecord, TaskStore
from .folder import FolderTaskStore, StoreError

if TYPE_CHECKING:  # pragma: no cover
    from ..models import FactoryConfig

__all__ = [
    "TaskRecord",
    "TaskStore",
    "FolderTaskStore",
    "StoreError",
    "open_store",
]


def open_store(
    project_dir: Path,
    config: Optional["FactoryConfig"] = None,
) -> TaskStore:
    """Return the folder store. Markdown files are the only task state.

    Older configs may still name ``storage_backend``; those values are ignored.
    """
    del config
    return FolderTaskStore(project_dir)
