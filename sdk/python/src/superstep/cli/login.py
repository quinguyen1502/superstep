"""`login`, `logout` and `whoami` (TASK-0167, DEC-0071)."""
from __future__ import annotations

import argparse
import sys
import time
import webbrowser
from typing import Optional

import httpx

from superstep.cli.i18n import Catalog
from superstep.cli.session import SessionError, call, clear_login, join_uri, resolve_target, store_login


def add_commands(commands, common, catalog: Catalog) -> None:
    login = _parser(commands, common, catalog, "login", "help.login", "example.login")
    login.add_argument("--url", help=catalog.format("help.url"))
    login.add_argument("--name", help=catalog.format("help.token_name"))
    login.add_argument("--no-browser", action="store_true", help=catalog.format("help.no_browser"))
    login.set_defaults(run=cmd_login)

    logout = _parser(commands, common, catalog, "logout", "help.logout", "example.logout")
    logout.set_defaults(run=cmd_logout)

    whoami = _parser(commands, common, catalog, "whoami", "help.whoami", "example.whoami")
    whoami.add_argument("--url", help=catalog.format("help.url"))
    whoami.set_defaults(run=cmd_whoami)


def cmd_login(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    try:
        url, _token = resolve_target(args.url)
        if not url:
            raise SessionError("URL_REQUIRED", "error.url_required")
        started = call("POST", url, "/api/auth/cli/devices", client=client, body={"name": args.name} if args.name else {}, phase2=True)
        if not isinstance(started, dict) or not started.get("device_code") or not started.get("verification_uri"):
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        page = join_uri(url, str(started["verification_uri"]))
        code = str(started.get("user_code") or "")
        # The code has to be readable while the command is still waiting, including when --json keeps stdout for the result.
        sys.stderr.write(catalog.format("login.visit", url=page, code=code) + "\n")
        if not args.no_browser:
            try:
                webbrowser.open(page)
            except Exception:
                pass
        secret = _poll(url, str(started["device_code"]), client, float(started.get("expires_in") or 600), float(started.get("interval") or 1))
        me = call("GET", url, "/api/me", client=client, token=secret)
        account = str(me.get("email") or "") if isinstance(me, dict) else ""
        if not account:
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
        store_login(url, secret, account)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "account": account, "url": url})
    else:
        sys.stderr.write(catalog.format("login.signed_in", account=account) + "\n")
    return 0


def cmd_logout(_args, catalog: Catalog, json_mode: bool, _client, _parser, _docker) -> int:
    clear_login()
    if json_mode:
        _write_json({"ok": True})
    else:
        sys.stderr.write(catalog.format("logout.done") + "\n")
    return 0


def cmd_whoami(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    try:
        url, token = resolve_target(getattr(args, "url", None))
        if not url:
            raise SessionError("URL_REQUIRED", "error.url_required")
        if not token:
            raise SessionError("AUTH_REQUIRED", "error.login_required")
        me = call("GET", url, "/api/me", client=client, token=token)
        account = str(me.get("email") or "") if isinstance(me, dict) else ""
        if not account:
            raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    if json_mode:
        _write_json({"ok": True, "account": account, "url": url})
    else:
        sys.stderr.write(catalog.format("whoami.account", account=account) + "\n")
    return 0


def _poll(url: str, device_code: str, client: Optional[httpx.Client], expires_in: float, interval: float) -> str:
    deadline = time.time() + max(0.0, expires_in)
    while True:
        try:
            data = call("GET", url, "/api/auth/cli/devices/" + device_code, client=client, phase2=True)
        except SessionError:
            raise
        if isinstance(data, dict) and data.get("status") == "pending":
            if time.time() >= deadline:
                raise SessionError("CLI_DEVICE_EXPIRED", "error.expired")
            time.sleep(max(0.0, float(data.get("interval") or interval)))
            continue
        if isinstance(data, dict) and data.get("token"):
            return str(data["token"])
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


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
