"""Engine-level errors (no web/HTTP knowledge)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class Interrupt(Exception):
    """Raised by a Human node that has no response yet: the run pauses (status `waiting`) at `node` (TASK-0006).
    extra: more fields for the `run_waiting` event (an Agent tool approval adds label, tool and arguments, TASK-0117)."""
    def __init__(self, node: str, prompt: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(f"Waiting for a human response at {node}")
        self.node, self.prompt, self.extra = node, prompt, extra or {}
