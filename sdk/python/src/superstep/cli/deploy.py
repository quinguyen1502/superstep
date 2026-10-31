"""`deploy ssh://user@host`. Files are written on the remote host, then Docker uses DOCKER_HOST."""
from __future__ import annotations

import json
import os
import secrets
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import superstep
from superstep.cli.backup import BackupError, _CRON, _shell, schedule_units
from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import (
    InstallError,
    _answers,
    add_storage_flags,
    storage_env,
    _compose,
    _image_list,
    _password,
    _port,
    _record,
    _remember,
    _write_private,
)
from superstep.cli.ssh import Ssh, SshError
from superstep.cli.upgrade import UpgradeError, _cmp, upgrade_instance


class DeployError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def add_commands(commands, common, catalog: Catalog) -> None:
    deploy = _parser(commands, common, catalog, "deploy", "help.deploy", "example.deploy")
    deploy.add_argument("target", help=catalog.format("help.deploy_target"))
    deploy.add_argument("--upgrade", action="store_true", help=catalog.format("help.force_upgrade"))
    deploy.add_argument("--yes", action="store_true", help=catalog.format("help.yes"))
    deploy.add_argument("--answers", help=catalog.format("help.answers"))
    deploy.add_argument("--images", help=catalog.format("help.images"))
    deploy.add_argument("--topology", choices=("single", "full"), help=catalog.format("help.topology"))
    deploy.add_argument("--sandbox", action="store_true", help=catalog.format("help.sandbox"))
    deploy.add_argument("--name", help=catalog.format("help.name"))
    deploy.add_argument("--dir", help=catalog.format("help.dir"))
    deploy.add_argument("--url", help=catalog.format("help.url"))
    deploy.add_argument("--admin-email", help=catalog.format("help.admin_email"))
    deploy.add_argument("--port", type=int, help=catalog.format("help.port"))
    deploy.add_argument("--schedule", choices=("daily", "weekly"), help=catalog.format("help.schedule"))
    deploy.add_argument("--keep", type=int, help=catalog.format("help.keep"))
    add_storage_flags(deploy, catalog)
    deploy.set_defaults(run=cmd_deploy)


def cmd_deploy(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        payload = deploy_instance(args, catalog, docker)
    except DeployError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except UpgradeError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except BackupError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except SshError as exc:
        return _fail(json_mode, catalog, "SSH", "error.ssh", message=_brace(exc.message))
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=_brace(exc.message))
    action = payload.pop("action")
    if json_mode:
        _write_json(payload)
    else:
        _human(catalog, action, payload)
    return 0


def deploy_instance(args, catalog: Catalog, docker: Docker) -> dict:
    """Install when the remote instance is absent. Upgrade when it is present."""
    destination, port, url = _target(args.target)
    if args.schedule or args.keep is not None:
        if args.schedule not in _CRON or not isinstance(args.keep, int) or args.keep < 1:
            raise DeployError("SCHEDULE", "error.schedule")
    answers = _answers(args.answers)
    name = args.name or answers.get("name") or "superstep"
    docker.host = url
    ssh = _open(docker, destination, port)
    ssh.probe()
    remote = args.dir.rstrip("/") if args.dir else f"{ssh.home().rstrip('/')}/.superstep/instances/{name}"
    raw = ssh.read(f"{remote}/instance.json")
    if raw is None:
        if args.upgrade:
            raise DeployError("NO_INSTANCE", "error.no_remote")
        payload = _install(args, catalog, docker, ssh, answers, name, remote, url)
    else:
        payload = _upgrade(args, docker, ssh, remote, url, raw)
    if args.schedule:
        payload["schedule"] = args.schedule
        payload["keep"] = args.keep
        payload["timer"] = _schedule(ssh, remote, _record_from(ssh, remote), args.schedule, args.keep)
    return payload


