"""`attachments migrate` for one instance (TASK-0194, REQ-0080, DEC-0074).

Runs `python -m app.admin_cmd attachments-migrate` in the API container, which copies each chat file to the new
backend, checks its size and SHA-256, switches the row and deletes the old copy. A stopped run is safe to start again;
a second run has nothing to do."""
from __future__ import annotations

import json

from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import InstallError, _load

BACKENDS = ("db", "fs", "s3")


def add_commands(commands, common, catalog: Catalog) -> None:
    from superstep.cli import _Parser
    from superstep.cli.admin import _parser, _sub

    group = _parser(commands, common, catalog, "attachments", "help.attachments", "example.attachments_migrate")

    class _Sub(_Parser):
        def __init__(self, *args, **kwargs):
            kwargs["catalog"] = group.catalog
            kwargs["json_mode"] = group.json_mode
            super().__init__(*args, **kwargs)

    subs = group.add_subparsers(dest="attachments_command", required=True, parser_class=_Sub)
    migrate = _sub(subs, common, catalog, "migrate", "help.attachments_migrate", "example.attachments_migrate")
    migrate.add_argument("--to", required=True, choices=BACKENDS, help=catalog.format("help.attachments_to"))
    migrate.add_argument("--dry-run", action="store_true", help=catalog.format("help.attachments_dry_run"))
    migrate.add_argument("--batch", type=int, default=100, help=catalog.format("help.attachments_batch"))
    migrate.add_argument("--name", help=catalog.format("help.name"))
    migrate.add_argument("--dir", help=catalog.format("help.dir"))
    migrate.set_defaults(run=cmd_migrate)


def cmd_migrate(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    from superstep.cli.admin import _fail, _write_err, _write_json
    try:
        directory, record = _load(args)
        service = "api" if record.get("topology") == "full" else "superstep"
        command = ["python", "-m", "app.admin_cmd", "attachments-migrate", "--to", args.to, "--batch", str(args.batch)]
        if args.dry_run:
            command.append("--dry-run")
        out = json.loads(docker.exec_bytes(str(directory), str(record["name"]), service, command).decode("utf-8"))
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        code, message = _server_error(exc.message)
        if code:
            return _fail(json_mode, catalog, code, "error.attachments_server", message=message)
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    except ValueError:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message="unexpected output")
    if json_mode:
        _write_json({"ok": not out["failed"], "name": record["name"], **out})
    else:
        if args.dry_run:
            _write_err(catalog.format("attachments.dry_run", pending=str(out["pending"]), to=args.to) + "\n")
        else:
            _write_err(catalog.format("attachments.moved", moved=str(out["moved"]), to=args.to, mb=f"{out['bytes'] / 1e6:.1f}") + "\n")
            for item in out["failed"]:
                _write_err(catalog.format("attachments.failed", id=item["id"], reason=item["reason"]) + "\n")
            if out["pending"]:
                _write_err(catalog.format("attachments.pending", pending=str(out["pending"])) + "\n")
    return 1 if out["failed"] else 0


def _server_error(text: str) -> tuple[str, str]:
    """(code, message) of an `app.admin_cmd` error line, or ("", "")."""
    for line in reversed(text.splitlines()):
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("code"):
            return str(data["code"]), str(data.get("message") or "")
    return "", ""
