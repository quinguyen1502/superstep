"""Chat attachments in backups and `attachments migrate` (TASK-0194, REQ-0080, DEC-0074)."""
import json

import pytest

import superstep
from test_backup import BackupDocker, archive_members, invoke, layout, setting

TAR = b"attachments-tar-bytes"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setattr(superstep, "__version__", "1.2.3")


class Docker(BackupDocker):
    def __init__(self, migrate=None, **kw):
        super().__init__(**kw)
        self.migrate = migrate or {}

    def exec_bytes(self, directory, project, service, command, stdin=None):
        self.calls.append(("exec", service, tuple(command), stdin))
        if command[:4] == ["python", "-m", "app.admin_cmd", "attachments-export"]:
            return TAR
        if command[:4] == ["python", "-m", "app.admin_cmd", "attachments-migrate"]:
            from superstep.cli.docker import DockerError
            if isinstance(self.migrate, Exception):
                raise self.migrate
            return json.dumps(self.migrate).encode()
        return super().exec_bytes(directory, project, service, command)


def storage(directory, value, extra=""):
    env = directory / ".env"
    env.write_text(env.read_text(encoding="utf-8") + f"STUDIO_ATTACHMENT_STORAGE={value}\n" + extra, encoding="utf-8")


def backup(directory, docker, *flags):
    code, out, err = invoke(["backup", "--dir", str(directory), "--json", *flags], docker)
    assert code == 0, out
    body = json.loads(out)
    return body, archive_members(body["archive"])


def test_db_backups_are_unchanged_and_record_the_backend(tmp_path):
    directory = layout(tmp_path)
    body, members = backup(directory, Docker())
    assert "attachments.tar" not in members and "warning" not in body
    manifest = json.loads(members["manifest.json"])
    assert manifest["attachment_storage"] == "db" and manifest["attachments_included"] is False


def test_fs_backups_carry_the_folder(tmp_path):
    directory = layout(tmp_path, "full")
    storage(directory, "fs")
    docker = Docker()
    _body, members = backup(directory, docker)
    assert members["attachments.tar"] == TAR
    assert json.loads(members["manifest.json"])["attachments_included"] is True
    export = [c for c in docker.calls if c[0] == "exec" and "attachments-export" in c[2]]
    assert export and export[0][1] == "api" and "--include-s3" not in export[0][2]


def test_s3_backups_record_the_bucket_and_include_objects_only_when_asked(tmp_path):
    directory = layout(tmp_path)
    storage(directory, "s3", "STUDIO_ATTACHMENT_S3_BUCKET=team-files\nSTUDIO_ATTACHMENT_S3_PREFIX=prod\nSTUDIO_ATTACHMENT_S3_SECRET_ACCESS_KEY=s3-very-secret\n")
    body, members = backup(directory, Docker())
    manifest = json.loads(members["manifest.json"])
    assert manifest["attachment_s3"] == {"bucket": "team-files", "prefix": "prod"} and "attachments.tar" not in members
    assert "team-files" in body["warning"] and "s3-very-secret" not in json.dumps(manifest)
    docker = Docker()
    body, members = backup(directory, docker, "--include-attachments")
    assert members["attachments.tar"] == TAR and "warning" not in body
    assert any("--include-s3" in c[2] for c in docker.calls if c[0] == "exec")


