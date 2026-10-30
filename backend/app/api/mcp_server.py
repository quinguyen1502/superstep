"""MCP server at /mcp (TASK-0114, DEC-0061; PAT + X-Superstep-Workflow, TASK-0171).

The official MCP Python SDK serves Streamable HTTP, stateless JSON (any API replica can answer; runs live in the database).

Clients authenticate with `X-Workflow-Token: wft_…` or `Authorization: Bearer wft_…`, or with `Authorization: Bearer pat_…`
plus `X-Superstep-Workflow`. A bad token is the JSON envelope, not JSON-RPC, before the SDK runs (401 TRIGGER_TOKEN_INVALID
or 403 MCP_SERVER_DISABLED). An unknown or revoked `pat_` is TRIGGER_TOKEN_INVALID here, not AUTH_TOKEN_INVALID.
Tools and their behaviour: services/workflow_mcp_service.py."""
from __future__ import annotations
import asyncio, json
from contextlib import asynccontextmanager
from typing import Optional
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from ..core import permissions as P
from ..core.errors import AppError
from ..repositories import PersonalAccessTokenRepository, WorkflowRepository
from ..services.pat_service import PAT_PREFIX, digest as pat_digest
from .deps import access_service, auth_service, get_db, workflow_mcp_service
from .error_handlers import respond

PATH = "/mcp"
PAT_HEADER = "x-superstep-workflow"


def token_of(headers) -> Optional[str]:
    """X-Workflow-Token wins over Authorization: Bearer (as hooks.workflow_token)."""
    if tok := (headers.get("x-workflow-token") or "").strip(): return tok
    auth = headers.get("authorization") or ""
    return auth[7:].strip() if auth.lower().startswith("bearer ") else None


def resolve_pat(headers) -> tuple[str, str, str]:
    """(user id, workflow id, PAT id) for a `pat_` bearer plus `X-Superstep-Workflow`. Does not build a workflow token."""
    token = token_of(headers) or ""
    wid = (headers.get(PAT_HEADER) or "").strip()
    if not token.startswith(PAT_PREFIX) or not wid: raise AppError("TRIGGER_TOKEN_INVALID")
    try: user = auth_service().current(token)
    except AppError as exc:
        if exc.code == "AUTH_TOKEN_INVALID": raise AppError("TRIGGER_TOKEN_INVALID") from None
        raise
    row = PersonalAccessTokenRepository(get_db()).by_hash(pat_digest(token))
    if row is None or row.revoked is not None: raise AppError("TRIGGER_TOKEN_INVALID")
    if not access_service().may(wid, user["id"], P.VIEW): raise AppError("TRIGGER_TOKEN_INVALID")
    workflow = WorkflowRepository(get_db()).get(wid)
    if workflow is None or not workflow.mcp_enabled: raise AppError("MCP_SERVER_DISABLED")
    return user["id"], wid, row.id


def admit(headers) -> None:
    """Auth before the SDK. A workflow token stays on its own workflow; the PAT header does not retarget it."""
    token = token_of(headers) or ""
    if token.startswith(PAT_PREFIX):
        resolve_pat(headers); return
    workflow_mcp_service().authenticate(token)


def _tools_of(headers) -> list[dict]:
    svc = workflow_mcp_service()
    token = token_of(headers) or ""
    if token.startswith(PAT_PREFIX):
        uid, wid, pat_id = resolve_pat(headers)
        return svc.tools_for(uid, wid, pat_id)
    return svc.tools(svc.authenticate(token))


async def _call_of(headers, name: str, arguments: dict) -> dict:
    svc = workflow_mcp_service()
    token = token_of(headers) or ""
    if token.startswith(PAT_PREFIX):
        uid, wid, pat_id = await asyncio.to_thread(resolve_pat, headers)
        return await svc.call_for(uid, wid, pat_id, name, arguments)
    tok = await asyncio.to_thread(svc.authenticate, token)
    return await svc.call(tok, name, arguments)


server: Server = Server("superstep", instructions="Superstep workflows as tools. A run paused at a Human node returns status "
                        "`waiting` with its run_id: answer it with resume_run; poll unfinished runs with get_run.")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    headers = server.request_context.request.headers
    return [types.Tool(name=t["name"], title=t["title"], description=t["description"], inputSchema=t["input_schema"])
            for t in await asyncio.to_thread(_tools_of, headers)]


@server.call_tool(validate_input=False)  # the run's input checks answer with our error codes
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    headers = server.request_context.request.headers
    try: res = await _call_of(headers, name, arguments or {})
    except AppError as e:
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"error": e.to_dict()}))],
                                    structuredContent={"error": e.to_dict()}, isError=True)
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res, ensure_ascii=False))],
                                structuredContent=res, isError=res.get("status") in ("error", "timeout", "expired"))


class McpApp:
    """ASGI app mounted at /mcp: token check, then the SDK's session manager."""
    manager: Optional[StreamableHTTPSessionManager] = None

    @asynccontextmanager
    async def running(self):
        """One session manager per app lifespan (the SDK's `run()` works once per manager)."""
        self.manager = StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)
        async with self.manager.run(): yield
        self.manager = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            try: await asyncio.to_thread(admit, Request(scope).headers)
            except AppError as e:
                await respond(e)(scope, receive, send); return
        if self.manager is None:  # served outside the lifespan (a TestClient used without `with`)
            async with self.running(): await self.manager.handle_request(scope, receive, send)
            return
        await self.manager.handle_request(scope, receive, send)
