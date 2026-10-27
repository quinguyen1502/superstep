"""backup, restore, and scheduled backups (TASK-0152)."""
import json
import os
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

import superstep
from superstep.cli import run
from superstep.cli.backup import _write_archive

SECRET = "superstep-secret-value"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)


class BackupDocker:
    def __init__(self, free=10 ** 12, volumes=None, dump=b"database-bytes", systemd=True):
        self.free = free
        self.volumes = volumes or {}
        self.dump = dump
        self.has_systemd = systemd
        self.calls = []

    def disk_free_bytes(self, path):
        return self.free

    def volume_bytes(self, name):
        return self.volumes.get(name, 0)

    def exec_bytes(self, directory, project, service, command):
        self.calls.append(("exec", service, tuple(command)))
        if command and command[0] == "pg_dump":
            return self.dump
        return b""

    def copy_from(self, directory, project, service, path):
        self.calls.append(("copy_from", service, path))
        return self.dump

    def copy_to(self, directory, project, service, path, data):
        self.calls.append(("copy_to", service, path))

    def compose(self, directory, project, args):
        self.calls.append(("compose", tuple(args)))

    def wait_healthy(self, url, timeout=60):
        self.calls.append(("wait", url))
        return True

    def systemd_user(self):
        return self.has_systemd

    def enable_timer(self, unit):
        self.calls.append(("enable_timer", unit))

    def install_cron(self, marker, line):
        self.calls.append(("cron", marker, line))


def invoke(argv, docker):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker)
    return code, out.getvalue(), err.getvalue()


def layout(tmp_path, topology="single"):
    directory = tmp_path / "inst"
    directory.mkdir(parents=True)
    env = f"JWT_SECRET=abc\nSTUDIO_SECRET_KEY={SECRET}\nSTUDIO_ENV=production\n"
    if topology == "full":
        env += "POSTGRES_PASSWORD=pg-secret\n"
        volumes = {"pgdata": "inst_pg", "redisdata": "inst_redis", "apidata": "inst_api"}
    else:
        volumes = {"data": "inst_data"}
    (directory / ".env").write_text(env, encoding="utf-8")
    (directory / "compose.yml").write_text("services: {}\n", encoding="utf-8")
    record = {
        "name": "inst",
        "topology": topology,
        "sandbox": False,
        "version": "1.2.3",
        "public_url": "http://localhost:8000",
        "dir": str(directory),
        "remote": None,
        "volumes": volumes,
    }
    (directory / "instance.json").write_text(json.dumps(record), encoding="utf-8")
    return directory


def archive_members(path):
    with tarfile.open(path, "r:gz") as tar:
        found = {}
        for info in tar.getmembers():
            if info.isfile():
                handle = tar.extractfile(info)
                found[Path(info.name).name] = handle.read()
        return found


def setting(text, key):
    for line in text.splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1]
    return ""


@pytest.mark.parametrize(
    ("topology", "member"),
    [("single", "database.sqlite"), ("full", "database.dump")],
)
def test_backup_archive_contains_the_instance(tmp_path, topology, member):
    directory = layout(tmp_path, topology)
    docker = BackupDocker(dump=b"PGDMP" if topology == "full" else b"sqlite-bytes")
    code, out, err = invoke(["backup", "--dir", str(directory), "--json"], docker)
    body = json.loads(out)
    archive = Path(body["archive"])
    members = archive_members(archive)
    assert code == 0 and err == ""
    assert archive.name.startswith("superstep-backup-inst-")
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    assert set(members) == {"manifest.json", member, "secret.key", ".env", "compose.yml"}
    manifest = json.loads(members["manifest.json"])
    assert manifest["format"] == 1 and manifest["name"] == "inst" and manifest["database"] == member
    assert members["secret.key"] == SECRET.encode()
    assert setting(members[".env"].decode(), "STUDIO_SECRET_KEY") == SECRET
    assert b"services: {}" in members["compose.yml"]
    assert SECRET not in out and SECRET not in err
    assert not any(call[0] == "compose" and call[1][0] == "stop" for call in docker.calls)
    if topology == "single":
        assert any(call[0] == "exec" and "src.backup(dst)" in " ".join(call[2]) for call in docker.calls)
    else:
        assert any(call[0] == "exec" and call[2][0] == "pg_dump" and "-Fc" in call[2] for call in docker.calls)
    assert json.loads((directory / "instance.json").read_text())["secret_backed_up"] is True


def test_short_disk_does_not_stop_or_write(tmp_path):
    directory = layout(tmp_path)
    before = sorted(path.name for path in directory.iterdir())
    docker = BackupDocker(free=10, volumes={"inst_data": 10_000_000})
    code, out, err = invoke(["backup", "--dir", str(directory), "--json"], docker)
    assert code != 0
    assert json.loads(out)["ok"] is False
    assert [call for call in docker.calls if call[0] in ("compose", "exec", "copy_from")] == []
    assert sorted(path.name for path in directory.iterdir()) == before