def test_restore_refuses_another_backend_unless_forced_and_imports_the_files(tmp_path):
    directory = layout(tmp_path)
    storage(directory, "fs")
    _body, _members = backup(directory, Docker())
    archive = _body["archive"]
    (directory / ".env").write_text((directory / ".env").read_text(encoding="utf-8").replace("STUDIO_ATTACHMENT_STORAGE=fs", "STUDIO_ATTACHMENT_STORAGE=s3"), encoding="utf-8")
    docker = Docker()
    code, out, _err = invoke(["restore", archive, "--dir", str(directory), "--yes", "--name", "inst", "--json"], docker)
    assert code != 0 and json.loads(out)["error"]["code"] == "STORAGE_MISMATCH" and docker.calls == []
    code, out, _err = invoke(["restore", archive, "--dir", str(directory), "--yes", "--name", "inst", "--force", "--json"], docker)
    assert code == 0, out
    assert setting((directory / ".env").read_text(encoding="utf-8"), "STUDIO_ATTACHMENT_STORAGE") == "s3"  # the instance's own setting
    imported = [c for c in docker.calls if c[0] == "exec" and "attachments-import" in c[2]]
    assert imported and imported[0][3] == TAR
    assert docker.calls.index(imported[0]) > max(i for i, c in enumerate(docker.calls) if c[0] == "compose" and c[1][:2] == ("up", "-d"))


def test_a_matching_restore_round_trips(tmp_path):
    directory = layout(tmp_path)
    storage(directory, "fs")
    body, _members = backup(directory, Docker())
    docker = Docker()
    code, out, _err = invoke(["restore", body["archive"], "--dir", str(directory), "--yes", "--name", "inst", "--json"], docker)
    assert code == 0 and json.loads(out)["ok"] is True
    assert any(c[0] == "exec" and "attachments-import" in c[2] for c in docker.calls)


def test_the_scheduled_script_exports_a_folder(tmp_path):
    from superstep.cli.backup import _shell
    script = _shell(tmp_path, tmp_path / "out", {"name": "inst", "topology": "single", "volumes": {}}, 7)
    assert "attachments-export" in script and '"attachment_storage"' in script and "attachments.tar" in script


@pytest.mark.parametrize("lang", ["en", "vi"])
def test_migrate_prints_the_outcome(tmp_path, lang):
    directory = layout(tmp_path)
    docker = Docker(migrate={"to": "fs", "dry_run": False, "moved": 3, "bytes": 2_000_000, "failed": [], "pending": 0})
    code, _out, err = invoke(["--lang", lang, "attachments", "migrate", "--to", "fs", "--dir", str(directory)], docker)
    assert code == 0
    assert ("Moved 3 files (2.0 MB) to fs." if lang == "en" else "Đã chuyển 3 tệp (2.0 MB) sang fs.") in err
    call = [c for c in docker.calls if c[0] == "exec"][0]
    assert call[1] == "superstep" and call[2][3:] == ("attachments-migrate", "--to", "fs", "--batch", "100")


def test_migrate_dry_run_failures_and_server_errors(tmp_path):
    from superstep.cli.docker import DockerError
    directory = layout(tmp_path)
    docker = Docker(migrate={"to": "s3", "dry_run": True, "moved": 0, "bytes": 0, "failed": [], "pending": 7})
    code, _out, err = invoke(["attachments", "migrate", "--to", "s3", "--dry-run", "--dir", str(directory)], docker)
    assert code == 0 and "7 files would move to s3." in err
    docker = Docker(migrate={"to": "s3", "dry_run": False, "moved": 1, "bytes": 10, "failed": [{"id": "a1", "reason": "missing on its backend"}], "pending": 1})
    code, out, _err = invoke(["attachments", "migrate", "--to", "s3", "--dir", str(directory), "--json"], docker)
    assert code == 1 and json.loads(out)["failed"][0]["id"] == "a1"
    docker = Docker(migrate=DockerError('{"code": "CHAT_ATTACHMENT_STORAGE", "message": "Attachment storage is not available: S3 error AccessDenied"}'))
    code, out, _err = invoke(["attachments", "migrate", "--to", "s3", "--dir", str(directory), "--json"], docker)
    assert code != 0 and json.loads(out)["error"]["code"] == "CHAT_ATTACHMENT_STORAGE" and "AccessDenied" in json.loads(out)["error"]["message"]
    code, _out, _err = invoke(["attachments", "migrate", "--to", "ftp", "--dir", str(directory)], docker)
    assert code == 2
