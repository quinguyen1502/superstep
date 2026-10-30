"""Engine-level errors (no web/HTTP knowledge)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from langgraph.errors import GraphBubbleUp


class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class Interrupt(GraphBubbleUp):
    """Raised by a Human node that has no response yet: the run pauses (status `waiting`) at `node` (TASK-0006).
    A GraphBubbleUp so a parallel sibling in the same superstep still finishes (TASK-0158).
    extra: more fields for the `run_waiting` event (an Agent tool approval adds label, tool and arguments, TASK-0117)."""
    def __init__(self, node: str, prompt: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(f"Waiting for a human response at {node}")
        self.node, self.prompt, self.extra = node, prompt, extra or {}


class AwaitChild(Interrupt):
    """Raised by an Agent tool step that started a child run for a workflow tool (TASK-0134, DEC-0066): the run waits for
    the child as it waits for a person (status `waiting`, with `wait` on the event and the checkpoint), and the step gets
    the child's result when the run service resumes it."""
    def __init__(self, node: str, child_run_id: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(node, "", {**(extra or {}), "wait": {"kind": "child", "run_id": child_run_id}})
