"""`run` and `runs` (TASK-0169, DEC-0071 decision 5).

The socket stays open until the run ends: closing it cancels the run. A waiting run is not answered.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlencode, urlparse, urlunparse

import httpx

from superstep.cli.i18n import Catalog
from superstep.cli.install import _fail
from superstep.cli.session import SessionError, call, resolve_target

DEFAULT_TIMEOUT = 300.0
_EXIT = {"ok": 0, "paused": 0, "error": 1, "waiting": 2, "timeout": 3, "cancelled": 4}
_TRACE = {"run_started", "run_finished", "run_waiting", "error"}
_NOT_FOUND = {"WORKFLOW_NOT_FOUND": "error.workflow_not_found"}
_RUN_MISSING = {"RUN_NOT_FOUND": "error.run_not_found"}


class _Outcome:
    def __init__(self, status: Optional[str], run_id: Optional[str], final_state, local_timeout: bool):
        self.status = status
        self.run_id = run_id
        self.final_state = final_state
        self.local_timeout = local_timeout


def add_commands(commands, common, catalog: Catalog) -> None:
    run = _parser(commands, common, catalog, "run", "help.run", "example.run")
    run.add_argument("workflow", help=catalog.format("help.workflow_ref"))
    run.add_argument("--input", help=catalog.format("help.input"))
    run.add_argument("--follow", action="store_true", help=catalog.format("help.run_follow"))
    run.add_argument("--timeout", type=_timeout, default=DEFAULT_TIMEOUT, help=catalog.format("help.timeout"))
    run.add_argument("--url", help=catalog.format("help.url"))
    run.set_defaults(run=cmd_run)

    runs = _parser(commands, common, catalog, "runs", "help.runs", "example.runs")
    nested = runs.add_subparsers(dest="runs_command", required=True, parser_class=type(runs))
    listing = _parser(nested, common, catalog, "list", "help.runs_list", "example.runs_list")
    listing.add_argument("--workflow", help=catalog.format("help.runs_workflow"))
    listing.add_argument("--url", help=catalog.format("help.url"))
    listing.set_defaults(run=cmd_runs_list)
    show = _parser(nested, common, catalog, "show", "help.runs_show", "example.runs_show")
    show.add_argument("run_id", help=catalog.format("help.run_id"))
    show.add_argument("--url", help=catalog.format("help.url"))
    show.set_defaults(run=cmd_runs_show)
    cancel = _parser(nested, common, catalog, "cancel", "help.runs_cancel", "example.runs_cancel")
    cancel.add_argument("run_id", help=catalog.format("help.run_id"))
    cancel.add_argument("--url", help=catalog.format("help.url"))
    cancel.set_defaults(run=cmd_runs_cancel)


def cmd_run(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    _quiet()
    try:
        base, token = _require(args)
        payload = _load_input(getattr(args, "input", None))
        workflow_id = _workflow_id(base, token, args.workflow, client)
        outcome = asyncio.run(_drive(
            base, token, workflow_id, payload, bool(args.follow), float(args.timeout), catalog,
            getattr(args, "connect", None),
        ))
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if outcome.local_timeout:
        sys.stderr.write(catalog.format("run.timeout", seconds=_plain(format(float(args.timeout), "g"))) + "\n")
    code = _EXIT.get(outcome.status or "", 1)
    if json_mode:
        _write_json({"ok": code == 0, "run_id": outcome.run_id, "status": outcome.status, "final_state": outcome.final_state})
    return code


def cmd_runs_list(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    _quiet()
    try:
        base, token = _require(args)
        if args.workflow:
            workflow_id = _workflow_id(base, token, args.workflow, client)
            data = call("GET", base, "/api/workflows/" + quote(workflow_id, safe="") + "/runs", client=client, token=token,
                        errors=_NOT_FOUND)
            rows = _rows(data, base)
            lines = [catalog.format("runs.row", id=_plain(row.get("id")), status=_plain(row.get("status"))) for row in rows]
        else:
            data = call("GET", base, "/api/runs/pending", client=client, token=token)
            rows = _rows(data, base)
            lines = [_pending_line(catalog, row) for row in rows]
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "runs": rows})
        return 0
    sys.stderr.write(("\n".join(lines) if lines else catalog.format("runs.none")) + "\n")
    return 0


def cmd_runs_show(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    _quiet()
    try:
        base, token = _require(args)
        data = call("GET", base, "/api/runs/" + quote(args.run_id, safe=""), client=client, token=token, errors=_RUN_MISSING)
        if not isinstance(data, dict):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=_plain(base))
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "run": data})
        return 0
    workflow = data.get("workflow_name") or data.get("workflow_id")
    sys.stderr.write(catalog.format("runs.show", id=_plain(data.get("id")), status=_plain(data.get("status")),
                                    workflow=_plain(workflow)) + "\n")
    return 0


def cmd_runs_cancel(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    _quiet()
    try:
        base, token = _require(args)
        data = call("POST", base, "/api/runs/" + quote(args.run_id, safe="") + "/cancel", client=client, token=token,
                    errors=_RUN_MISSING)
        if not isinstance(data, dict):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=_plain(base))
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        body = {"ok": True}
        body.update(data)
        _write_json(body)
        return 0
    sys.stderr.write(catalog.format("runs.cancelled", run_id=_plain(data.get("run_id") or args.run_id)) + "\n")
    return 0


def _workflow_id(base: str, token: str, selector: str, client: Optional[httpx.Client]) -> str:
    """An id, or an exact name. Two names are AMBIGUOUS. No match is the server's WORKFLOW_NOT_FOUND."""
    rows = call("GET", base, "/api/workflows", client=client, token=token)
    if not isinstance(rows, list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=_plain(base))
    by_id = [row for row in rows if isinstance(row, dict) and row.get("id") == selector]
    if by_id:
        return str(by_id[0]["id"])
    by_name = [row for row in rows if isinstance(row, dict) and row.get("name") == selector]
    if len(by_name) > 1:
        raise SessionError("AMBIGUOUS", "error.ambiguous", name=_plain(selector))
    if len(by_name) == 1:
        return str(by_name[0]["id"])
    loaded = call("GET", base, "/api/workflows/" + quote(selector, safe=""), client=client, token=token, errors=_NOT_FOUND)
    if isinstance(loaded, dict) and loaded.get("id"):
        return str(loaded["id"])
    raise SessionError("WORKFLOW_NOT_FOUND", "error.workflow_not_found")


