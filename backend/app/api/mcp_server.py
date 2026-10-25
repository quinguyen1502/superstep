"""MCP server at /mcp (TASK-0114, DEC-0061): the official MCP Python SDK, Streamable HTTP transport, stateless JSON
responses (any API replica can answer any request; runs live in the shared database).

Clients authenticate like the public API: `X-Workflow-Token: wft_…` or `Authorization: Bearer wft_…`. A request without
a valid token for an MCP-enabled workflow is answered before the MCP layer with the common error envelope (401
TRIGGER_TOKEN_INVALID or 403 MCP_SERVER_DISABLED). Tools and their behaviour: services/workflow_mcp_service.py."""
from __future__ import annotations
import asyncio, json
from contextlib import asynccontextmanager
from typing import Optional
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from ..core.errors import AppError
from .deps import workflow_mcp_service
from .error_handlers import respond

PATH = "/mcp"


def token_of(headers) -> Optional[str]:
    """X-Workflow-Token wins over Authorization: Bearer (as hooks.workflow_token)."""
    if tok := (headers.get("x-workflow-token") or "").strip(): return tok
    auth = headers.get("authorization") or ""
    return auth[7:].strip() if auth.lower().startswith("bearer ") else None


def _token() -> str:
    req: Request = server.request_context.request
    return token_of(req.headers) or ""


server: Server = Server("superstep", instructions="Superstep workflows as tools. A run paused at a Human node returns status "
                        "`waiting` with its run_id: answer it with resume_run; poll unfinished runs with get_run.")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    svc = workflow_mcp_service()
    tok = await asyncio.to_thread(svc.authenticate, _token())
    return [types.Tool(name=t["name"], title=t["title"], description=t["description"], inputSchema=t["input_schema"])
            for t in await asyncio.to_thread(svc.tools, tok)]


@server.call_tool(validate_input=False)  # the run's input checks answer with our error codes
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    svc = workflow_mcp_service()
    try:
        tok = await asyncio.to_thread(svc.authenticate, _token())
        res = await svc.call(tok, name, arguments or {})
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
            try: await asyncio.to_thread(workflow_mcp_service().authenticate, token_of(Request(scope).headers))
            except AppError as e:
                await respond(e)(scope, receive, send); return
        if self.manager is None:  # served outside the lifespan (a TestClient used without `with`)
            async with self.running(): await self.manager.handle_request(scope, receive, send)
            return
        await self.manager.handle_request(scope, receive, send)
