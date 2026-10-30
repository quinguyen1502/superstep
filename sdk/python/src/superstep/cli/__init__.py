"""The `superstep` command. Phase 1 starts with `version` and `completion`; later tasks add commands here."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx

import superstep
from superstep.cli.admin import add_commands as add_admin_commands
from superstep.cli.backup import add_commands as add_backup_commands
from superstep.cli.deploy import add_commands as add_deploy_commands
from superstep.cli.docker import Docker
from superstep.cli.i18n import Catalog, lang_flag, resolve_lang
from superstep.cli.install import add_commands
from superstep.cli.login import add_commands as add_login_commands
from superstep.cli.run import add_commands as add_run_commands
from superstep.cli.status import add_commands as add_status_commands
from superstep.cli.upgrade import add_commands as add_upgrade_commands
from superstep.cli.suite import add_commands as add_suite_commands
from superstep.cli.workflows import add_commands as add_workflow_commands

_TIMEOUT = 5.0


class CliError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def main(argv: Optional[list[str]] = None) -> None:
    sys.exit(run(argv))


def run(argv: Optional[list[str]] = None, client: Optional[httpx.Client] = None, docker: Optional[Docker] = None, ssh=None,
        connect: Optional[Callable] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args
    catalog = Catalog.load(resolve_lang(lang_flag(args)))
    parser = _parser(catalog, json_mode)
    try:
        parsed = parser.parse_args(args)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (1 if code else 0)
    engine = docker or Docker()
    if ssh is not None:
        engine.ssh_client = ssh
    if connect is not None:
        parsed.connect = connect
    return parsed.run(parsed, catalog, json_mode, client, parser, engine)


def _parser(catalog: Catalog, json_mode: bool) -> argparse.ArgumentParser:
    """Parent and subparsers share flags. The mode itself is read from argv, because a subparser default would clear it."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help=catalog.format("help.json"))
    common.add_argument("--lang", choices=("en", "vi"), help=catalog.format("help.lang"))

    class BoundParser(_Parser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, catalog=catalog, json_mode=json_mode, **kwargs)

    parser = BoundParser(
        prog="superstep",
        parents=[common],
        description=catalog.format("help.main"),
        epilog=catalog.format("example.main"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True, parser_class=BoundParser)

    version = commands.add_parser(
        "version",
        parents=[common],
        help=catalog.format("help.version"),
        description=catalog.format("help.version"),
        epilog=catalog.format("example.version"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    version.add_argument("--url", help=catalog.format("help.url"))
    version.set_defaults(run=_cmd_version)

    completion = commands.add_parser(
        "completion",
        parents=[common],
        help=catalog.format("help.completion"),
        description=catalog.format("help.completion"),
        epilog=catalog.format("example.completion"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    completion.add_argument("shell", choices=("bash", "zsh", "fish"), help=catalog.format("help.shell"))
    completion.set_defaults(run=_cmd_completion)
    add_commands(commands, common, catalog)
    add_status_commands(commands, common, catalog)
    add_backup_commands(commands, common, catalog)
    add_upgrade_commands(commands, common, catalog)
    add_admin_commands(commands, common, catalog)
    add_deploy_commands(commands, common, catalog)
    add_login_commands(commands, common, catalog)
    add_workflow_commands(commands, common, catalog)
    add_run_commands(commands, common, catalog)
    add_suite_commands(commands, common, catalog)
    return parser


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, catalog: Catalog, json_mode: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog = catalog
        self.json_mode = json_mode

    def print_help(self, file=None):
        super().print_help(file or sys.stderr)

    def error(self, message: str):
        text = self.catalog.format("error.usage", message=message)
        if self.json_mode:
            _write_json({"ok": False, "error": {"code": "USAGE", "message": text}})
            self.exit(2)
        self.exit(2, text + "\n")


def _cmd_version(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    cli_version = superstep.__version__
    server = None
    warning = None
    if args.url:
        try:
            server, warning_key, extra = _fetch_version(args.url, client, cli_version)
        except CliError as exc:
            return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
        if warning_key:
            warning = catalog.format(warning_key, **extra)
    if json_mode:
        _write_json({"ok": True, "cli_version": cli_version, "server_version": server, "warning": warning})
        return 0
    lines = [catalog.format("version.cli", version=cli_version)]
    if server is not None:
        lines.append(catalog.format("version.server", version=server))
    if warning:
        lines.append(warning)
    sys.stderr.write("\n".join(lines) + "\n")
    return 0


def _cmd_completion(args, catalog: Catalog, json_mode: bool, _client, parser: argparse.ArgumentParser, _docker) -> int:
    # The script is the command's output, so it stays on stdout. `source <(superstep completion bash)` reads stdout.
    script = _completion(args.shell, _commands(parser), _flags(parser))
    if json_mode:
        _write_json({"ok": True, "shell": args.shell, "script": script})
    else:
        sys.stdout.write(script)
        if not script.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def _fetch_version(url: str, client: Optional[httpx.Client], cli_version: str):
    health = _health_url(url)
    owned = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    try:
        try:
            response = http.get(health, headers={"Accept": "application/json", "User-Agent": f"superstep-cli/{cli_version}"})
        except httpx.HTTPError:
            raise CliError("CONNECTION_FAILED", "error.connection", url=url)
    finally:
        if owned:
            http.close()
    if response.status_code != 200:
        raise CliError("BAD_RESPONSE", "error.bad_response", url=url)
    try:
        body = response.json()
    except ValueError:
        raise CliError("BAD_RESPONSE", "error.bad_response", url=url)
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict) or body.get("success") is not True:
        raise CliError("BAD_RESPONSE", "error.bad_response", url=url)
    raw = data.get("version")
    if raw is None or str(raw).strip() == "":
        return None, "version.warning_missing", {}
    server = str(raw).strip()
    if _minor(server) is None or _minor(server) != _minor(cli_version):
        return server, "version.warning_mismatch", {"cli": cli_version, "server": server}
    return server, None, {}


def _health_url(url: str) -> str:
    parts = urlparse(url)
    path = parts.path.rstrip("/")
    if path.endswith("/api/health"):
        return url
    return url.rstrip("/") + "/api/health"


def _minor(value: str) -> Optional[tuple[int, int]]:
    parts = value.split(".")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    message = catalog.format(key, **fmt)
    if json_mode:
        _write_json({"ok": False, "error": {"code": code, "message": message}})
    else:
        sys.stderr.write(message + "\n")
    return 1


def _write_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")


def _write_err(text: str) -> None:
    sys.stderr.write(text)


def _commands(parser: argparse.ArgumentParser) -> list[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices)
    return []


def _flags(parser: argparse.ArgumentParser) -> list[str]:
    found: list[str] = []
    for action in parser._actions:
        for option in action.option_strings:
            if option not in found:
                found.append(option)
    return found


def _completion(shell: str, commands: list[str], flags: list[str]) -> str:
    words = commands + flags
    rendered = " ".join(words)
    writers: dict[str, Callable[[], str]] = {
        "bash": lambda: (
            "_superstep_complete() {\n"
            f"  COMPREPLY=($(compgen -W \"{rendered}\" -- \"${{COMP_WORDS[COMP_CWORD]}}\"))\n"
            "}\n"
            "complete -F _superstep_complete superstep\n"
        ),
        "zsh": lambda: f"#compdef superstep\ncompadd {rendered}\n",
        "fish": lambda: f"complete -c superstep -a \"{' '.join(commands)}\"\n" + "".join(
            f"complete -c superstep -l {flag[2:]}\n" for flag in flags if flag.startswith("--")
        ),
    }
    return writers[shell]()
