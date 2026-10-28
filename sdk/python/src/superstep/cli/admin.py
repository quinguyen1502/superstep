"""`admin` and `uninstall` for one instance."""
from __future__ import annotations

import shutil

from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import InstallError, _load


class AdminError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def add_commands(commands, common, catalog: Catalog) -> None:
    from superstep.cli import _Parser

    admin = _parser(commands, common, catalog, "admin", "help.admin", "example.admin")

    class _Sub(_Parser):
        def __init__(self, *args, **kwargs):
            kwargs["catalog"] = admin.catalog
            kwargs["json_mode"] = admin.json_mode
            super().__init__(*args, **kwargs)

    subs = admin.add_subparsers(dest="admin_command", required=True, parser_class=_Sub)
    create = _sub(subs, common, catalog, "create", "help.admin_create", "example.admin")
    reset = _sub(subs, common, catalog, "reset-password", "help.admin_reset", "example.admin_reset")
    listing = _sub(subs, common, catalog, "list", "help.admin_list", "example.admin_list")
    for command in (create, reset):
        command.add_argument("--email", required=True, help=catalog.format("help.account_email"))
        command.add_argument("--password", help=catalog.format("help.admin_password"))
    for command in (create, reset, listing):
        command.add_argument("--name", help=catalog.format("help.name"))
        command.add_argument("--dir", help=catalog.format("help.dir"))
        command.set_defaults(run=cmd_admin)

    uninstall = _parser(commands, common, catalog, "uninstall", "help.uninstall", "example.uninstall")
    uninstall.add_argument("--purge", action="store_true", help=catalog.format("help.purge"))
    uninstall.add_argument("--yes", action="store_true", help=catalog.format("help.confirm_yes"))
    uninstall.add_argument("--name", help=catalog.format("help.name"))
    uninstall.add_argument("--dir", help=catalog.format("help.dir"))
    uninstall.set_defaults(run=cmd_uninstall)


def cmd_admin(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        service = "api" if record.get("topology") == "full" else "superstep"
        command = ["python", "-m", "app.admin_cmd", args.admin_command]
        if args.admin_command != "list":
            command.extend(["--email", args.email])
            if args.password:
                command.extend(["--password", args.password])
        raw = docker.exec_bytes(str(directory), str(record["name"]), service, command)
        if args.admin_command == "list":
            rows = _rows(raw)
            payload = {"ok": True, "name": record["name"], "admins": rows}
            if json_mode:
                _write_json(payload)
            else:
                for row in rows:
                    _write_err(catalog.format("admin.row", email=row["email"], role=row["role"]) + "\n")
            return 0
        password = _one_line(raw)
        payload = {"ok": True, "name": record["name"], "email": args.email, "password": password}
    except AdminError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    if json_mode:
        _write_json(payload)
    else:
        key = "admin.created" if args.admin_command == "create" else "admin.reset"
        _write_err(catalog.format(key, email=args.email, password=_brace(password)) + "\n")
    return 0


def cmd_uninstall(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        if args.purge:
            _confirm(args, catalog, record)
            docker.compose(str(directory), str(record["name"]), ["down", "-v"])
            for name in (record.get("volumes") or {}).values():
                if name:
                    docker.remove_volume(str(name))
            shutil.rmtree(directory)
            payload = {"ok": True, "name": record["name"], "purged": True}
            message = catalog.format("uninstall.purged", name=record["name"])
        else:
            docker.compose(str(directory), str(record["name"]), ["down"])
            payload = {"ok": True, "name": record["name"], "purged": False}
            message = catalog.format("uninstall.kept", name=record["name"])
    except AdminError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    if json_mode:
        _write_json(payload)
    else:
        _write_err(message + "\n")
    return 0


def _confirm(args, catalog: Catalog, record: dict) -> None:
    expected = str(record.get("name") or "")
    if args.yes:
        if args.name != expected:
            raise AdminError("CONFIRM", "error.uninstall_name")
        return
    _write_err(catalog.format("prompt.uninstall", name=expected) + " ")
    try:
        typed = input("")
    except EOFError:
        typed = ""
    if typed.strip() != expected:
        raise AdminError("CONFIRM", "error.uninstall_name")


def _rows(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8", "replace")
    if "pbkdf2" in text:
        raise AdminError("OUTPUT", "error.admin_output")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        email, sep, role = line.partition("\t")
        if not sep or not email or not role.strip():
            raise AdminError("OUTPUT", "error.admin_output")
        rows.append({"email": email, "role": role.strip()})
    return rows


def _one_line(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace").strip()
    if not text or "\n" in text or "pbkdf2" in text:
        raise AdminError("OUTPUT", "error.admin_output")
    return text


def _brace(value: str) -> str:
    return value.replace("{", "{{").replace("}", "}}")


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


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    from superstep.cli.install import _parser as parser
    return parser(commands, common, catalog, name, help_key, example_key)


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _write_json(payload: dict) -> None:
    from superstep.cli import _write_json as write
    write(payload)


def _write_err(text: str) -> None:
    from superstep.cli import _write_err as write
    write(text)
