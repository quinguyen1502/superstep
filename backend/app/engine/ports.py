"""Run-time ports: services a node may call, bound to the run's user by the service layer (/0013).

The engine only sees these callables, never repositories or HTTP clients of other features, so node executors stay
testable with plain functions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

Retrieve = Callable[[str, str, int], List[Dict[str, Any]]]   # (knowledge_base_id, query, top_k) -> chunks
McpCall = Callable[[str, str, Dict[str, Any]], Any]          # (server_id, tool, arguments) -> result
EmailQuota = Callable[[int], None]                           # (recipients) -> None, raises EMAIL_RATE_LIMITED
Cancelled = Callable[[], bool]                               # True once the run was cancelled or timed out
CodeAudit = Callable[[], None]                               # records that Code nodes ran without isolation
# (call key, child workflow, its version, input, {workflow_id, label}) -> child run id; at most one child per key
Attachment = Callable[[str], Optional[Tuple[str, bytes]]]  # chat attachment id -> (MIME, bytes) or None
StartChild = Callable[[str, Dict[str, Any], Optional[int], Dict[str, Any], Dict[str, Any]], str]


@dataclass
class Ports:
    browser: Optional[Any] = None  # trusted per-run scope; never supplied by workflow/model arguments
    retrieve: Optional[Retrieve] = None
    mcp_call: Optional[McpCall] = None
    mcp_effect_call: Optional[Callable[[str, str, dict, Optional[str], bool], Any]] = None
    email_quota: Optional[EmailQuota] = None
    cancelled: Optional[Cancelled] = None
    code_audit: Optional[CodeAudit] = None
    attachment: Optional[Attachment] = None  # image bytes of chat attachments, read at call time ( decision 2)
    start_child: Optional[StartChild] = None  # workflow tools of Agent nodes; bound by the run service per run
    dataset_call: Optional[Callable[[dict, dict, Optional[str]], dict]] = None  # server-bound Dataset execution
    test: bool = False         # a workflow test run: Send email nodes do a dry run
    mock_models: bool = False  # a test run with the offline mock model: LLM and Decision nodes never call a provider
    locale: str = "en"         # language of offline answers: the mock model and the example tools (engine/locale)

    def prepare_browsers(self, group, batch, calls):
        if self.browser is None or self.test or self.mock_models:return {}
        return self.browser.prepare(group,batch,calls)

    def cache_mcp(self,node,state):
        if self.browser is None or self.test or self.mock_models:return True
        data=node.get('data') or {}
        if node['type']=='mcp':return not self.browser.is_browser(data.get('server_id'))
        if node['type']=='agent_tool':
            from . import agents
            calls=((state.get(agents.private(agents.owner(node))) or {}).get('pending')) or []
            index=agents.slot_index(node['id'])-1
            if index>=len(calls):return True
            tool=next((item for item in data.get('tools') or [] if item.get('name')==calls[index]['name']),{})
            return tool.get('source')!='mcp' or not self.browser.is_browser(tool.get('server_id'))
        return True

    def call_mcp(self, server_id, tool, arguments, key=None, *, group=None, ticket=None):
        if self.browser is not None and not (self.test or self.mock_models) and self.browser.is_browser(server_id):
            if group is None or key is None:raise RuntimeError('Browser requires a trusted run group and call key')
            if ticket is None:
                ticket=self.browser.prepare(group,key,[{'index':0,'server_id':server_id,'tool':tool,'arguments':arguments}]).get(0)
            return self.browser.call(group,ticket,tool,arguments)
        if self.mcp_effect_call is not None:
            return self.mcp_effect_call(server_id, tool, arguments, key, self.test or self.mock_models)
        if self.mcp_call is None: raise RuntimeError("MCP tools need the MCP service")
        return self.mcp_call(server_id, tool, arguments)
