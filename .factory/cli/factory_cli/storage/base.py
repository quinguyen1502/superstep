from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TaskRecord:
    """A lifecycle task as seen by any storage backend."""

    task_id: str
    title: str
    state: str
    path: Optional[str] = None
    body: Optional[str] = None
    owner: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "state": self.state,
            "path": self.path,
        }


class TaskStore(ABC):
    """Backend-agnostic access to lifecycle tasks."""

    @abstractmethod
    def list_tasks(self) -> List[TaskRecord]:
        ...

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        ...

    @abstractmethod
    def create_task(self, task_id: str, title: str, state: str) -> TaskRecord:
        ...

    @abstractmethod
    def move_task(self, task_id: str, target_state: str) -> TaskRecord:
        ...

    def forget(self, task_ids: List[str]) -> None:
        """Hook for stores that mirror tasks outside the Markdown files."""
        del task_ids


_TASK_ID_RE = re.compile(r"^-\s*Task ID:\s*(?P<id>\S+)\s*$", re.MULTILINE)
_OWNER_RE = re.compile(r"^-\s*Owner:\s*(?P<owner>.+?)\s*$", re.MULTILINE)
_IN_SCOPE_RE = re.compile(
    r"###\s+In Scope\s*\n\s*\n-\s*(?P<title>.+?)\s*\n", re.MULTILINE
)


def parse_task_markdown(filename: str, body: str) -> "tuple[str, str]":
    """Best-effort extraction of (task_id, title) from a rendered task file."""
    task_id = ""
    match = _TASK_ID_RE.search(body)
    if match:
        task_id = match.group("id").strip()
    if not task_id:
        task_id = filename.split("-")[0] if "-" in filename else filename
    title = ""
    scope_match = _IN_SCOPE_RE.search(body)
    if scope_match:
        title = scope_match.group("title").strip()
    if not title:
        stem = filename[: -len(".md")] if filename.endswith(".md") else filename
        remainder = stem[len(task_id) + 1 :] if stem.startswith(task_id) else stem
        title = remainder.replace("-", " ").strip() or stem
    return task_id, title


def parse_task_owner(body: str) -> Optional[str]:
    """Extract the Owner metadata value from a rendered task, if set."""
    match = _OWNER_RE.search(body)
    if not match:
        return None
    owner = match.group("owner").strip()
    return owner or None
