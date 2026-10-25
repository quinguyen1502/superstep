"""Effectively-once side effects (TASK-0021, DEC-0018).

Execution is at-least-once (a crashed worker's job runs again). To make side effects effectively-once:
- every LLM/Tool node execution gets a stable **idempotency key** derived from (run id, node id, iteration), sent as the
  `Idempotency-Key` header by HTTP Tool nodes and passed to Python tools that accept `idempotency_key`. A retry of the
  same node execution (after a crash) sends the same key, so an idempotent receiver applies it once.
- a **node-result ledger** stores each finished side-effect node's state update; when the node runs again for the same
  (run, node, iteration) the stored update is returned instead of executing it again.
- a **guard** (fencing check) runs before every side-effect node so a worker that lost its lease stops before acting.
The engine stays storage-agnostic: the service layer passes a `Ledger` (get/put) and the guard.
"""
from __future__ import annotations
import hashlib, inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Protocol

SIDE_EFFECT_TYPES = ("llm", "tool", "decision", "email", "agent_model", "agent_tool")  # Decision: a paid call; Send email: never sent twice;
# an Agent node's model and tool steps (TASK-0116): one ledger entry and idempotency key per model call and per tool call


class Ledger(Protocol):
    def get(self, node_id: str, iteration: int) -> Optional[dict]: ...
    def put(self, node_id: str, iteration: int, delta: dict, key: str) -> None: ...


def idempotency_key(run_id: str, node_id: str, iteration: int) -> str:
    """Stable per (run, node, iteration): the same execution retried after a crash reuses it."""
    return "studio-" + hashlib.sha256(f"{run_id}:{node_id}:{iteration}".encode()).hexdigest()[:32]


@dataclass
class Effects:
    run_id: str
    attempt: int = 1                      # queue delivery attempt (1 = first; recovered jobs > 1), sent as X-Studio-Attempt
    ledger: Optional[Ledger] = None
    guard: Optional[Callable[[], None]] = None  # raises when this worker may no longer act for the run (fencing)
    counts: Dict[str, int] = field(default_factory=dict)  # node id -> iteration, kept by the runtime
    reused: set = field(default_factory=set)              # node ids whose last result came from the ledger

    def key(self, node_id: str) -> str: return idempotency_key(self.run_id, node_id, self.counts.get(node_id, 1))

    def headers(self, node_id: str) -> dict:
        return {"Idempotency-Key": self.key(node_id), "X-Studio-Run-Id": self.run_id, "X-Studio-Attempt": str(self.attempt)}

    def wrap(self, node: Dict[str, Any], fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        """Ledger + guard around a side-effect node; other node types are pure and run as they are."""
        if node["type"] not in SIDE_EFFECT_TYPES: return fn
        nid = node["id"]

        def run(state):
            it = self.counts.get(nid, 1)
            if self.ledger is not None and (hit := self.ledger.get(nid, it)) is not None:
                self.reused.add(nid); return hit
            if self.guard is not None: self.guard()
            out = fn(state)
            if self.ledger is not None: self.ledger.put(nid, it, out or {}, self.key(nid))
            return out
        return run


def call_tool(fn: Callable, state: dict, key: Optional[str], locale: str = "en") -> Any:
    """Python tools opt in to the idempotency key by declaring an `idempotency_key` parameter, and to the run's
    language (engine/locale) by declaring `locale`."""
    params = inspect.signature(fn).parameters
    kw = {**({"idempotency_key": key} if key and "idempotency_key" in params else {}), **({"locale": locale} if "locale" in params else {})}
    return fn(state, **kw)
