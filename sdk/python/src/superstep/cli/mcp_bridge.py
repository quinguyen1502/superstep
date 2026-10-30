"""`superstep mcp`: a local stdio MCP server that forwards tools to the studio (TASK-0171, DEC-0071).

Stdout is only the protocol while the server runs. The process speaks the newline-delimited JSON the MCP Python SDK
1.x stdio client writes, and also Content-Length frames. It does not import `mcp` and it does not create a workflow token.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

import httpx

import superstep
from superstep.cli.i18n import Catalog
from superstep.cli.session import SessionError, call, resolve_target

_METHOD_NOT_FOUND = -32601
_INTERNAL = -32603
_MCP_ACCEPT = "application/json, text/event-stream"
_HEADER = "X-Superstep-Workflow"


def add_commands(commands, common, catalog: Catalog) -> None:
    mcp = commands.add_parser(
        "mcp",
        parents=[common],
        help=catalog.format("help.mcp"),
        description=catalog.format("help.mcp"),
        epilog=catalog.format("example.mcp"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mcp.add_argument("workflows", nargs="*", metavar="workflow", help=catalog.format("help.mcp_workflow"))
    mcp.add_argument("--url", help=catalog.format("help.url"))
    mcp.set_defaults(run=cmd_mcp)


def cmd_mcp(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker,
            stdin=None, stdout=None) -> int:
    # `--json` would write a document onto the protocol stream. Reject it before any request or stdin read.
    if json_mode:
        sys.stderr.write(catalog.format("error.usage", message="mcp does not accept --json") + "\n")
        return 2
    names = list(getattr(args, "workflows", None) or [])
    if not names:
        sys.stderr.write(catalog.format("error.usage", message="workflow is required") + "\n")
        return 2
    owned = client is None
    http = client or httpx.Client(timeout=120.0, trust_env=False)
    try:
        try:
            url, token = resolve_target(getattr(args, "url", None))
            if not token:
                raise SessionError("AUTH_REQUIRED", "error.login_required")
            if not url:
                raise SessionError("URL_REQUIRED", "error.url_required")
            workflows = resolve_workflows(http, url, token, names)
        except SessionError as exc:
            return _fail(catalog, exc.code, exc.key, **exc.fmt)
        return serve(workflows, url, token, catalog, http, stdin if stdin is not None else sys.stdin.buffer,
                     stdout if stdout is not None else sys.stdout.buffer)
    finally:
        if owned:
            http.close()


def resolve_workflows(http: httpx.Client, url: str, token: str, names: list[str]) -> list[dict]:
    """Each arg is an id, or an exact name. Two names is AMBIGUOUS. MCP off, or not visible, is MCP_DISABLED."""
    rows = call("GET", url, "/api/workflows", client=http, token=token)
    if not isinstance(rows, list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    chosen = []
    for arg in names:
        by_id = [row for row in rows if isinstance(row, dict) and row.get("id") == arg]
        if by_id:
            chosen.append(by_id[0])
            continue
        by_name = [row for row in rows if isinstance(row, dict) and row.get("name") == arg]
        if len(by_name) > 1:
            raise SessionError("AMBIGUOUS", "error.ambiguous", name=arg)
        if len(by_name) == 1:
            chosen.append(by_name[0])
            continue
        raise SessionError("MCP_DISABLED", "error.mcp_disabled", name=arg)
    ready = []
    for row in chosen:
        wid = str(row.get("id") or "")
        label = str(row.get("name") or wid)
        _require_enabled(http, url, token, wid, label)
        ready.append({"id": wid, "name": label})
    return ready


def _require_enabled(http: httpx.Client, url: str, token: str, wid: str, label: str) -> None:
    try:
        data = call("GET", url, "/api/workflows/" + wid + "/mcp", client=http, token=token, phase2=True, errors={
            "WORKFLOW_FORBIDDEN": "error.mcp_disabled",
            "WORKFLOW_NOT_FOUND": "error.mcp_disabled",
            "MCP_SERVER_DISABLED": "error.mcp_disabled",
        })
    except SessionError as exc:
        if exc.code == "SERVER_TOO_OLD":
            raise
        if exc.code in ("WORKFLOW_FORBIDDEN", "WORKFLOW_NOT_FOUND", "MCP_SERVER_DISABLED"):
            raise SessionError("MCP_DISABLED", "error.mcp_disabled", name=label) from None
        raise
    if not isinstance(data, dict) or not data.get("enabled"):
        raise SessionError("MCP_DISABLED", "error.mcp_disabled", name=label)


def serve(workflows: list[dict], url: str, token: str, catalog: Catalog, http: httpx.Client, stdin, stdout) -> int:
    """Read stdio frames until EOF. `workflows` is already checked; this is the only place that reads stdin."""
    owners: dict[str, tuple[str, str]] = {}
    while True:
        try:
            incoming = read_message(stdin)
        except (json.JSONDecodeError, ValueError, UnicodeError):
            _log("invalid JSON")
            continue
        if incoming is None:
            return 0
        payload, framed = incoming
        if not isinstance(payload, dict):
            _log("invalid JSON")
            continue
        response = _dispatch(payload, framed, workflows, url, token, catalog, http, owners)
        if response is None:
            continue
        message, framed_out = response
        write_message(stdout, message, framed_out)


def _dispatch(payload: dict, framed: bool, workflows: list[dict], url: str, token: str, catalog: Catalog,
              http: httpx.Client, owners: dict) -> Optional[tuple[dict, bool]]:
    method = payload.get("method")
    req_id = payload.get("id")
    has_id = "id" in payload
    if method == "initialize" and has_id:
        return _result(req_id, _initialize(payload.get("params"))), framed
    if method == "ping" and has_id:
        return _result(req_id, {}), framed
    if method == "tools/list" and has_id:
        try:
            tools = _listed(http, url, token, workflows, owners)
        except SessionError as exc:
            _log(catalog.format(exc.key, **exc.fmt))
            return _error(req_id, _INTERNAL, exc.code), framed
        return _result(req_id, {"tools": tools}), framed
    if method == "tools/call" and has_id:
        try:
            result = _called(http, url, token, workflows, owners, payload.get("params") or {})
        except SessionError as exc:
            _log(catalog.format(exc.key, **exc.fmt))
            return _error(req_id, _INTERNAL, exc.code), framed
        return _result(req_id, result), framed
    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    if not has_id:
        return None
    return _error(req_id, _METHOD_NOT_FOUND, "Method not found"), framed


def _initialize(params) -> dict:
    version = "2025-03-26"
    if isinstance(params, dict) and params.get("protocolVersion"):
        version = str(params["protocolVersion"])
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": "superstep", "version": superstep.__version__},
        "instructions": "Superstep workflows as tools. This process speaks MCP on stdio.",
    }


def _listed(http, url, token, workflows, owners) -> list[dict]:
    exposed, found = _merge(_groups(http, url, token, workflows))
    owners.clear()
    owners.update(found)
    return exposed


def _called(http, url, token, workflows, owners, params) -> dict:
    name = str((params or {}).get("name") or "")
    if name not in owners:
        _listed(http, url, token, workflows, owners)
    if name not in owners:
        return {"content": [{"type": "text", "text": "MCP_TOOL_NOT_FOUND"}], "isError": True}
    wid, original = owners[name]
    arguments = (params or {}).get("arguments") or {}
    payload = _post(http, url, token, wid, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                            "params": {"name": original, "arguments": arguments}})
    if "result" in payload:
        result = payload["result"]
        return result if isinstance(result, dict) else {"content": [{"type": "text", "text": json.dumps(result)}], "isError": False}
    return {"content": [{"type": "text", "text": _remote_message(payload)}], "isError": True}


def _groups(http, url, token, workflows) -> list[tuple[str, str, list]]:
    groups = []
    for workflow in workflows:
        payload = _post(http, url, token, workflow["id"], {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        tools = []
        if isinstance(payload.get("result"), dict):
            tools = payload["result"].get("tools") or []
        elif "error" in payload:
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        groups.append((workflow["id"], workflow["name"], tools if isinstance(tools, list) else []))
    return groups


def merge_tools(groups: list[tuple[str, str, list]]) -> tuple[list[dict], dict[str, tuple[str, str]]]:
    """First tool keeps its name. A later one with the same name gets `_<first 6 of the workflow id>`."""
    return _merge(groups)


def _merge(groups: list[tuple[str, str, list]]) -> tuple[list[dict], dict[str, tuple[str, str]]]:
    used: set[str] = set()
    exposed: list[dict] = []
    owners: dict[str, tuple[str, str]] = {}
    for wid, wname, tools in groups:
        for tool in tools:
            if not isinstance(tool, dict) or not tool.get("name"):
                continue
            original = str(tool["name"])
            name = original
            if name in used:
                name = original + "_" + wid[:6]
                extra = 1
                while name in used:
                    extra += 1
                    name = original + "_" + wid[:6] + "_" + str(extra)
            used.add(name)
            description = str(tool.get("description") or "")
            if wname and wname not in description:
                description = (description + " " if description else "") + wname
            schema = tool.get("inputSchema") or tool.get("input_schema") or {"type": "object", "properties": {}}
            item = {"name": name, "description": description, "inputSchema": schema}
            if tool.get("title"):
                item["title"] = tool["title"]
            exposed.append(item)
            owners[name] = (wid, original)
    return exposed, owners


def _post(http: httpx.Client, url: str, token: str, wid: str, message: dict) -> dict:
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": _MCP_ACCEPT,
        "Content-Type": "application/json",
        _HEADER: wid,
    }
    try:
        response = http.post(url.rstrip("/") + "/mcp", json=message, headers=headers)
    except httpx.HTTPError:
        raise SessionError("CONNECTION_FAILED", "error.connection", url=url) from None
    try:
        payload = response.json()
    except ValueError:
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url) from None
    if not isinstance(payload, dict):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    return payload


def _remote_message(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error.get("code") or error["message"])
    return "MCP request failed"


def _result(req_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def read_message(stream) -> Optional[tuple[dict, bool]]:
    """One JSON-RPC message. Content-Length (LSP) or one newline-delimited JSON object. None at EOF."""
    line = _readline(stream)
    if line is None:
        return None
    stripped = line.strip()
    if not stripped:
        return read_message(stream)
    if stripped.lower().startswith(b"content-length:"):
        headers = [stripped]
        while True:
            nxt = _readline(stream)
            if nxt is None:
                return None
            if nxt.strip() == b"":
                break
            headers.append(nxt.strip())
        length = 0
        for header in headers:
            if header.lower().startswith(b"content-length:"):
                length = int(header.split(b":", 1)[1].strip() or b"0")
        body = _read_exact(stream, length)
        return json.loads(body.decode("utf-8")), True
    return json.loads(stripped.decode("utf-8")), False


def write_message(stream, payload: dict, framed: bool) -> None:
    """Reply in the framing the request used. The MCP SDK 1.x stdio client uses a single JSON line."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if framed:
        stream.write(("Content-Length: %d\r\n\r\n" % len(data)).encode("ascii") + data)
    else:
        stream.write(data + b"\n")
    stream.flush()


def _readline(stream) -> Optional[bytes]:
    buf = bytearray()
    while True:
        chunk = stream.read(1)
        if not chunk:
            return bytes(buf) if buf else None
        buf += chunk
        if chunk == b"\n":
            return bytes(buf)


def _read_exact(stream, length: int) -> bytes:
    buf = bytearray()
    while len(buf) < length:
        chunk = stream.read(length - len(buf))
        if not chunk:
            break
        buf += chunk
    return bytes(buf)


def _log(text: str) -> None:
    sys.stderr.write(text + ("" if text.endswith("\n") else "\n"))


def _fail(catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(False, catalog, code, key, **fmt)
