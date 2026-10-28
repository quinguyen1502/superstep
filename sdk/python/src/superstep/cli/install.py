"""`install`, `adopt`, and the compose wrappers around one instance directory."""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import superstep
from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog

_GIB = 1024 ** 3
APP = "ghcr.io/quinguyen1502/superstep"
API = "ghcr.io/quinguyen1502/superstep-api"
WEB = "ghcr.io/quinguyen1502/superstep-web"
SANDBOX = "ghcr.io/quinguyen1502/superstep-sandbox"


class InstallError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def add_commands(commands, common, catalog: Catalog) -> None:
    install = _parser(commands, common, catalog, "install", "help.install", "example.install")
    install.add_argument("--yes", action="store_true", help=catalog.format("help.yes"))
    install.add_argument("--answers", help=catalog.format("help.answers"))
    install.add_argument("--name", help=catalog.format("help.name"))
    install.add_argument("--dir", help=catalog.format("help.dir"))
    install.add_argument("--url", help=catalog.format("help.url"))
    install.add_argument("--admin-email", help=catalog.format("help.admin_email"))
    install.add_argument("--port", type=int, help=catalog.format("help.port"))
    install.add_argument("--images", help=catalog.format("help.images"))
    install.add_argument("--topology", choices=("single", "full"), help=catalog.format("help.topology"))
    install.add_argument("--sandbox", action="store_true", help=catalog.format("help.sandbox"))
    install.add_argument("--adopt", metavar="DIR", help=catalog.format("help.adopt_flag"))
    install.set_defaults(run=cmd_install)

    adopt = _parser(commands, common, catalog, "adopt", "help.adopt", "example.adopt")
    adopt.add_argument("directory")
    adopt.add_argument("--name", help=catalog.format("help.name"))
    adopt.add_argument("--url", help=catalog.format("help.url"))
    adopt.add_argument("--topology", choices=("single", "full"), help=catalog.format("help.topology"))
    adopt.set_defaults(run=cmd_adopt)

    for name, key, example in (
        ("start", "help.start", "example.start"),
        ("stop", "help.stop", "example.stop"),
        ("restart", "help.restart", "example.restart"),
    ):
        command = _parser(commands, common, catalog, name, key, example)
        command.add_argument("--name", help=catalog.format("help.name"))
        command.add_argument("--dir", help=catalog.format("help.dir"))
        command.set_defaults(run={"start": cmd_start, "stop": cmd_stop, "restart": cmd_restart}[name])

    logs = _parser(commands, common, catalog, "logs", "help.logs", "example.logs")
    logs.add_argument("service", nargs="?", help=catalog.format("help.service"))
    logs.add_argument("--follow", action="store_true", help=catalog.format("help.follow"))
    logs.add_argument("--name", help=catalog.format("help.name"))
    logs.add_argument("--dir", help=catalog.format("help.dir"))
    logs.set_defaults(run=cmd_logs)


