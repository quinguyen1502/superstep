from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


@dataclass
class UsageRecord:
    """A single token/cost usage entry attributed to a task or agent."""

    scope: str
    ref: str
    tool_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    recorded_at: str = ""
    note: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return int(self.input_tokens) + int(self.output_tokens)

    def to_dict(self) -> Dict[str, object]:
        return {
            "scope": self.scope,
            "ref": self.ref,
            "tool_id": self.tool_id,
            "input_tokens": int(self.input_tokens),
            "output_tokens": int(self.output_tokens),
            "cost_usd": float(self.cost_usd),
            "recorded_at": self.recorded_at,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "UsageRecord":
        return cls(
            scope=str(data.get("scope", "")),
            ref=str(data.get("ref", "")),
            tool_id=str(data.get("tool_id", "")),
            input_tokens=int(data.get("input_tokens", 0) or 0),
            output_tokens=int(data.get("output_tokens", 0) or 0),
            cost_usd=float(data.get("cost_usd", 0.0) or 0.0),
            recorded_at=str(data.get("recorded_at", "")),
            note=(str(data["note"]) if data.get("note") is not None else None),
        )


@dataclass
class UsageAggregate:
    """Token/cost totals grouped by a dimension key (ref or tool)."""

    key: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    entries: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TaskStore(ABC):
    """Backend-agnostic access to lifecycle tasks and usage metrics."""

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

    @abstractmethod
    def record_usage(self, record: UsageRecord) -> None:
        ...

    @abstractmethod
    def list_usage(
        self,
        scope: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> List[UsageRecord]:
        ...

    def forget(self, task_ids: List[str]) -> None:
        """Drop tasks from any database mirror (e.g. after archiving).

        The folder backend keeps the files as truth and overrides nothing here;
        database-backed stores remove the rows.
        """

    def aggregate_usage(self, by: str = "ref") -> List[UsageAggregate]:
        """Group usage records by 'ref', 'tool', or 'scope'."""
        if by not in {"ref", "tool", "scope"}:
            raise ValueError("Aggregate usage by must be ref, tool, or scope.")
        groups: Dict[str, UsageAggregate] = {}
        for record in self.list_usage():
            if by == "tool":
                key = record.tool_id
            elif by == "scope":
                key = record.scope
            else:
                key = f"{record.scope}:{record.ref}"
            bucket = groups.setdefault(key, UsageAggregate(key=key))
            bucket.input_tokens += int(record.input_tokens)
            bucket.output_tokens += int(record.output_tokens)
            bucket.cost_usd += float(record.cost_usd)
            bucket.entries += 1
        return [groups[key] for key in sorted(groups)]

    def usage_for_key(self, budget_key: str) -> int:
        """Total tokens recorded for a budget key such as 'task:TASK-0001'."""
        scope, _, ref = budget_key.partition(":")
        return sum(
            record.total_tokens
            for record in self.list_usage(scope=scope or None, ref=ref or None)
        )


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