def _install(args, catalog, docker, ssh, answers, name, remote, url) -> dict:
    topology = args.topology or answers.get("topology") or "single"
    sandbox = bool(args.sandbox or answers.get("sandbox"))
    if sandbox and topology != "full":
        raise InstallError("SANDBOX", "error.sandbox_topology")
    public = args.url or answers.get("url")
    email = args.admin_email or answers.get("admin_email")
    if not args.yes and not args.topology and "topology" not in answers:
        typed = input(catalog.format("prompt.topology") + " ").strip()
        if typed in ("single", "full"):
            topology = typed
    if not public or not email:
        if not args.yes:
            public = public or input(catalog.format("prompt.url") + " ").strip()
            email = email or input(catalog.format("prompt.email") + " ").strip()
        if not public or not email:
            raise InstallError("REQUIRED", "error.required")
    attachments = storage_env(args, answers, topology, catalog)
    if not docker.docker_ok():
        raise InstallError("DOCKER", "error.docker")
    if not docker.compose_v2():
        raise InstallError("COMPOSE", "error.compose")
    port = _port(args, answers, topology)
    version = superstep.__version__
    password = _password()
    env = {
        "JWT_SECRET": secrets.token_hex(32),
        "STUDIO_SECRET_KEY": secrets.token_hex(32),
        "STUDIO_ADMIN_EMAILS": email,
        "STUDIO_ADMIN_PASSWORD": password,
        "STUDIO_PUBLIC_URL": public,
        "STUDIO_ENV": "production",
        **attachments,
    }
    volumes = {"data": f"{name}_data"}
    if topology == "full":
        env["POSTGRES_PASSWORD"] = secrets.token_hex(32)
        volumes = {"pgdata": f"{name}_pgdata", "redisdata": f"{name}_redisdata", "apidata": f"{name}_apidata"}
    compose = _compose(name, topology, sandbox, version, port, volumes)
    record = _record(name, topology, sandbox, version, public, Path(remote), volumes)
    record["remote"] = url
    body = json.dumps(record, indent=2) + "\n"
    env_text = "".join(f"{key}={value}\n" for key, value in env.items())
    ssh.mkdir(remote, 0o700)
    ssh.write(f"{remote}/compose.yml", compose.encode("utf-8"), 0o600)
    ssh.write(f"{remote}/.env", env_text.encode("utf-8"), 0o600)
    ssh.write(f"{remote}/instance.json", body.encode("utf-8"), 0o600)
    _remember(name)
    cache = _cache()
    try:
        _write_private(cache / "compose.yml", compose)
        _write_private(cache / ".env", env_text)
        _write_private(cache / "instance.json", body)
        if args.images:
            docker.load(args.images)
        else:
            for image in _image_list(topology, sandbox, version):
                docker.pull(image)
        docker.compose(str(cache), name, ["up", "-d"])
    except DockerError as exc:
        raise InstallError("DOCKER", "error.docker_failed", message=_brace(exc.message))
    finally:
        shutil.rmtree(cache, ignore_errors=True)
    if not docker.wait_healthy(public):
        raise InstallError("UNHEALTHY", "error.health", url=public)
    return {
        "ok": True,
        "action": "install",
        "name": name,
        "dir": remote,
        "url": public,
        "remote": url,
        "admin_password": password,
        "warnings": [],
    }


def _upgrade(args, docker, ssh, remote, url, raw: bytes) -> dict:
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeployError("SSH", "error.ssh", message=_brace(str(exc)))
    if not isinstance(record, dict) or not record.get("name"):
        raise DeployError("SSH", "error.ssh", message="instance.json")
    target = superstep.__version__
    current = str(record.get("version") or "")
    if _cmp(target, current) < 0:
        raise UpgradeError("DOWNGRADE", "error.downgrade", target=target, current=current)
    _remember(str(record["name"]))
    if _cmp(target, current) == 0:
        return {
            "ok": True,
            "action": "current",
            "name": record["name"],
            "dir": remote,
            "remote": url,
            "version": current,
            "archive": "",
        }
    cache = _cache()
    archive = ""
    try:
        for filename in (".env", "compose.yml", "instance.json"):
            data = raw if filename == "instance.json" else ssh.read(f"{remote}/{filename}")
            if data:
                _write_private(cache / filename, data.decode("utf-8"))
        try:
            local = upgrade_instance(cache, record, docker, target, args.images)
        except UpgradeError as exc:
            if exc.code == "ROLLED_BACK":
                _publish(ssh, cache, remote)
            raise
        archive = _publish(ssh, cache, remote) or str(local)
    finally:
        shutil.rmtree(cache, ignore_errors=True)
    return {
        "ok": True,
        "action": "upgrade",
        "name": record["name"],
        "dir": remote,
        "remote": url,
        "version": target,
        "archive": archive,
    }


