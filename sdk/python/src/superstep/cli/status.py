"""`status`, `config`, and `doctor` for an instance directory from install."""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import InstallError, _load, _write_private

_RESTART = {"JWT_SECRET", "STUDIO_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "STUDIO_ENV", "STUDIO_TRUSTED_PROXIES"}
_SECRET_PARTS = ("SECRET", "PASSWORD", "TOKEN", "KEY")
_PLACEHOLDER = "dev-secret-change-me"


def add_commands(commands, common, catalog: Catalog) -> None:
    status = _parser(commands, common, catalog, "status", "help.status", "example.status")
    status.add_argument("--name", help=catalog.format("help.name"))
    status.add_argument("--dir", help=catalog.format("help.dir"))
    status.set_defaults(run=cmd_status)

    config = _parser(commands, common, catalog, "config", "help.config", "example.config")
    config.add_argument("action", choices=("get", "set", "list"))
    config.add_argument("key", nargs="?")
    config.add_argument("value", nargs="?")
    config.add_argument("--show-secrets", action="store_true", help=catalog.format("help.show_secrets"))
    config.add_argument("--name", help=catalog.format("help.name"))
    config.add_argument("--dir", help=catalog.format("help.dir"))
    config.set_defaults(run=cmd_config)

    doctor = _parser(commands, common, catalog, "doctor", "help.doctor", "example.doctor")
    doctor.add_argument("--name", help=catalog.format("help.name"))
    doctor.add_argument("--dir", help=catalog.format("help.dir"))
    doctor.set_defaults(run=cmd_doctor)


def cmd_status(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        health = docker.health(record.get("public_url") or "")
        services = docker.ps(str(directory), record["name"])
        volumes = [{"name": name, "bytes": docker.volume_bytes(name)} for name in (record.get("volumes") or {}).values()]
        release = docker.registry_version() or _bundled_release(str(record.get("version") or "")) or "unknown"
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    payload = {
        "ok": True,
        "version": health.get("version") or record.get("version"),
        "services": services,
        "database": health.get("database"),
        "run_bus": health.get("run_bus"),
        "volumes": volumes,
        "release": release,
    }
    _show(json_mode, payload)
    if not json_mode:
        from superstep.cli import _write_err
        _write_err(f"{payload['version']} {payload['database']} {payload['run_bus']} {payload['release']}\n")
    return 0


def cmd_config(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        env_path = directory / ".env"
        values = _read_env(env_path)
        if args.action == "list":
            settings = [{"key": key, "value": _mask(key, value, args.show_secrets)} for key, value in values.items()]
            _show(json_mode, {"ok": True, "settings": settings})
            if not json_mode:
                from superstep.cli import _write_err
                _write_err("".join(f"{item['key']}={item['value']}\n" for item in settings))
            return 0
        if not args.key or (args.action == "set" and args.value is None):
            return _fail(json_mode, catalog, "USAGE", "error.config_args")
        if args.action == "get":
            if args.key not in values:
                return _fail(json_mode, catalog, "MISSING", "error.config_missing", setting=args.key)
            shown = _mask(args.key, values[args.key], args.show_secrets)
            _show(json_mode, {"ok": True, "key": args.key, "value": shown})
            if not json_mode:
                from superstep.cli import _write_err
                _write_err(shown + "\n")
            return 0
        values[args.key] = args.value
        _write_private(env_path, "".join(f"{key}={value}\n" for key, value in values.items()))
        restarted = args.key in _RESTART
        if restarted:
            docker.compose(str(directory), record["name"], ["restart"])
        message = catalog.format("config.restarted" if restarted else "config.kept", setting=args.key)
        _show(json_mode, {"ok": True, "key": args.key, "restarted": restarted, "message": message})
        if not json_mode:
            from superstep.cli import _write_err
            _write_err(message + "\n")
        return 0
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)


def cmd_doctor(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    env = _read_env(directory / ".env")
    compose = (directory / "compose.yml").read_text(encoding="utf-8") if (directory / "compose.yml").is_file() else ""
    findings = []
    notes = []
    jwt = env.get("JWT_SECRET", "")
    if jwt == "" or jwt == _PLACEHOLDER:
        findings.append(catalog.format("doctor.jwt"))
    secret = env.get("STUDIO_SECRET_KEY", "")
    backed = (directory / "secret.key").is_file() or bool(record.get("secret_backed_up"))
    if secret == "" and not backed:
        findings.append(catalog.format("doctor.secret_key"))
    if env.get("STUDIO_ENV") != "production":
        findings.append(catalog.format("doctor.env"))
    url = record.get("public_url") or env.get("STUDIO_PUBLIC_URL") or ""
    if url and not _https_or_local(url):
        findings.append(catalog.format("doctor.url"))
    if record.get("topology") == "full" and not env.get("STUDIO_TRUSTED_PROXIES"):
        findings.append(catalog.format("doctor.proxies"))
    if record.get("sandbox") and "docker.sock" not in compose:
        findings.append(catalog.format("doctor.socket"))
    service = "api" if record.get("topology") == "full" else "superstep"
    try:
        skew = docker.clock_skew_seconds(str(directory), record["name"], service)
    except DockerError:
        skew = 0.0
    if skew > 30:
        findings.append(catalog.format("doctor.clock", seconds=str(int(skew))))
    provider = _provider_url(env)
    if provider:
        result = docker.probe(provider)
        if result == "offline":
            notes.append(catalog.format("doctor.offline"))
        elif result == "unreachable":
            findings.append(catalog.format("doctor.provider", url=provider))
    storage = _attachment_storage(catalog, docker, env, url, findings, notes)
    payload = {"ok": not findings, "findings": findings, "notes": notes, "attachment_storage": storage}
    _show(json_mode, payload)
    if not json_mode:
        from superstep.cli import _write_err
        text = "\n".join(findings + notes)
        if text:
            _write_err(text + "\n")
    return 1 if findings else 0


def _attachment_storage(catalog: Catalog, docker: Docker, env: dict, url: str, findings: list, notes: list) -> dict:
    """The attachment backend and whether its probe passes (TASK-0195). Only /api/health's short reason is shown,
    never a bucket key or endpoint secret."""
    backend = (env.get("STUDIO_ATTACHMENT_STORAGE") or "db").strip() or "db"
    out = {"backend": backend, "ok": None}
    health = docker.health(url) if url else {}
    if "attachment_storage_ok" in health:
        out["ok"] = bool(health["attachment_storage_ok"])
        backend = str(health.get("attachment_storage") or backend)
        out["backend"] = backend
        if out["ok"]:
            notes.append(catalog.format("doctor.attachments_ok", backend=backend))
        else:
            reason = str(health.get("attachment_storage_reason") or "")
            out["reason"] = reason
            findings.append(catalog.format("doctor.attachments_failing", backend=backend, reason=reason))
        seen = health.get("attachment_storage_worker_seen")
        if backend == "fs" and "attachment_storage_worker_seen" in health and seen is None:
            notes.append(catalog.format("doctor.attachments_worker"))
    else:
        notes.append(catalog.format("doctor.attachments_unknown", backend=backend))
    return out


def _provider_url(env: dict) -> str:
    if not env.get("OPENAI_API_KEY"):
        return ""
    return env.get("OPENAI_BASE_URL") or "https://api.openai.com"


def _https_or_local(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return True
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1"}


def _mask(key: str, value: str, show: bool) -> str:
    if show:
        return value
    upper = key.upper()
    if any(part in upper for part in _SECRET_PARTS):
        return "***"
    return value


def _read_env(path: Path) -> dict:
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _bundled_release(current: str) -> str:
    path = Path(__file__).resolve().parent / "CHANGELOG.md"
    if not path.is_file():
        return ""
    newest = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            token = line[3:].strip().lstrip("v").split()[0].strip("[]")
            if token and token[0].isdigit():
                newest = token
    if newest and newest != current:
        return newest
    return ""


def _show(json_mode: bool, payload: dict) -> None:
    from superstep.cli import _write_json
    if json_mode:
        _write_json(payload)


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    return commands.add_parser(
        name,
        parents=[common],
        help=catalog.format(help_key),
        description=catalog.format(help_key),
        epilog=catalog.format(example_key),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