def cmd_install(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    if args.adopt:
        args.directory = args.adopt
        return cmd_adopt(args, catalog, json_mode, _client, _parser, docker)
    try:
        payload, warnings = _install(args, catalog, docker)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    _emit(json_mode, catalog, payload, warnings)
    return 0


def cmd_adopt(args, catalog, json_mode, _client, _parser, _docker: Docker) -> int:
    try:
        payload = _adopt(args)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    _emit(json_mode, catalog, payload, [])
    return 0


def cmd_start(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    return _lifecycle(args, catalog, json_mode, docker, ["up", "-d"], wait=True)


def cmd_stop(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    return _lifecycle(args, catalog, json_mode, docker, ["stop"], wait=False)


def cmd_restart(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    return _lifecycle(args, catalog, json_mode, docker, ["restart"], wait=True)


def cmd_logs(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    compose_args = ["logs"]
    if args.service:
        compose_args.append(args.service)
    if args.follow:
        compose_args.append("-f")
    return _lifecycle(args, catalog, json_mode, docker, compose_args, wait=False)


def _install(args, catalog: Catalog, docker: Docker):
    answers = _answers(args.answers)
    topology = args.topology or answers.get("topology") or "single"
    sandbox = bool(args.sandbox or answers.get("sandbox"))
    if sandbox and topology != "full":
        raise InstallError("SANDBOX", "error.sandbox_topology")
    name = args.name or answers.get("name") or "superstep"
    url = args.url or answers.get("url")
    email = args.admin_email or answers.get("admin_email")
    if not args.yes and not args.topology and "topology" not in answers:
        typed = input(catalog.format("prompt.topology") + " ").strip()
        if typed in ("single", "full"):
            topology = typed
    if not url or not email:
        if not args.yes:
            url = url or input(catalog.format("prompt.url") + " ").strip()
            email = email or input(catalog.format("prompt.email") + " ").strip()
        if not url or not email:
            raise InstallError("REQUIRED", "error.required")
    if not docker.docker_ok():
        raise InstallError("DOCKER", "error.docker")
    if not docker.compose_v2():
        raise InstallError("COMPOSE", "error.compose")
    port = _port(args, answers, topology)
    owner = docker.port_owner(port)
    if owner and args.port is None and answers.get("port") is None:
        if args.yes:
            raise InstallError("PORT_BUSY", "error.port", port=str(port), process=owner)
        port = _ask_port(catalog, docker, port, owner)
    elif owner:
        raise InstallError("PORT_BUSY", "error.port", port=str(port), process=owner)
    directory = _instance_dir(name, args.dir)
    if (directory / "instance.json").is_file():
        raise InstallError("INSTALLED", "error.installed")
    warnings = _warnings(catalog, docker, directory)
    version = superstep.__version__
    password = _password()
    jwt = secrets.token_hex(32)
    secret_key = secrets.token_hex(32)
    env = {
        "JWT_SECRET": jwt,
        "STUDIO_SECRET_KEY": secret_key,
        "STUDIO_ADMIN_EMAILS": email,
        "STUDIO_ADMIN_PASSWORD": password,
        "STUDIO_PUBLIC_URL": url,
        "STUDIO_ENV": "production",
    }
    volumes = {"data": f"{name}_data"}
    if topology == "full":
        env["POSTGRES_PASSWORD"] = secrets.token_hex(32)
        volumes = {"pgdata": f"{name}_pgdata", "redisdata": f"{name}_redisdata", "apidata": f"{name}_apidata"}
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    compose = _compose(name, topology, sandbox, version, port, volumes)
    _write_private(directory / "compose.yml", compose)
    _write_private(directory / ".env", "".join(f"{key}={value}\n" for key, value in env.items()))
    record = _record(name, topology, sandbox, version, url, directory, volumes)
    _write_private(directory / "instance.json", json.dumps(record, indent=2) + "\n")
    _remember(name)
    try:
        if args.images:
            docker.load(args.images)
        else:
            for image in _image_list(topology, sandbox, version):
                docker.pull(image)
        docker.compose(str(directory), name, ["up", "-d"])
    except DockerError as exc:
        raise InstallError("DOCKER", "error.docker_failed", message=exc.message)
    if not docker.wait_healthy(url):
        raise InstallError("UNHEALTHY", "error.health", url=url)
    return {"ok": True, "url": url, "admin_password": password, "name": name, "dir": str(directory), "warnings": warnings}, warnings


def _adopt(args) -> dict:
    directory = Path(args.directory)
    if not directory.is_dir():
        raise InstallError("NO_INSTANCE", "error.no_instance")
    name = args.name or directory.name or "superstep"
    topology = args.topology or "single"
    url = args.url or ""
    record = _record(name, topology, False, superstep.__version__, url, directory, {})
    _write_private(directory / "instance.json", json.dumps(record, indent=2) + "\n")
    _remember(name)
    return {"ok": True, "name": name, "dir": str(directory), "url": url}


def _lifecycle(args, catalog, json_mode, docker: Docker, compose_args: list[str], wait: bool) -> int:
    try:
        directory, record = _load(args)
        docker.compose(str(directory), record["name"], compose_args)
        url = record.get("public_url") or ""
        if wait and url and not docker.wait_healthy(url):
            raise InstallError("UNHEALTHY", "error.health", url=url)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    payload = {"ok": True, "url": record.get("public_url") or ""}
    if wait:
        payload["announce"] = True
    _emit(json_mode, catalog, payload, [])
    return 0


def _load(args):
    name = args.name or _current_name() or "superstep"
    directory = _instance_dir(name, args.dir)
    path = directory / "instance.json"
    if not path.is_file():
        raise InstallError("NO_INSTANCE", "error.no_instance")
    return directory, json.loads(path.read_text(encoding="utf-8"))


def _port(args, answers: dict, topology: str) -> int:
    if args.port is not None:
        return args.port
    if answers.get("port") is not None:
        return int(answers["port"])
    return 8080 if topology == "full" else 8000


def _ask_port(catalog: Catalog, docker: Docker, port: int, owner: str) -> int:
    from superstep.cli import _write_err
    _write_err(catalog.format("error.port", port=str(port), process=owner) + "\n")
    typed = input(catalog.format("prompt.port") + " ").strip()
    if not typed:
        raise InstallError("PORT_BUSY", "error.port", port=str(port), process=owner)
    chosen = int(typed)
    again = docker.port_owner(chosen)
    if again:
        raise InstallError("PORT_BUSY", "error.port", port=str(chosen), process=again)
    return chosen


def _warnings(catalog: Catalog, docker: Docker, directory: Path) -> list[str]:
    warnings = []
    if docker.memory_bytes() < _GIB:
        warnings.append(catalog.format("warn.memory"))
    probe = directory.parent if directory.parent.exists() else Path.home()
    if docker.disk_free_bytes(str(probe)) < 2 * _GIB:
        warnings.append(catalog.format("warn.disk"))
    return warnings


def _instance_dir(name: str, explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    return Path.home() / ".superstep" / "instances" / name


def _record(name, topology, sandbox, version, url, directory: Path, volumes: dict) -> dict:
    return {
        "name": name,
        "topology": topology,
        "sandbox": sandbox,
        "version": version,
        "public_url": url,
        "dir": str(directory),
        "remote": None,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "volumes": volumes,
    }


def _image_list(topology: str, sandbox: bool, version: str) -> list[str]:
    if topology == "single":
        return [f"{APP}:{version}"]
    images = ["pgvector/pgvector:pg17", "redis:7-alpine", f"{API}:{version}", f"{WEB}:{version}"]
    if sandbox:
        images.append(f"{SANDBOX}:{version}")
    return images


def _named_volume(alias: str, volume_name: str, external_names: Optional[set] = None) -> str:
    text = f"  {alias}:\n    name: {volume_name}\n"
    if external_names and volume_name in external_names:
        text += "    external: true\n"
    return text


def _compose(name: str, topology: str, sandbox: bool, version: str, port: int, volumes: dict, external_names: Optional[set] = None) -> str:
    if topology == "single":
        return (
            f"name: {name}\n"
            "services:\n"
            "  superstep:\n"
            f"    image: {APP}:{version}\n"
            f"    ports: [\"{port}:8000\"]\n"
            "    environment:\n"
            "      JWT_SECRET: ${JWT_SECRET}\n"
            "      STUDIO_SECRET_KEY: ${STUDIO_SECRET_KEY}\n"
            "      STUDIO_ADMIN_EMAILS: ${STUDIO_ADMIN_EMAILS}\n"
            "      STUDIO_ADMIN_PASSWORD: ${STUDIO_ADMIN_PASSWORD}\n"
            "      STUDIO_PUBLIC_URL: ${STUDIO_PUBLIC_URL}\n"
            "      STUDIO_ENV: production\n"
            f"    volumes: [\"{volumes['data']}:/data\"]\n"
            "    restart: unless-stopped\n"
            "volumes:\n"
            + _named_volume("data", volumes["data"], external_names)
        )
    text = (
        f"name: {name}\n"
        "services:\n"
        "  postgres:\n"
        "    image: pgvector/pgvector:pg17\n"
        "    environment:\n"
        "      POSTGRES_USER: studio\n"
        "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}\n"
        "      POSTGRES_DB: studio\n"
        f"    volumes: [\"{volumes['pgdata']}:/var/lib/postgresql/data\"]\n"
        "    restart: unless-stopped\n"
        "  redis:\n"
        "    image: redis:7-alpine\n"
        "    command: [\"redis-server\", \"--appendonly\", \"yes\"]\n"
        f"    volumes: [\"{volumes['redisdata']}:/data\"]\n"
        "    restart: unless-stopped\n"
        "  api:\n"
        f"    image: {API}:{version}\n"
        "    environment:\n"
        "      DATABASE_URL: postgresql+psycopg://studio:${POSTGRES_PASSWORD}@postgres:5432/studio\n"
        "      REDIS_URL: redis://redis:6379/0\n"
        "      JWT_SECRET: ${JWT_SECRET}\n"
        "      STUDIO_SECRET_KEY: ${STUDIO_SECRET_KEY}\n"
        "      STUDIO_ADMIN_EMAILS: ${STUDIO_ADMIN_EMAILS}\n"
        "      STUDIO_ADMIN_PASSWORD: ${STUDIO_ADMIN_PASSWORD}\n"
        "      STUDIO_PUBLIC_URL: ${STUDIO_PUBLIC_URL}\n"
        "      STUDIO_ENV: production\n"
        f"    volumes: [\"{volumes['apidata']}:/data\"]\n"
        "    depends_on: [postgres, redis]\n"
        "    restart: unless-stopped\n"
        "  worker:\n"
        f"    image: {API}:{version}\n"
        "    command: [\"python\", \"-m\", \"app.worker\"]\n"
        "    environment:\n"
        "      DATABASE_URL: postgresql+psycopg://studio:${POSTGRES_PASSWORD}@postgres:5432/studio\n"
        "      REDIS_URL: redis://redis:6379/0\n"
        "      JWT_SECRET: ${JWT_SECRET}\n"
        "      STUDIO_SECRET_KEY: ${STUDIO_SECRET_KEY}\n"
        "      STUDIO_ENV: production\n"
        f"    volumes: [\"{volumes['apidata']}:/data\"]\n"
        "    depends_on: [api]\n"
        "    restart: unless-stopped\n"
        "  web:\n"
        f"    image: {WEB}:{version}\n"
        f"    ports: [\"{port}:80\"]\n"
        "    depends_on: [api]\n"
        "    restart: unless-stopped\n"
    )
    if sandbox:
        text += (
            "  sandbox:\n"
            f"    image: {SANDBOX}:{version}\n"
            "    restart: unless-stopped\n"
        )
    text += (
        "volumes:\n"
        + _named_volume("pgdata", volumes["pgdata"], external_names)
        + _named_volume("redisdata", volumes["redisdata"], external_names)
        + _named_volume("apidata", volumes["apidata"], external_names)
    )
    return text


def _answers(path: Optional[str]) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InstallError("REQUIRED", "error.required")
    return data


def _password() -> str:
    while True:
        value = secrets.token_urlsafe(12)
        if any(char.isalpha() for char in value) and any(char.isdigit() for char in value):
            return value


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(path, 0o600)


def _remember(name: str) -> None:
    path = Path.home() / ".superstep" / "cli.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    data["current"] = name
    path.write_text(json.dumps(data), encoding="utf-8")


def _current_name() -> Optional[str]:
    path = Path.home() / ".superstep" / "cli.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and isinstance(data.get("current"), str):
        return data["current"]
    return None


def _emit(json_mode: bool, catalog: Catalog, payload: dict, warnings: list[str]) -> None:
    from superstep.cli import _write_err, _write_json
    if json_mode:
        body = dict(payload)
        body.pop("announce", None)
        if "warnings" not in body:
            body["warnings"] = warnings
        _write_json(body)
        return
    lines = []
    if payload.get("url") and (payload.get("admin_password") or payload.get("announce")):
        lines.append(catalog.format("install.url", url=payload["url"]))
    if payload.get("admin_password"):
        lines.append(catalog.format("install.password", password=payload["admin_password"]))
    lines.extend(warnings)
    if lines:
        _write_err("\n".join(lines) + "\n")


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    import argparse
    return commands.add_parser(
        name,
        parents=[common],
        help=catalog.format(help_key),
        description=catalog.format(help_key),
        epilog=catalog.format(example_key),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
