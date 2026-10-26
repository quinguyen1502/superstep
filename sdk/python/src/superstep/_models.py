"""Typed models of the public API payloads (docs/api/openapi.public.json; tests/test_spec_sync.py keeps them in step)."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, Literal, Optional, Tuple

RunStatus = Literal["queued", "running", "ok", "error", "cancelled", "timeout", "waiting", "expired"]
PENDING: Tuple[str, ...] = ("queued", "running")


def _pick(cls, data: Optional[Dict[str, Any]]):
    if data is None: return None
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


@dataclass(frozen=True)
class RunMetrics:
    duration_ms: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None
    error_count: Optional[int] = None


@dataclass(frozen=True)
class RunWaiting:
    """The Human node a `waiting` run is paused at, or the child run of a workflow tool it waits for (`child_run_id`)."""
    node: Optional[str] = None
    prompt: Optional[str] = None
    child_run_id: Optional[str] = None


@dataclass(frozen=True)
class Run:
    """A run as returned by `run()` and `get_run()`. A just-queued run has only `run_id`, `status` and `poll_url`."""
    run_id: str
    status: RunStatus
    workflow_id: Optional[str] = None
    source: Optional[str] = None
    final_state: Optional[Dict[str, Any]] = None
    error: Optional[Any] = None
    waiting: Optional[RunWaiting] = None
    parent_run_id: Optional[str] = None  # the run whose Agent node called this one as a workflow tool
    metrics: Optional[RunMetrics] = None
    trace_url: Optional[str] = None
    started: Optional[float] = None
    ended: Optional[float] = None
    poll_url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def done(self) -> bool:
        """True once the run has stopped changing (any status but `queued` / `running`)."""
        return self.status not in PENDING

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Run":
        plain = {f.name for f in fields(cls)} - {"waiting", "metrics", "raw"}
        return cls(**{k: v for k, v in data.items() if k in plain}, waiting=_pick(RunWaiting, data.get("waiting")),
                   metrics=_pick(RunMetrics, data.get("metrics")), raw=dict(data))