def _schedule(ssh, remote: str, record: dict, period: str, keep: int) -> str:
    folder = Path(remote)
    script = _shell(folder, folder, record, keep)
    unit, service, timer = schedule_units(folder, record, period)
    ssh.write(f"{remote}/backup.sh", script.encode("utf-8"), 0o700)
    ssh.write(f"{remote}/{unit}.service", service.encode("utf-8"), 0o600)
    ssh.write(f"{remote}/{unit}.timer", timer.encode("utf-8"), 0o600)
    found = ssh.run(["command", "-v", "systemctl"])
    if found.returncode == 0 and found.stdout.strip():
        home = ssh.home().rstrip("/")
        user = f"{home}/.config/systemd/user"
        ssh.mkdir(user, 0o700)
        ssh.write(f"{user}/{unit}.service", service.encode("utf-8"), 0o600)
        ssh.write(f"{user}/{unit}.timer", timer.encode("utf-8"), 0o600)
        reload = ssh.run(["systemctl", "--user", "daemon-reload"])
        enable = ssh.run(["systemctl", "--user", "enable", "--now", f"{unit}.timer"])
        if reload.returncode != 0 or enable.returncode != 0:
            message = (reload.stderr or enable.stderr).decode("utf-8", "replace").strip()
            raise SshError(message or "systemctl failed")
        return "systemd"
    line = f"{_CRON[period]} {shlex.quote(str(folder / 'backup.sh'))}"
    ssh.write(f"{remote}/backup.cron", f"# {unit} start\n{line}\n# {unit} end\n".encode("utf-8"), 0o600)
    _remote_cron(ssh, unit, line)
    return "cron"


def _remote_cron(ssh, unit: str, line: str) -> None:
    listed = ssh.run(["crontab", "-l"])
    current = listed.stdout.decode("utf-8", "replace") if listed.returncode == 0 else ""
    start, end = f"# {unit} start", f"# {unit} end"
    kept = []
    skip = False
    for row in current.splitlines():
        if row == start:
            skip = True
            continue
        if row == end:
            skip = False
            continue
        if not skip:
            kept.append(row)
    kept.extend([start, line, end])
    result = ssh.run(["crontab", "-"], ("\n".join(kept) + "\n").encode("utf-8"))
    if result.returncode != 0:
        raise SshError(result.stderr.decode("utf-8", "replace").strip() or "crontab failed")


def _publish(ssh, cache: Path, remote: str) -> Optional[str]:
    """Copy the instance files back. An unchanged .env is left where the first write put it."""
    archive = None
    for path in sorted(cache.iterdir()):
        if not path.is_file():
            continue
        if path.name not in {".env", "compose.yml", "instance.json", "secret.key"} and not path.name.startswith(("superstep-backup-", "upgrade-failed-")):
            continue
        data = path.read_bytes()
        if path.name == ".env":
            current = ssh.read(f"{remote}/.env")
            if current == data:
                continue
        ssh.write(f"{remote}/{path.name}", data, 0o600)
        if path.name.startswith("superstep-backup-"):
            archive = f"{remote}/{path.name}"
    return archive


def _record_from(ssh, remote: str) -> dict:
    raw = ssh.read(f"{remote}/instance.json")
    if not raw:
        raise DeployError("NO_INSTANCE", "error.no_remote")
    record = json.loads(raw.decode("utf-8"))
    if not isinstance(record, dict):
        raise DeployError("SSH", "error.ssh", message="instance.json")
    return record


def _open(docker: Docker, destination: str, port: Optional[int]):
    client = getattr(docker, "ssh_client", None)
    if client is not None:
        return client
    return Ssh(destination, port)


def _target(value: str) -> tuple[str, Optional[int], str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "ssh" or not parsed.hostname or not parsed.username or parsed.password:
        raise DeployError("SSH_TARGET", "error.ssh_target")
    return f"{parsed.username}@{parsed.hostname}", parsed.port, value.strip()


def _cache() -> Path:
    path = Path(tempfile.mkdtemp(prefix="superstep-deploy-"))
    os.chmod(path, 0o700)
    return path


def _brace(value: str) -> str:
    return value.replace("{", "{{").replace("}", "}}")


def _human(catalog: Catalog, action: str, payload: dict) -> None:
    lines = []
    if action == "install":
        lines.append(catalog.format("install.url", url=payload["url"]))
        lines.append(catalog.format("install.password", password=payload["admin_password"]))
        lines.append(catalog.format("deploy.installed", name=payload["name"], url=payload["remote"]))
    elif action == "upgrade":
        lines.append(catalog.format("upgrade.done", version=payload["version"], archive=payload.get("archive") or ""))
    else:
        lines.append(catalog.format("upgrade.current", version=payload["version"]))
    if payload.get("timer"):
        lines.append(catalog.format(f"schedule.{payload['timer']}", period=payload["schedule"], keep=str(payload["keep"])))
    _write_err("\n".join(lines) + "\n")


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
