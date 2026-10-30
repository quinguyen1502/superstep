"""`workflows`, `pull` and `push` (TASK-0168, DEC-0071 decision 4)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse

import httpx

import superstep
from superstep.cli.i18n import Catalog
from superstep.cli.session import SessionError, _AUTH, _version, call, resolve_target

# Exporter ids in backend/app/engine/exporters.py. typescript's route id is "typescript".
# langgraph is the Python project zip, not a third exporter.
_EXPORT = {
    "python": "/export/python",
    "typescript": "/export/typescript",
    "langgraph": "/export/python/project",
}
_EXT = {"json": ".json", "python": ".py", "typescript": ".ts", "langgraph": ".zip"}
_STRIP = frozenset(("access", "mine", "owner_email", "version", "updated"))
_NOT_FOUND = {"WORKFLOW_NOT_FOUND": "error.not_found"}


def add_commands(commands, common, catalog: Catalog) -> None:
    from superstep.cli import _Parser

    workflows = _parser(commands, common, catalog, "workflows", "help.workflows", "example.workflows")

    class _Sub(_Parser):
        def __init__(self, *args, **kwargs):
            kwargs["catalog"] = workflows.catalog
            kwargs["json_mode"] = workflows.json_mode
            super().__init__(*args, **kwargs)

    subs = workflows.add_subparsers(dest="workflows_command", required=True, parser_class=_Sub)
    listing = _sub(subs, common, catalog, "list", "help.workflows_list", "example.workflows_list")
    listing.add_argument("--url", help=catalog.format("help.url"))
    listing.set_defaults(run=cmd_list)

    export = _sub(subs, common, catalog, "export", "help.workflows_export", "example.workflows_export")
    export.add_argument("workflow", help=catalog.format("help.workflow"))
    export.add_argument("--format", required=True, choices=("json", "python", "typescript", "langgraph"), help=catalog.format("help.format"))
    export.add_argument("--output", help=catalog.format("help.output"))
    export.add_argument("--url", help=catalog.format("help.url"))
    export.set_defaults(run=cmd_export)

    imported = _sub(subs, common, catalog, "import", "help.workflows_import", "example.workflows_import")
    imported.add_argument("file")
    imported.add_argument("--url", help=catalog.format("help.url"))
    imported.set_defaults(run=cmd_import)

    pull = _parser(commands, common, catalog, "pull", "help.pull", "example.pull")
    pull.add_argument("directory")
    pull.add_argument("--url", help=catalog.format("help.url"))
    pull.set_defaults(run=cmd_pull)

    push = _parser(commands, common, catalog, "push", "help.push", "example.push")
    push.add_argument("directory")
    push.add_argument("--force", action="store_true", help=catalog.format("help.force"))
    push.add_argument("--url", help=catalog.format("help.url"))
    push.set_defaults(run=cmd_push)


def cmd_list(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    try:
        url, token = _target(args)
        rows = _workflow_list(url, token, client)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "workflows": rows})
    elif rows:
        for row in rows:
            _write_err(catalog.format("workflows.row", name=str(row.get("name") or ""), id=str(row.get("id") or ""), version=str(_row_version(row))) + "\n")
    else:
        _write_err(catalog.format("workflows.empty") + "\n")
    return 0


def cmd_export(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    try:
        url, token = _target(args)
        wid = _resolve(url, token, client, args.workflow)
        if args.format == "json":
            detail = _get(url, token, client, wid)
            content = _dump(_strip(detail)).encode("utf-8")
        else:
            content = _raw(url, "/api/workflows/" + quote(wid, safe="") + _EXPORT[args.format], client, token)
        dest = Path(args.output) if args.output else Path.cwd() / (wid + _EXT[args.format])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "id": wid, "format": args.format, "file": str(dest)})
    else:
        _write_err(catalog.format("workflows.wrote", file=str(dest)) + "\n")
    return 0


def cmd_import(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    path = Path(args.file)
    try:
        body = _load_import(path)
        url, token = _target(args)
        result = call("POST", url, "/api/workflows", client=client, body=_post_body(body), token=token, phase2=True, errors=_NOT_FOUND)
        if not isinstance(result, dict) or not result.get("id"):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        wid = str(result["id"])
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "id": wid})
    else:
        _write_err(catalog.format("workflows.imported", id=wid) + "\n")
    return 0


def cmd_pull(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    directory = Path(args.directory)
    try:
        url, token = _target(args)
        rows = _workflow_list(url, token, client)
        details = []
        for row in rows:
            wid = row.get("id")
            if not isinstance(wid, str) or not wid:
                raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
            details.append(_get(url, token, client, wid))
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(directory))
        locked = {}
        for detail in details:
            wid = str(detail["id"])
            (directory / (wid + ".json")).write_text(_dump(_strip(detail)), encoding="utf-8")
            locked[wid] = {"name": str(detail.get("name") or ""), "version": _row_version(detail)}
        _write_lock(directory, url, locked)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "directory": str(directory), "workflows": locked})
    else:
        _write_err(catalog.format("pull.done", count=str(len(locked)), directory=str(directory)) + "\n")
    return 0


def cmd_push(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    directory = Path(args.directory)
    try:
        url, token = _target(args)
        lock = _read_lock(directory)
        _refuse_wrong_server(lock, url, bool(args.force))
        files = _read_workflows(directory)
        server = _by_id(_workflow_list(url, token, client))
        _refuse_conflicts(files, server, _lock_map(lock), bool(args.force))
        pushed, unchanged = _save_files(url, token, client, files, server, bool(args.force))
        if pushed or args.force:
            server = _by_id(_workflow_list(url, token, client))
            _write_lock(directory, url, _lock_from(files, server, url))
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "pushed": pushed, "unchanged": unchanged})
    elif pushed:
        _write_err(catalog.format("push.done", count=str(len(pushed))) + "\n")
    else:
        _write_err(catalog.format("push.unchanged") + "\n")
    return 0


def _target(args) -> tuple:
    url, token = resolve_target(getattr(args, "url", None))
    if not url:
        raise SessionError("URL_REQUIRED", "error.url_required")
    if not token:
        raise SessionError("AUTH_REQUIRED", "error.login_required")
    return url, token


def _workflow_list(url: str, token: str, client: Optional[httpx.Client]) -> list:
    rows = call("GET", url, "/api/workflows", client=client, token=token, phase2=True, errors=_NOT_FOUND)
    if not isinstance(rows, list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    return rows


def _get(url: str, token: str, client: Optional[httpx.Client], wid: str) -> dict:
    detail = call("GET", url, "/api/workflows/" + quote(wid, safe=""), client=client, token=token, phase2=True, errors=_NOT_FOUND)
    if not isinstance(detail, dict) or not detail.get("id"):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    return detail


def _resolve(url: str, token: str, client: Optional[httpx.Client], name: str) -> str:
    rows = _workflow_list(url, token, client)
    for row in rows:
        if isinstance(row, dict) and row.get("id") == name:
            return str(row["id"])
    matches = [row for row in rows if isinstance(row, dict) and row.get("name") == name and row.get("id")]
    if len(matches) == 1:
        return str(matches[0]["id"])
    if len(matches) > 1:
        raise SessionError("AMBIGUOUS", "error.ambiguous", name=name)
    raise SessionError("WORKFLOW_NOT_FOUND", "error.not_found", name=name)


def _raw(base: str, path: str, client: Optional[httpx.Client], token: str) -> bytes:
    """A route that returns the file itself, not the JSON envelope. A 404 is SERVER_TOO_OLD."""
    url = base.rstrip("/") + path
    headers = {"Accept": "*/*", "User-Agent": "superstep-cli/" + superstep.__version__}
    if token:
        headers["Authorization"] = "Bearer " + token
    owned = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        try:
            response = http.request("GET", url, headers=headers)
        except httpx.HTTPError:
            raise SessionError("CONNECTION_FAILED", "error.connection", url=base)
    finally:
        if owned:
            http.close()
    if 200 <= response.status_code < 300:
        return response.content
    if response.status_code == 404:
        raise SessionError("SERVER_TOO_OLD", "error.server_old", version=_version(base, client))
    code = _error_code(response)
    key = _AUTH.get(code) if code else None
    if key:
        raise SessionError(code, key)
    if code and code in _NOT_FOUND:
        raise SessionError(code, _NOT_FOUND[code])
    raise SessionError("BAD_RESPONSE", "error.bad_response", url=base)


def _error_code(response: httpx.Response) -> Optional[str]:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = error.get("code")
    return str(code) if code else None


def _load_import(path: Path) -> dict:
    if path.suffix.lower() in {".py", ".ts", ".zip"}:
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
    if not isinstance(data, dict):
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
    return data


def _strip(data: dict) -> dict:
    return {key: value for key, value in data.items() if key not in _STRIP}


def _post_body(data: dict) -> dict:
    body = _strip(data)
    if not body.get("id"):
        body.pop("id", None)
    return body


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _read_lock(directory: Path) -> Optional[dict]:
    path = directory / ".superstep" / "lock.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
    if not isinstance(data, dict):
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
    return data


def _lock_map(lock: Optional[dict]) -> dict:
    if not lock:
        return {}
    raw = lock.get("workflows") or {}
    if not isinstance(raw, dict):
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file="lock.json")
    return raw


def _write_lock(directory: Path, url: str, workflows: dict) -> None:
    path = directory / ".superstep" / "lock.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump({"format": 1, "url": url, "workflows": workflows}), encoding="utf-8")


def _read_workflows(directory: Path) -> list:
    if not directory.is_dir():
        raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(directory))
    found = []
    paths = sorted((path for path in directory.glob("*.json") if path.is_file()), key=lambda path: path.name)
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
        if not isinstance(data, dict):
            raise SessionError("NOT_A_WORKFLOW", "error.not_a_workflow", file=str(path))
        found.append((path, data))
    return found


def _origin(url: str) -> tuple:
    parts = urlparse(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if parts.port is not None:
        port = parts.port
    elif scheme == "https":
        port = 443
    elif scheme == "http":
        port = 80
    else:
        port = None
    return scheme, host, port


def _refuse_wrong_server(lock: Optional[dict], url: str, force: bool) -> None:
    if force or lock is None:
        return
    lock_url = lock.get("url")
    if not isinstance(lock_url, str) or _origin(lock_url) != _origin(url):
        raise SessionError("WRONG_SERVER", "error.wrong_server", lock_url=str(lock_url or ""), url=url)


def _by_id(rows: list) -> dict:
    return {row["id"]: row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)}


def _refuse_conflicts(files: list, server: dict, locked: dict, force: bool) -> None:
    if force:
        return
    for _path, body in files:
        wid = body.get("id")
        if not isinstance(wid, str) or wid not in server:
            continue
        have = locked.get(wid)
        if not isinstance(have, dict) or _as_int(have.get("version")) != _row_version(server[wid]):
            name = str(server[wid].get("name") or body.get("name") or wid)
            raise SessionError("WORKFLOW_CHANGED", "error.workflow_changed", name=name)


def _save_files(url: str, token: str, client: Optional[httpx.Client], files: list, server: dict, force: bool) -> tuple:
    pushed, unchanged = [], []
    for path, body in files:
        wid = body.get("id") if isinstance(body.get("id"), str) and body.get("id") else None
        if wid in server and not force:
            remote = _get(url, token, client, wid)
            if _strip(body) == _strip(remote):
                unchanged.append(wid)
                continue
        result = call("POST", url, "/api/workflows", client=client, body=_post_body(body), token=token, phase2=True, errors=_NOT_FOUND)
        if not isinstance(result, dict) or not result.get("id"):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        new_id = str(result["id"])
        if body.get("id") != new_id:
            body["id"] = new_id
            path.write_text(_dump(_strip(body)), encoding="utf-8")
        pushed.append(new_id)
    return pushed, unchanged


def _lock_from(files: list, server: dict, url: str) -> dict:
    locked = {}
    for _path, body in files:
        wid = body.get("id")
        if not isinstance(wid, str) or wid not in server:
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        row = server[wid]
        locked[wid] = {"name": str(row.get("name") or body.get("name") or ""), "version": _row_version(row)}
    return locked


def _row_version(row: dict) -> int:
    if not isinstance(row, dict) or row.get("version") is None:
        return 0
    number = _as_int(row.get("version"))
    return number if number is not None else 0


def _as_int(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _write_json(payload: dict) -> None:
    from superstep.cli import _write_json as write
    write(payload)


def _write_err(text: str) -> None:
    from superstep.cli import _write_err as write
    write(text)


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    from superstep.cli.install import _parser as parser
    return parser(commands, common, catalog, name, help_key, example_key)


def _sub(subs, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    import argparse
    return subs.add_parser(
        name,
        parents=[common],
        help=catalog.format(help_key),
        description=catalog.format(help_key),
        epilog=catalog.format(example_key),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
