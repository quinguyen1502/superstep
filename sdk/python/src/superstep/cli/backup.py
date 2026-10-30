"""`backup` and `restore`. `create_backup` and `restore_archive` are what upgrade calls."""
from __future__ import annotations

import io
import json
import os
import shlex
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import superstep
from superstep.cli.docker import Docker, DockerError
from superstep.cli.i18n import Catalog
from superstep.cli.install import InstallError, _load, _write_private
from superstep.cli.status import _read_env

_FORMAT = 1
_MEMBERS = {"manifest.json", "database.sqlite", "database.dump", "secret.key", ".env", "compose.yml"}
_CRON = {"daily": "0 3 * * *", "weekly": "0 3 * * 0"}
_SQLITE_PY = (
    "import sqlite3\n"
    "src = sqlite3.connect('/data/studio.db')\n"
    "dst = sqlite3.connect('/tmp/superstep-online.db')\n"
    "src.backup(dst)\n"
    "dst.close()\n"
    "src.close()\n"
)
_PG_DUMP = ["pg_dump", "-U", "studio", "-d", "studio", "-Fc"]
_PG_RESTORE = ["pg_restore", "-U", "studio", "-d", "studio", "--clean", "--if-exists", "/tmp/superstep-restore.dump"]


class BackupError(Exception):
    def __init__(self, code: str, key: str, **fmt: str):
        self.code = code
        self.key = key
        self.fmt = fmt


def add_commands(commands, common, catalog: Catalog) -> None:
    backup = _parser(commands, common, catalog, "backup", "help.backup", "example.backup")
    backup.add_argument("--to", help=catalog.format("help.to"))
    backup.add_argument("--schedule", choices=("daily", "weekly"), help=catalog.format("help.schedule"))
    backup.add_argument("--keep", type=int, help=catalog.format("help.keep"))
    backup.add_argument("--name", help=catalog.format("help.name"))
    backup.add_argument("--dir", help=catalog.format("help.dir"))
    backup.set_defaults(run=cmd_backup)

    restore = _parser(commands, common, catalog, "restore", "help.restore", "example.restore")
    restore.add_argument("archive", help=catalog.format("help.restore"))
    restore.add_argument("--yes", action="store_true", help=catalog.format("help.confirm_yes"))
    restore.add_argument("--name", help=catalog.format("help.name"))
    restore.add_argument("--dir", help=catalog.format("help.dir"))
    restore.set_defaults(run=cmd_restore)


