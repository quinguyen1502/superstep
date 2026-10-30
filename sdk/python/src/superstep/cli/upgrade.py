"""`upgrade`. Backs up, moves to a pinned version, and restores that backup on a failed health check."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import superstep
from superstep.cli.backup import BackupError, _newer, _parts, create_backup, restore_archive
from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import InstallError, _compose, _image_list, _load, _write_private

# One row. A later release appends another row; it does not add a second code path.
_GATES = (
    {
        "project": "langgraph-studio",
        "volumes": frozenset({
            "langgraph-studio_pgdata",
            "langgraph-studio_redisdata",
            "langgraph-studio_apidata",
            "_redisdata",
            "_apidata",
        }),
    },
)


class UpgradeError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def add_commands(commands, common, catalog: Catalog) -> None:
    upgrade = _parser(commands, common, catalog, "upgrade", "help.upgrade", "example.upgrade")
    upgrade.add_argument("--to", help=catalog.format("help.to_version"))
    upgrade.add_argument("--images", help=catalog.format("help.images"))
    upgrade.add_argument("--check", action="store_true", help=catalog.format("help.check"))
    upgrade.add_argument("--name", help=catalog.format("help.name"))
    upgrade.add_argument("--dir", help=catalog.format("help.dir"))
    upgrade.set_defaults(run=cmd_upgrade)


def cmd_upgrade(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        target = args.to or superstep.__version__
        current = str(record.get("version") or "")
        shown = _shown(catalog, current, target)
        if args.check:
            payload = {"ok": True, "current": current, "target": target, "differs": _cmp(target, current) != 0, "changelog": shown}
            if json_mode:
                _write_json(payload)
            else:
                _write_err(catalog.format("upgrade.check", current=current, target=target) + "\n")
                if shown:
                    _write_err(shown + "\n")
            return 0
        if _cmp(target, current) < 0:
            raise UpgradeError("DOWNGRADE", "error.downgrade", target=target, current=current)
        if _cmp(target, current) == 0:
            payload = {"ok": True, "version": current, "archive": "", "name": record["name"], "changelog": shown}
            if json_mode:
                _write_json(payload)
            else:
                _write_err(catalog.format("upgrade.current", version=current) + "\n")
            return 0
        if not json_mode and shown:
            _write_err(shown + "\n")
        archive = upgrade_instance(directory, record, docker, target, args.images)
        payload = {"ok": True, "version": target, "archive": str(archive), "name": record["name"], "changelog": shown}
    except UpgradeError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except BackupError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    if json_mode:
        _write_json(payload)
    else:
        _write_err(catalog.format("upgrade.done", version=target, archive=str(archive)) + "\n")
    return 0


def upgrade_instance(directory: Path, record: dict, docker: Docker, target: str, images: Optional[str] = None) -> Path:
    """Back up, then move the instance to `target`. A failed health check restores this backup."""
    current = str(record.get("version") or "")
    if _cmp(target, current) < 0:
        raise UpgradeError("DOWNGRADE", "error.downgrade", target=target, current=current)
    archive = create_backup(directory, record, docker, directory)
    topology = record.get("topology") or "single"
    if images:
        docker.load(images)
    else:
        for image in _image_list(topology, bool(record.get("sandbox")), target):
            docker.pull(image)
    try:
        _restart(directory, record, docker, target)
        url = record.get("public_url") or ""
        if not _healthy(docker, url):
            raise UpgradeError("UNHEALTHY", "error.health", url=url)
    except UpgradeError as exc:
        if exc.code != "UNHEALTHY":
            raise
        log_path = _rollback(directory, record, docker, archive)
        raise UpgradeError("ROLLED_BACK", "error.rolled_back", log=str(log_path)) from exc
    except (DockerError, BackupError):
        log_path = _rollback(directory, record, docker, archive)
        raise UpgradeError("ROLLED_BACK", "error.rolled_back", log=str(log_path))
    record["version"] = target
    _write_private(directory / "instance.json", _dump_record(record))
    return archive


def _restart(directory: Path, record: dict, docker: Docker, target: str) -> None:
    compose_path = directory / "compose.yml"
    current = compose_path.read_text(encoding="utf-8") if compose_path.is_file() else ""
    folder = str(directory)
    if _gate_matches(record, current):
        project = _compose_project(current) or record["name"]
        docker.compose(folder, project, ["down"])
    rewritten = _compose(
        record["name"],
        record.get("topology") or "single",
        bool(record.get("sandbox")),
        target,
        _host_port(current, record.get("topology") or "single"),
        record.get("volumes") or {},
        _external_names(record, current),
    )
    _write_private(compose_path, rewritten)
    docker.compose(folder, record["name"], ["up", "-d"])


def _rollback(directory: Path, record: dict, docker: Docker, archive: Path) -> Path:
    log_path = _write_failure_log(directory, docker, record)
    try:
        restore_archive(directory, record, docker, archive)
    except (BackupError, DockerError, OSError):
        pass
    try:
        docker.compose(str(directory), record["name"], ["up", "-d"])
    except DockerError:
        pass
    return log_path


def _healthy(docker: Docker, url: str) -> bool:
    """Same wait as install, then `data.ok`. A timeout or `ok` other than true is a failure.

    `SUPERSTEP_UPGRADE_HEALTH_FAIL=1` is the smoke-test hook. It is not an operator flag.
    """
    if os.environ.get("SUPERSTEP_UPGRADE_HEALTH_FAIL") == "1":
        return False
    if not url:
        return False
    if not docker.wait_healthy(url):
        return False
    try:
        data = docker.health(url)
    except (DockerError, OSError, AttributeError):
        return False
    return isinstance(data, dict) and data.get("ok") is True


def _write_failure_log(directory: Path, docker: Docker, record: dict) -> Path:
    try:
        body = docker.compose_logs(str(directory), str(record.get("name") or ""))
    except (DockerError, OSError, AttributeError):
        body = ""
    if not body.endswith("\n"):
        body += "\n"
    path = directory / f"upgrade-failed-{_stamp()}.log"
    _write_private(path, body)
    return path


def _shown(catalog: Catalog, current: str, target: str) -> str:
    notes = _changelog_between(current, target)
    if notes:
        return notes
    if _cmp(target, current) > 0:
        return catalog.format("upgrade.changelog_missing")
    return ""


def _changelog_between(current: str, target: str) -> str:
    sections = []
    heading = ""
    body: list[str] = []
    for line in _changelog_text().splitlines():
        if line.startswith("## "):
            if heading:
                sections.append((heading, "\n".join(body).strip()))
            heading = line[3:].strip()
            body = [line]
            continue
        if heading:
            body.append(line)
    if heading:
        sections.append((heading, "\n".join(body).strip()))
    chosen = []
    for heading, text in sections:
        version = _heading_version(heading)
        if version and _cmp(version, current) > 0 and _cmp(version, target) <= 0:
            chosen.append(text)
    return "\n\n".join(chosen).strip()


def _changelog_text() -> str:
    bundled = Path(__file__).resolve().parent / "CHANGELOG.md"
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "CHANGELOG.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def _heading_version(heading: str) -> str:
    token = heading.lstrip("v").split()[0].strip("[]")
    if token and token[0].isdigit():
        return token
    return ""


def _gate_matches(record: dict, compose_text: str) -> bool:
    project = _compose_project(compose_text)
    values = {str(value) for value in (record.get("volumes") or {}).values()}
    for gate in _GATES:
        if project == gate["project"] or values & gate["volumes"]:
            return True
    return False


def _external_names(record: dict, compose_text: str) -> set:
    if not _gate_matches(record, compose_text):
        return set()
    values = {str(value) for value in (record.get("volumes") or {}).values()}
    named = set()
    for gate in _GATES:
        named |= values & gate["volumes"]
    if named:
        return named
    return values


def _compose_project(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _host_port(text: str, topology: str) -> int:
    match = re.search(r'ports:\s*\["(\d+):', text)
    if match:
        return int(match.group(1))
    return 8080 if topology == "full" else 8000


def _cmp(left: str, right: str) -> int:
    """Positive when left is newer. Pads missing numeric parts with zero, same as backup."""
    if _newer(left, right):
        return 1
    if _newer(right, left):
        return -1
    width = max(len(_parts(left)), len(_parts(right)))
    if width == 0 and left != right:
        return -1 if left < right else 1
    return 0


def _dump_record(record: dict) -> str:
    import json
    return json.dumps(record, indent=2) + "\n"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
