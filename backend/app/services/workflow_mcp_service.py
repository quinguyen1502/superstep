"""Workflows as MCP tools (TASK-0114, DEC-0061): what the MCP server at /mcp lists and calls for a workflow token.

A workflow token (`wft_…`, the public API's credential) scopes a client to one workflow, so the server it sees has
three tools: `run_<workflow>` (input schema = the workflow's state fields), `get_run` and `resume_run`. The owner opts
the workflow in (`mcp_enabled`, under API in the editor); otherwise every call answers MCP_SERVER_DISABLED. Runs are
ordinary queued API runs (history source `api`, same rate limit and input checks as POST /api/hooks/.../runs).
A run that pauses at a Human node returns `status: waiting` with its `run_id` and prompt; `resume_run` answers it.
This module has no MCP dependency: `api/mcp_server.py` adapts it to the SDK."""
from __future__ import annotations
import asyncio, json, re
from typing import Any, Optional
from ..core import config
from ..core.errors import AppError
from ..engine.state_schema import state_schema
from ..models import WorkflowToken
from ..repositories import WorkflowRepository
from .trigger_service import TriggerService

GET_RUN, RESUME_RUN = "get_run", "resume_run"
NAME_MAX = 64  # MCP clients commonly cap tool names at 64 characters
RUN_ID = {"run_id": {"type": "string", "description": "The run id returned by the run tool."}}


def tool_name(workflow_name: Optional[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (workflow_name or "").lower()).strip("_")
    return ("run_" + slug)[:NAME_MAX].rstrip("_") if slug else "run_workflow"


class WorkflowMcpService:
    def __init__(self, triggers: TriggerService, workflows: WorkflowRepository):
        self.triggers, self.workflows = triggers, workflows

    # ---- owner settings (JWT) ----
    def settings(self, wid: str, uid: str) -> dict:
        self.triggers._owned(wid, uid)
        w = self.workflows.get(wid)
        return {"enabled": bool(w.mcp_enabled), "tool": tool_name(w.name), "path": "/mcp"}

    def set_enabled(self, wid: str, uid: str, enabled: bool) -> dict:
        self.triggers._owned(wid, uid)
        self.workflows.set_mcp(wid, enabled)
        return self.settings(wid, uid)

    # ---- MCP (workflow token) ----
    def authenticate(self, token: Optional[str]) -> WorkflowToken:
        tok = self.triggers.authenticate(None, token)
        w = self.workflows.get(tok.workflow_id)
        if w is None or not w.mcp_enabled: raise AppError("MCP_SERVER_DISABLED")
        return tok

    def tools(self, tok: WorkflowToken) -> list[dict]:
        w = self.workflows.get(tok.workflow_id)
        wf = json.loads(w.data or "{}")
        desc = (wf.get("description") or "").strip()
        run = {"name": tool_name(w.name), "title": w.name or "Workflow",
               "description": f"Run the Superstep workflow \"{w.name}\"" + (f": {desc}" if desc else ".") +
                              " Returns the final state; a run paused at a Human node returns status `waiting`, its run_id "
                              f"and prompt: answer it with {RESUME_RUN}. A run still going returns its run_id: poll {GET_RUN}.",
               "input_schema": state_schema(wf, "Input")}
        return [run,
                {"name": GET_RUN, "title": "Get a run", "description": "Status and result of a run of this workflow.",
                 "input_schema": {"type": "object", "properties": RUN_ID, "required": ["run_id"]}},
                {"name": RESUME_RUN, "title": "Answer a Human node",
                 "description": "Answer the Human node a waiting run is paused at (text, or true / false to approve / reject) and wait for it to settle again.",
                 "input_schema": {"type": "object", "properties": {**RUN_ID, "response": {"type": ["string", "boolean"], "description": "The answer."}},
                                  "required": ["run_id", "response"]}}]

    async def call(self, tok: WorkflowToken, name: str, args: dict[str, Any]) -> dict:
        """Run the tool; the public run result (`hooks` GET shape). Raises AppError."""
        timeout = min(config.sync_wait_max(), config.run_timeout() + 5)
        if name == GET_RUN: return await asyncio.to_thread(self.triggers.result, tok, str(args.get("run_id") or ""))
        if name == RESUME_RUN:
            rid = str(args.get("run_id") or "")
            since = await asyncio.to_thread(self.triggers.resume, tok, rid, args.get("response"))
            return await self.triggers.wait(tok, rid, timeout, since)
        w = await asyncio.to_thread(self.workflows.get, tok.workflow_id)
        if name != tool_name(w.name): raise AppError("MCP_TOOL_NOT_FOUND", tool=name)
        await self.triggers.check_rate(tok)
        rid = await asyncio.to_thread(self.triggers.start, tok, args, None)
        return await self.triggers.wait(tok, rid, timeout)