def test_restore_refuses_a_newer_format_or_server(tmp_path):
    directory = layout(tmp_path)
    env_before = (directory / ".env").read_text(encoding="utf-8")
    docker = BackupDocker()
    newer = tmp_path / "newer.tar.gz"
    unknown = tmp_path / "format.tar.gz"
    base = {
        "server_version": "0.1.0",
        "topology": "single",
        "name": "inst",
        "created": "2026-10-27T00:00:00Z",
        "database": "database.sqlite",
    }
    _write_archive(newer, _bundle({**base, "format": 1, "server_version": "9.9.9"}))
    _write_archive(unknown, _bundle({**base, "format": 2}))
    for archive in (unknown, newer):
        code, out, _err = invoke(["restore", str(archive), "--dir", str(directory), "--yes", "--name", "inst", "--json"], docker)
        assert code != 0 and json.loads(out)["ok"] is False
    assert (directory / ".env").read_text(encoding="utf-8") == env_before
    assert docker.calls == []


def test_restore_requires_the_typed_name(tmp_path, monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "1.2.3")
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    directory = layout(tmp_path)
    docker = BackupDocker()
    code, out, _err = invoke(["backup", "--dir", str(directory), "--json"], docker)
    archive = json.loads(out)["archive"]
    (directory / ".env").write_text("STUDIO_SECRET_KEY=changed\n", encoding="utf-8")
    code, out, _err = invoke(["restore", archive, "--dir", str(directory), "--json"], docker)
    assert code != 0
    assert setting((directory / ".env").read_text(encoding="utf-8"), "STUDIO_SECRET_KEY") == "changed"
    code, out, _err = invoke(["restore", archive, "--dir", str(directory), "--yes", "--json"], docker)
    assert code != 0
    assert setting((directory / ".env").read_text(encoding="utf-8"), "STUDIO_SECRET_KEY") == "changed"


def test_restore_yes_name_writes_the_archive_key(tmp_path, monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "1.2.3")
    directory = layout(tmp_path)
    docker = BackupDocker(dump=b"sqlite-bytes")
    code, out, _err = invoke(["backup", "--dir", str(directory), "--json"], docker)
    archive = Path(json.loads(out)["archive"])
    key = archive_members(archive)["secret.key"].decode()
    (directory / ".env").write_text("STUDIO_SECRET_KEY=changed\n", encoding="utf-8")
    code, out, err = invoke(["restore", str(archive), "--dir", str(directory), "--yes", "--name", "inst", "--json"], docker)
    assert code == 0 and err == ""
    assert json.loads(out)["ok"] is True
    assert setting((directory / ".env").read_text(encoding="utf-8"), "STUDIO_SECRET_KEY") == key
    assert SECRET not in out and SECRET not in err


def test_schedule_systemd_prunes_to_two(tmp_path):
    directory = layout(tmp_path)
    docker = BackupDocker(systemd=True)
    code, out, err = invoke(["backup", "--dir", str(directory), "--schedule", "daily", "--keep", "2", "--json"], docker)
    assert code == 0 and err == ""
    assert json.loads(out)["timer"] == "systemd"
    timer = directory / "superstep-backup-inst.timer"
    assert "OnCalendar=daily" in timer.read_text(encoding="utf-8")
    assert not (directory / "backup.cron").exists()
    assert ("enable_timer", "superstep-backup-inst.timer") in docker.calls
    script = (directory / "backup.sh").read_text(encoding="utf-8")
    assert "docker compose" in script and "superstep backup" not in script
    for index, stamp in enumerate(("20260101T000000Z", "20260102T000000Z", "20260103T000000Z")):
        path = directory / f"superstep-backup-inst-{stamp}.tar.gz"
        path.write_bytes(b"x")
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))
    proc = subprocess.run(["sh", str(directory / "backup.sh"), "prune"], capture_output=True)
    assert proc.returncode == 0
    left = sorted(path.name for path in directory.glob("superstep-backup-inst-*.tar.gz"))
    assert left == [
        "superstep-backup-inst-20260102T000000Z.tar.gz",
        "superstep-backup-inst-20260103T000000Z.tar.gz",
    ]


def test_schedule_uses_cron_without_systemd(tmp_path):
    directory = layout(tmp_path)
    docker = BackupDocker(systemd=False)
    code, out, _err = invoke(["backup", "--dir", str(directory), "--schedule", "weekly", "--keep", "2", "--json"], docker)
    assert code == 0 and json.loads(out)["timer"] == "cron"
    assert "backup.sh" in (directory / "backup.cron").read_text(encoding="utf-8")
    assert not any(call[0] == "enable_timer" for call in docker.calls)
    assert any(call[0] == "cron" for call in docker.calls)


def test_help_examples():
    code, out, err = invoke(["backup", "--help"], BackupDocker())
    assert code == 0 and out == "" and "Example: superstep backup" in err
    code, out, err = invoke(["restore", "--help"], BackupDocker())
    assert code == 0 and out == "" and "Example: superstep restore" in err


def test_new_catalog_keys_match():
    root = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((root / "vi.json").read_text(encoding="utf-8"))
    assert set(en) == set(vi)
    for key in ("help.backup", "help.restore", "error.disk", "error.format", "error.newer", "error.confirm_name", "schedule.systemd", "schedule.cron"):
        assert en[key] and vi[key]


def _bundle(manifest):
    return {
        "manifest.json": json.dumps(manifest).encode(),
        "database.sqlite": b"db",
        "secret.key": b"archive-secret",
        ".env": b"STUDIO_SECRET_KEY=archive-secret\n",
        "compose.yml": b"services: {}\n",
    }
