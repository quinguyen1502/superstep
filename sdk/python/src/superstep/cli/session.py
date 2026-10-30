"""The CLI's saved server URL and personal access token (TASK-0167, DEC-0071).

`SUPERSTEP_URL` and `SUPERSTEP_TOKEN` win over `~/.superstep/cli.json`. A flag wins over the environment for the URL.
The token is never read from the command line.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import httpx

import superstep

_AUTH = {
    "AUTH_REQUIRED": "error.login_required",
    "AUTH_TOKEN_INVALID": "error.login_required",
    "AUTH_TOKEN_EXPIRED": "error.login_required",
    "AUTH_ACCOUNT_DISABLED": "error.login_required",
    "CLI_DEVICE_DENIED": "error.denied",
    "CLI_DEVICE_EXPIRED": "error.expired",
    "CLI_DEVICE_INVALID": "error.device",
}


class SessionError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def config_path() -> Path:
    return Path.home() / ".superstep" / "cli.json"


def load_config() -> dict:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False))
    os.chmod(path, 0o600)


def resolve_target(url_flag: Optional[str] = None) -> tuple[str, str]:
    """Base URL and token. `--url`, then `SUPERSTEP_URL`, then the file. The token is the env var, then the file."""
    data = load_config()
    url = url_flag or os.environ.get("SUPERSTEP_URL") or data.get("url") or ""
    token = os.environ.get("SUPERSTEP_TOKEN") or data.get("token") or ""
    if not isinstance(url, str):
        url = ""
    if not isinstance(token, str):
        token = ""
    return url.rstrip("/"), token


def store_login(url: str, token: str, account: str) -> None:
    data = load_config()
    data["url"] = url
    data["token"] = token
    data["account"] = account
    write_config(data)


def clear_login() -> None:
    """Drop the token and the account. Leave `lang`, `current` and `url` in place."""
    path = config_path()
    if not path.is_file():
        return
    data = load_config()
    data.pop("token", None)
    data.pop("account", None)
    write_config(data)


def join_uri(base: str, uri: str) -> str:
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    if not uri.startswith("/"):
        uri = "/" + uri
    return base.rstrip("/") + uri


def call(method: str, base: str, path: str, client: Optional[httpx.Client] = None, body: Optional[dict] = None,
         token: Optional[str] = None, phase2: bool = False, errors: Optional[dict] = None):
    """One envelope call. `phase2` turns a missing route into SERVER_TOO_OLD."""
    url = base.rstrip("/") + path
    headers = {"Accept": "application/json", "User-Agent": "superstep-cli/" + superstep.__version__}
    if token:
        headers["Authorization"] = "Bearer " + token
    owned = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        try:
            kwargs = {"json": body} if body is not None else {}
            response = http.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError:
            raise SessionError("CONNECTION_FAILED", "error.connection", url=base)
    finally:
        if owned:
            http.close()
    if response.status_code == 404 and phase2:
        raise SessionError("SERVER_TOO_OLD", "error.server_old", version=_version(base, client))
    try:
        payload = response.json()
    except ValueError:
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=base)
    if not isinstance(payload, dict):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=base)
    if payload.get("success") is True:
        return payload.get("data")
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error.get("code") or "BAD_RESPONSE")
    key = _AUTH.get(code)
    if key:
        raise SessionError(code, key)
    if errors is not None and code in errors:
        raise SessionError(code, errors[code])
    raise SessionError("BAD_RESPONSE", "error.bad_response", url=base)


def _version(base: str, client: Optional[httpx.Client]) -> str:
    try:
        data = call("GET", base, "/api/health", client=client)
    except SessionError:
        return "unknown"
    if isinstance(data, dict) and data.get("version"):
        return str(data["version"])
    return "unknown"