def cmd_backup(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        dest = Path(args.to) if args.to else directory
        if args.schedule or args.keep is not None:
            if args.schedule not in _CRON or not isinstance(args.keep, int) or args.keep < 1:
                raise BackupError("SCHEDULE", "error.schedule")
            kind = install_schedule(directory, record, docker, dest, args.schedule, args.keep)
            payload = {"ok": True, "schedule": args.schedule, "keep": args.keep, "timer": kind, "name": record["name"]}
            if not json_mode:
                _write_err(catalog.format(f"schedule.{kind}", period=args.schedule, keep=str(args.keep)) + "\n")
                return 0
        else:
            archive = create_backup(directory, record, docker, dest)
            payload = {"ok": True, "archive": str(archive), "name": record["name"]}
            if not json_mode:
                _write_err(catalog.format("backup.wrote", archive=str(archive)) + "\n")
                return 0
    except BackupError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    _write_json(payload)
    return 0


def cmd_restore(args, catalog, json_mode, _client, _parser, docker: Docker) -> int:
    try:
        directory, record = _load(args)
        archive = Path(args.archive)
        manifest = _manifest(_read_archive(archive))
        _accept(manifest)
        _confirm(args, catalog, record)
        restore_archive(directory, record, docker, archive)
    except BackupError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except InstallError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    except DockerError as exc:
        return _fail(json_mode, catalog, "DOCKER", "error.docker_failed", message=exc.message)
    if json_mode:
        _write_json({"ok": True, "name": record["name"]})
    else:
        _write_err(catalog.format("restore.done", name=record["name"]) + "\n")
    return 0


def create_backup(directory: Path, record: dict, docker: Docker, dest: Path) -> Path:
    """Write one archive and return its path. A short disk raises before any stop or file."""
    parent = dest if dest.is_dir() else dest.parent
    if not parent.is_dir() or (dest.exists() and not dest.is_dir()):
        raise BackupError("ARCHIVE", "error.archive")
    if docker.disk_free_bytes(str(parent)) < _estimate(docker, directory, record):
        raise BackupError("DISK", "error.disk")
    member, blob = _dump(docker, str(directory), record)
    try:
        env_text = (directory / ".env").read_text(encoding="utf-8") if (directory / ".env").is_file() else ""
        compose = (directory / "compose.yml").read_text(encoding="utf-8") if (directory / "compose.yml").is_file() else ""
        secret = _secret_bytes(docker, directory, record, _read_env(directory / ".env"))
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = {
            "format": _FORMAT,
            "server_version": str(record.get("version") or ""),
            "topology": record.get("topology") or "single",
            "name": record["name"],
            "created": created,
            "database": member,
        }
        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = dest / f"superstep-backup-{record['name']}-{stamp}.tar.gz"
        _write_archive(archive, {
            "manifest.json": json.dumps(manifest).encode("utf-8"),
            member: blob,
            "secret.key": secret,
            ".env": _env_with_secret(env_text, secret).encode("utf-8"),
            "compose.yml": compose.encode("utf-8"),
        })
        record["secret_backed_up"] = True
        _write_private(directory / "instance.json", json.dumps(record, indent=2) + "\n")
        return archive
    finally:
        if isinstance(blob, Path):
            blob.unlink(missing_ok=True)


def restore_archive(directory: Path, record: dict, docker: Docker, archive: Path) -> None:
    """Replace instance data from an archive. The caller has already confirmed the name."""
    members = _read_archive(archive)
    try:
        _restore_members(directory, record, docker, members)
    finally:
        _drop_spill(members)


def _restore_members(directory: Path, record: dict, docker: Docker, members: dict) -> None:
    manifest = _manifest(members)
    _accept(manifest)
    for name in ("manifest.json", ".env", "compose.yml", "secret.key"):
        if name not in members:
            raise BackupError("ARCHIVE", "error.archive")
    db_name = manifest.get("database")
    if db_name not in members:
        raise BackupError("ARCHIVE", "error.archive")
    secret = members["secret.key"]
    _write_private(directory / ".env", _env_with_secret(members[".env"].decode("utf-8"), secret))
    _write_private(directory / "compose.yml", members["compose.yml"].decode("utf-8"))
    _write_private_bytes(directory / "secret.key", secret)
    folder = str(directory)
    project = record["name"]
    topology = manifest.get("topology") or record.get("topology") or "single"
    docker.compose(folder, project, ["stop"])
    try:
        if topology == "full":
            docker.compose(folder, project, ["up", "-d", "postgres"])
            docker.copy_to(folder, project, "postgres", "/tmp/superstep-restore.dump", members[db_name])
            docker.exec_bytes(folder, project, "postgres", _PG_RESTORE)
            docker.copy_to(folder, project, "api", "/data/secret.key", secret)
            _own(docker, folder, project, "api", "/data/secret.key")
        else:
            # WAL mode replays studio.db-wal onto studio.db at the next open. Drop the sidecars
            # before the copy, or an unclean stop applies the old pages to the restored file.
            _remove_sqlite_sidecars(docker, folder, project)
            docker.copy_to(folder, project, "superstep", "/data/studio.db", members[db_name])
            docker.copy_to(folder, project, "superstep", "/data/secret.key", secret)
            _own(docker, folder, project, "superstep", "/data/studio.db", "/data/secret.key")
    finally:
        docker.compose(folder, project, ["up", "-d"])
    url = record.get("public_url") or ""
    if url and not docker.wait_healthy(url):
        raise BackupError("UNHEALTHY", "error.health", url=url)
    record["secret_backed_up"] = True
    _write_private(directory / "instance.json", json.dumps(record, indent=2) + "\n")


def schedule_units(directory: Path, record: dict, period: str) -> tuple[str, str, str]:
    """Systemd unit text. ExecStart is the backup script inside `directory`."""
    unit = f"superstep-backup-{record['name']}"
    service = (
        "[Unit]\n"
        f"Description=Superstep backup ({record['name']})\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={directory / 'backup.sh'}\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    timer = (
        "[Unit]\n"
        f"Description=Superstep backup schedule ({record['name']})\n\n"
        "[Timer]\n"
        f"OnCalendar={period}\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )
    return unit, service, timer


def install_schedule(directory: Path, record: dict, docker: Docker, dest: Path, period: str, keep: int) -> str:
    """Write the docker-only script and a user timer, or cron when systemd is missing."""
    dest.mkdir(parents=True, exist_ok=True)
    script = directory / "backup.sh"
    _write_private(script, _shell(directory, dest, record, keep))
    os.chmod(script, 0o700)
    unit, service, timer = schedule_units(directory, record, period)
    _write_private(directory / f"{unit}.service", service)
    _write_private(directory / f"{unit}.timer", timer)
    if docker.systemd_user():
        user = Path.home() / ".config" / "systemd" / "user"
        user.mkdir(parents=True, exist_ok=True)
        _write_private(user / f"{unit}.service", service)
        _write_private(user / f"{unit}.timer", timer)
        docker.enable_timer(f"{unit}.timer")
        return "systemd"
    line = f"{_CRON[period]} {shlex.quote(str(script))}"
    _write_private(directory / "backup.cron", f"# {unit} start\n{line}\n# {unit} end\n")
    docker.install_cron(unit, line)
    return "cron"


def _dump(docker: Docker, directory: str, record: dict):
    project = record["name"]
    if (record.get("topology") or "single") == "full":
        try:
            return _pg_dump(docker, directory, project)
        except DockerError:
            try:
                docker.compose(directory, project, ["stop"])
                docker.compose(directory, project, ["up", "-d", "postgres"])
                return _pg_dump(docker, directory, project)
            finally:
                docker.compose(directory, project, ["up", "-d"])
    try:
        docker.exec_bytes(directory, project, "superstep", ["python", "-c", _SQLITE_PY])
        return "database.sqlite", docker.copy_from(directory, project, "superstep", "/tmp/superstep-online.db")
    except DockerError:
        try:
            docker.compose(directory, project, ["stop"])
            return "database.sqlite", docker.copy_from(directory, project, "superstep", "/data/studio.db")
        finally:
            docker.compose(directory, project, ["up", "-d"])


def _pg_dump(docker: Docker, directory: str, project: str):
    """A Postgres custom dump. `exec_to_file` writes it to disk; a fake Docker still returns bytes."""
    sink = getattr(docker, "exec_to_file", None)
    if sink is None:
        return "database.dump", docker.exec_bytes(directory, project, "postgres", _PG_DUMP)
    fd, name = tempfile.mkstemp(prefix="superstep-dump-", suffix=".dump")
    os.close(fd)
    target = Path(name)
    try:
        sink(directory, project, "postgres", list(_PG_DUMP), target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return "database.dump", target


def _remove_sqlite_sidecars(docker: Docker, directory: str, project: str) -> None:
    """Delete `studio.db-wal` and `studio.db-shm` if they are still on the volume. Missing files are fine."""
    script = (
        "import os\n"
        "for name in ('studio.db-wal', 'studio.db-shm'):\n"
        "    try:\n"
        "        os.remove('/data/' + name)\n"
        "    except FileNotFoundError:\n"
        "        pass\n"
    )
    docker.compose(directory, project, [
        "run", "--rm", "--no-deps", "--user", "root", "--entrypoint", "python",
        "superstep", "-c", script,
    ])


def _own(docker: Docker, directory: str, project: str, service: str, *paths: str) -> None:
    """`docker compose cp` writes as root. The image process is `studio` and must be able to open the files."""
    docker.compose(directory, project, [
        "run", "--rm", "--no-deps", "--user", "root", "--entrypoint", "chown",
        service, "studio:studio", *paths,
    ])


def _secret_bytes(docker: Docker, directory: Path, record: dict, env: dict) -> bytes:
    value = env.get("STUDIO_SECRET_KEY") or ""
    if value:
        return value.encode("utf-8")
    service = "api" if record.get("topology") == "full" else "superstep"
    return docker.copy_from(str(directory), record["name"], service, "/data/secret.key")


def _estimate(docker: Docker, directory: Path, record: dict) -> int:
    total = 0
    for name in (record.get("volumes") or {}).values():
        total += docker.volume_bytes(str(name))
    for filename in (".env", "compose.yml"):
        path = directory / filename
        if path.is_file():
            total += path.stat().st_size
    return max(total, 1)


def _confirm(args, catalog: Catalog, record: dict) -> None:
    expected = str(record.get("name") or "")
    if args.yes:
        if args.name != expected:
            raise BackupError("CONFIRM", "error.confirm_name")
        return
    _write_err(catalog.format("prompt.restore", name=expected) + " ")
    if input("").strip() != expected:
        raise BackupError("CONFIRM", "error.confirm_name")


def _accept(manifest: dict) -> None:
    if manifest.get("format") != _FORMAT:
        raise BackupError("FORMAT", "error.format", format=str(manifest.get("format")))
    server = str(manifest.get("server_version") or "")
    cli = superstep.__version__
    if not server or _newer(server, cli):
        raise BackupError("VERSION", "error.newer", server=server or "unknown", cli=cli)


def _newer(server: str, cli: str) -> bool:
    left, right = _parts(server), _parts(cli)
    size = max(len(left), len(right), 1)
    left.extend([0] * (size - len(left)))
    right.extend([0] * (size - len(right)))
    return left > right


def _parts(value: str) -> list[int]:
    parts = []
    for piece in value.split("."):
        digits = ""
        for char in piece:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return parts


def _manifest(members: dict) -> dict:
    try:
        manifest = json.loads(members["manifest.json"].decode("utf-8"))
    except (KeyError, UnicodeError, json.JSONDecodeError):
        raise BackupError("ARCHIVE", "error.archive")
    if not isinstance(manifest, dict):
        raise BackupError("ARCHIVE", "error.archive")
    return manifest


def _read_archive(path: Path) -> dict:
    if not path.is_file():
        raise BackupError("ARCHIVE", "error.archive")
    found = {}
    try:
        with tarfile.open(path, "r:gz") as tar:
            for info in tar.getmembers():
                name = Path(info.name).name
                if not info.isfile() or name not in _MEMBERS:
                    continue
                handle = tar.extractfile(info)
                if handle is None:
                    continue
                if name == "database.dump":
                    fd, tmp = tempfile.mkstemp(prefix="superstep-restore-", suffix=".dump")
                    os.close(fd)
                    dest = Path(tmp)
                    try:
                        with dest.open("wb") as out:
                            shutil.copyfileobj(handle, out)
                    except Exception:
                        dest.unlink(missing_ok=True)
                        raise
                    found[name] = dest
                else:
                    found[name] = handle.read()
    except (tarfile.TarError, OSError, EOFError):
        _drop_spill(found)
        raise BackupError("ARCHIVE", "error.archive")
    if "manifest.json" not in found:
        _drop_spill(found)
        raise BackupError("ARCHIVE", "error.archive")
    return found


def _drop_spill(members: dict) -> None:
    for value in members.values():
        if isinstance(value, Path):
            value.unlink(missing_ok=True)


def _write_archive(path: Path, members: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as raw:
        with tarfile.open(fileobj=raw, mode="w:gz") as tar:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.mode = 0o600
                info.mtime = int(datetime.now(timezone.utc).timestamp())
                if isinstance(data, Path):
                    info.size = data.stat().st_size
                    with data.open("rb") as handle:
                        tar.addfile(info, handle)
                else:
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
    os.chmod(path, 0o600)


def _write_private_bytes(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.chmod(path, 0o600)


def _env_with_secret(text: str, secret: bytes) -> str:
    value = secret.decode("utf-8")
    lines = []
    found = False
    for line in text.splitlines():
        if line.startswith("STUDIO_SECRET_KEY="):
            lines.append("STUDIO_SECRET_KEY=" + value)
            found = True
        else:
            lines.append(line)
    if not found:
        lines.append("STUDIO_SECRET_KEY=" + value)
    return "\n".join(lines) + "\n"


def _shell(directory: Path, dest: Path, record: dict, keep: int) -> str:
    name = str(record["name"])
    topology = record.get("topology") or "single"
    service = "api" if topology == "full" else "superstep"
    volumes = " ".join(shlex.quote(str(item)) for item in (record.get("volumes") or {}).values())
    volume_check = ""
    if volumes:
        volume_check = (
            f"for vol in {volumes}; do\n"
            "  grep -F -q \"$vol\" \"$dir/instance.json\"\n"
            "done\n"
        )
    volume_size = ""
    if volumes:
        volume_size = f"""for vol in {volumes}; do
  token=$(docker system df -v 2>/dev/null | awk -v vol="$vol" '$1 == vol {{ print $NF; exit }}' || true)
  vol_bytes=$(printf '%s' "$token" | awk '{{ n=$0; u=$0; gsub(/[^0-9.]/, "", n); gsub(/[0-9.]/, "", u); u=toupper(u); m=1; if (u=="KB"||u=="K") m=1000; else if (u=="MB"||u=="M") m=1000000; else if (u=="GB"||u=="G") m=1000000000; else if (u=="KIB") m=1024; else if (u=="MIB") m=1048576; else if (u=="GIB") m=1073741824; if (n=="") n=0; printf "%.0f", n*m }}')
  need=$((need + vol_bytes))
done
"""
    quoted_dir = shlex.quote(str(directory))
    quoted_dest = shlex.quote(str(dest))
    database = "database.dump" if topology == "full" else "database.sqlite"
    dump = (
        'docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" exec -T postgres pg_dump -U studio -d studio -Fc > "$work/database.dump"'
        if topology == "full"
        else 'docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" exec -T superstep python -c \'import sqlite3\nsrc = sqlite3.connect("/data/studio.db")\ndst = sqlite3.connect("/tmp/superstep-online.db")\nsrc.backup(dst)\ndst.close()\nsrc.close()\n\'\n'
        '  docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" cp superstep:/tmp/superstep-online.db "$work/database.sqlite"'
    )
    fallback = (
        'docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" up -d postgres\n'
        '  docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" exec -T postgres pg_dump -U studio -d studio -Fc > "$work/database.dump"'
        if topology == "full"
        else 'docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" cp superstep:/data/studio.db "$work/database.sqlite"'
    )
    return f"""#!/bin/sh
# Calls docker only. Prune runs after a successful backup.
set -eu
dir={quoted_dir}
dest={quoted_dest}
name={shlex.quote(name)}
keep={int(keep)}
topology={shlex.quote(topology)}
service={shlex.quote(service)}
database={shlex.quote(database)}
prune() {{
  found=$(ls -1t "$dest"/superstep-backup-"$name"-*.tar.gz 2>/dev/null || true)
  if [ -z "$found" ]; then
    return 0
  fi
  printf '%s\\n' "$found" | awk -v keep="$keep" 'NR > keep {{ print }}' | while IFS= read -r old; do
    rm -f "$old"
  done
}}
if [ "${{1:-}}" = "prune" ]; then
  prune
  exit 0
fi
{volume_check}free_kb=$(df -Pk "$dest" | awk 'NR==2 {{ print $4 }}')
need=$(wc -c < "$dir/.env")
need=$((need + $(wc -c < "$dir/compose.yml")))
{volume_size}if [ "${{free_kb:-0}}" -lt $(( (need + 1023) / 1024 )) ]; then
  echo "not enough disk" >&2
  exit 1
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
umask 077
if ! {{
{dump}
}}; then
  docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" stop
  if ! {{
{fallback}
  }}; then
    docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" up -d
    exit 1
  fi
  docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" up -d
fi
cp "$dir/.env" "$work/.env"
cp "$dir/compose.yml" "$work/compose.yml"
awk -F= '$1 == "STUDIO_SECRET_KEY" {{ print substr($0, index($0, "=") + 1); exit }}' "$dir/.env" > "$work/secret.key"
if [ ! -s "$work/secret.key" ]; then
  docker compose -p "$name" --project-directory "$dir" -f "$dir/compose.yml" cp "$service:/data/secret.key" "$work/secret.key"
fi
version=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p' "$dir/instance.json" | head -n 1)
created=$(date -u +%Y-%m-%dT%H:%M:%SZ)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
printf '%s\\n' "{{" '"format": 1,' '"server_version": "'"$version"'",' '"topology": "'"$topology"'",' '"name": "'"$name"'",' '"created": "'"$created"'",' '"database": "'"$database"'"' "}}" > "$work/manifest.json"
mkdir -p "$dest"
archive="$dest/superstep-backup-$name-$stamp.tar.gz"
tar -czf "$archive" -C "$work" manifest.json "$database" secret.key .env compose.yml
chmod 0600 "$archive"
prune
"""


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


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _write_err(text: str) -> None:
    from superstep.cli import _write_err as write_err
    write_err(text)


def _write_json(payload: dict) -> None:
    from superstep.cli import _write_json as write_json
    write_json(payload)