def _require(args) -> tuple[str, str]:
    base, token = resolve_target(getattr(args, "url", None))
    if not base:
        raise SessionError("URL_REQUIRED", "error.url_required")
    if not token:
        raise SessionError("AUTH_REQUIRED", "error.login_required")
    return base, token


def _load_input(path: Optional[str]) -> dict:
    if path is None:
        return {}
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    except OSError:
        raise SessionError("INPUT_INVALID", "error.input")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise SessionError("INPUT_INVALID", "error.input")
    if not isinstance(data, dict):
        raise SessionError("INPUT_INVALID", "error.input")
    return data


def _socket_url(base: str, token: str) -> str:
    parts = urlparse(base)
    scheme = "wss" if parts.scheme == "https" else "ws"
    path = (parts.path or "").rstrip("/") + "/ws/run"
    return urlunparse((scheme, parts.netloc, path, "", urlencode({"token": token}), ""))


def _open(url: str):
    """Real client. Tests pass their own connect and never call this."""
    import websockets
    return websockets.connect(url, open_timeout=30, close_timeout=5, logger=_socket_logger())


async def _drive(base: str, token: str, workflow_id: str, payload: dict, follow: bool, timeout: float, catalog: Catalog,
                 connect) -> _Outcome:
    opener = connect or _open
    start = {"workflow_id": workflow_id, "input": payload}
    url = _socket_url(base, token)
    try:
        async with opener(url) as ws:
            try:
                await ws.send(json.dumps(start))
            except Exception:
                raise SessionError("CONNECTION_FAILED", "error.connection", url=_plain(base)) from None
            return await _read(ws, follow, timeout, catalog, base)
    except SessionError:
        raise
    except Exception as exc:
        if not _network(exc):
            raise
        raise SessionError("CONNECTION_FAILED", "error.connection", url=_plain(base)) from None


def _network(exc: BaseException) -> bool:
    if isinstance(exc, (OSError, asyncio.TimeoutError, TimeoutError, EOFError)):
        return True
    return type(exc).__name__ in {
        "ConnectionClosed", "ConnectionClosedOK", "ConnectionClosedError", "InvalidURI", "InvalidHandshake",
        "InvalidStatus", "InvalidStatusCode", "InvalidMessage", "SecurityError", "InvalidProxy", "ProxyError",
    }


