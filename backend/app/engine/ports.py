"""Run-time ports: services a node may call, bound to the run's user by the service layer (TASK-0012/0013).

The engine only sees these callables, never repositories or HTTP clients of other features, so node executors stay
testable with plain functions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

Retrieve = Callable[[str, str, int], List[Dict[str, Any]]]   # (knowledge_base_id, query, top_k) -> chunks
McpCall = Callable[[str, str, Dict[str, Any]], Any]          # (server_id, tool, arguments) -> result
EmailQuota = Callable[[int], None]                           # (recipients) -> None, raises EMAIL_RATE_LIMITED (TASK-0051)
Cancelled = Callable[[], bool]                               # True once the run was cancelled or timed out (TASK-0053)
CodeAudit = Callable[[], None]                               # records that Code nodes ran without isolation (TASK-0056)
# (call key, child workflow, its version, input, {workflow_id, label}) -> child run id; at most one child per key (TASK-0134)
Attachment = Callable[[str], Optional[Tuple[str, bytes]]]  # chat attachment id -> (MIME, bytes) or None (TASK-0176)
StartChild = Callable[[str, Dict[str, Any], Optional[int], Dict[str, Any], Dict[str, Any]], str]


@dataclass
class Ports:
    retrieve: Optional[Retrieve] = None
    mcp_call: Optional[McpCall] = None
    email_quota: Optional[EmailQuota] = None
    cancelled: Optional[Cancelled] = None
    code_audit: Optional[CodeAudit] = None
    attachment: Optional[Attachment] = None  # image bytes of chat attachments, read at call time (DEC-0072 decision 2)
    start_child: Optional[StartChild] = None  # workflow tools of Agent nodes (DEC-0066); bound by the run service per run
    test: bool = False         # a workflow test run (TASK-0067, DEC-0044): Send email nodes do a dry run
    mock_models: bool = False  # a test run with the offline mock model: LLM and Decision nodes never call a provider
    locale: str = "en"         # language of offline answers: the mock model and the example tools (engine/locale)