async def _read(ws, follow: bool, timeout: float, catalog: Catalog, base: str) -> _Outcome:
    status: Optional[str] = None
    run_id: Optional[str] = None
    final_state = None
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            await _cancel(ws)
            return _Outcome("timeout", run_id, final_state, True)
        try:
            raw = await asyncio.wait_for(_recv(ws), remaining)
        except (asyncio.TimeoutError, TimeoutError):
            await _cancel(ws)
            return _Outcome("timeout", run_id, final_state, True)
        except (StopAsyncIteration, EOFError):
            break
        except Exception as exc:
            if type(exc).__name__.startswith("ConnectionClosed"):
                break
            if _network(exc):
                raise SessionError("CONNECTION_FAILED", "error.connection", url=_plain(base)) from None
            raise
        try:
            event = _event(raw)
        except (json.JSONDecodeError, UnicodeError, TypeError):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=_plain(base))
        if event.get("run_id"):
            run_id = str(event["run_id"])
        status, final_state, done = _apply(event, status, final_state)
        if follow and _traceable(event):
            sys.stderr.write(_trace_line(catalog, event) + "\n")
        if event.get("type") == "run_waiting":
            sys.stderr.write(catalog.format("run.prompt", prompt=_plain(event.get("prompt"))) + "\n")
        if done:
            break
    return _Outcome(status, run_id, final_state, False)


def _apply(event: dict, status: Optional[str], final_state):
    kind = event.get("type")
    done = False
    if kind == "run_finished":
        final_state = event.get("state")
        if status is None:
            status = "ok"
    elif kind == "error":
        status = str(event.get("status") or "error")
    elif kind == "run_waiting":
        status = "waiting"
        if "state" in event:
            final_state = event.get("state")
    elif kind == "run_paused":
        status = "paused"
        if "state" in event:
            final_state = event.get("state")
    elif kind == "run_cancelled":
        status = "cancelled"
    elif kind == "run_summary":
        if event.get("status"):
            status = str(event["status"])
        done = True
    return status, final_state, done


async def _recv(ws):
    recv = getattr(ws, "recv", None)
    if recv is not None:
        return await recv()
    return await ws.__anext__()


async def _cancel(ws) -> None:
    try:
        await ws.send(json.dumps({"type": "cancel"}))
    except Exception:
        return None


def _event(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("event")
    return data


def _traceable(event: dict) -> bool:
    if event.get("type") in _TRACE:
        return True
    node = event.get("node")
    return isinstance(node, str) and node != ""


def _trace_line(catalog: Catalog, event: dict) -> str:
    kind = str(event.get("type") or "")
    if kind == "run_started":
        return catalog.format("run.started", run_id=_plain(event.get("run_id")))
    if kind == "run_finished":
        return catalog.format("run.finished")
    if kind == "run_waiting":
        return catalog.format("run.waiting", node=_plain(_node_name(event)))
    if kind == "error":
        return catalog.format("run.error", message=_plain(_error_message(event)))
    return catalog.format("run.node", type=_plain(kind), node=_plain(_node_name(event)))


def _node_name(event: dict) -> str:
    node = "" if event.get("node") is None else str(event.get("node"))
    label = event.get("label")
    if label and str(label) != node:
        return (node + " " + str(label)).strip()
    return node


def _error_message(event: dict) -> str:
    err = event.get("error")
    if isinstance(err, dict) and err.get("message"):
        return str(err["message"])
    errors = event.get("errors")
    if isinstance(errors, list) and errors:
        return str(errors[0])
    return ""


def _pending_line(catalog: Catalog, row: dict) -> str:
    workflow = row.get("workflow_name") or row.get("workflow_id")
    return catalog.format("runs.pending", id=_plain(row.get("id")), workflow=_plain(workflow), node=_plain(row.get("node")),
                          prompt=_plain(row.get("prompt")))


def _rows(data, base: str) -> list:
    if not isinstance(data, list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=_plain(base))
    return [row for row in data if isinstance(row, dict)]


def _plain(value: object) -> str:
    """Brace-escape values before Catalog.format, which is str.format."""
    if value is None:
        return ""
    return str(value).replace("{", "{{").replace("}", "}}")


def _timeout(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError(value)
    return number


def _quiet() -> None:
    for name in ("httpx", "httpcore", "websockets"):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def _socket_logger() -> logging.Logger:
    log = logging.getLogger("superstep.cli.run.socket")
    log.setLevel(logging.CRITICAL)
    log.propagate = False
    return log


def _write_json(payload: dict) -> None:
    from superstep.cli import _write_json as write
    write(payload)


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    return commands.add_parser(
        name,
        parents=[common],
        help=catalog.format(help_key),
        description=catalog.format(help_key),
        epilog=catalog.format(example_key),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
