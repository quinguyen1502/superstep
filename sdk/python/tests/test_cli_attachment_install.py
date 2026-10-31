"""Chat attachment storage in `install`, `deploy` and `doctor` (TASK-0195, REQ-0080, DEC-0074)."""
import io
import json
import os
import stat

import pytest

from test_install import FakeDocker, env_values, install_args, invoke
from test_status import OpsDocker, layout

SECRET = "s3-secret-never-printed"
BASE = "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\n"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("SUPERSTEP_S3_SECRET_ACCESS_KEY", raising=False)


def test_db_is_the_default_and_writes_nothing(tmp_path):
    directory = tmp_path / "plain"
    code, out, _err = invoke(install_args(directory) + ["--json"], FakeDocker())
    assert code == 0 and not any(k.startswith("STUDIO_ATTACHMENT_") for k in env_values(directory))
    compose = (directory / "compose.yml").read_text(encoding="utf-8")
    assert "STUDIO_ATTACHMENT_STORAGE: ${STUDIO_ATTACHMENT_STORAGE:-db}" in compose


def test_fs_on_both_topologies(tmp_path):
    for topology in ("single", "full"):
        directory = tmp_path / f"fs-{topology}"
        code, out, _err = invoke(install_args(directory, tail=["--topology", topology, "--attachment-storage", "fs"]) + ["--json"], FakeDocker())
        assert code == 0, out
        assert env_values(directory)["STUDIO_ATTACHMENT_STORAGE"] == "fs"
        compose = (directory / "compose.yml").read_text(encoding="utf-8")
        assert compose.count("      STUDIO_ATTACHMENT_STORAGE:") == (1 if topology == "single" else 2)  # api and worker share /data


def test_s3_with_yes_keeps_the_secret_out_of_argv_and_output(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSTEP_S3_SECRET_ACCESS_KEY", SECRET)
    directory = tmp_path / "s3"
    tail = ["--topology", "full", "--attachment-storage", "s3", "--s3-bucket", "team-files", "--s3-endpoint", "https://acct.r2.cloudflarestorage.com",
            "--s3-region", "auto", "--s3-access-key-id", "AKID"]
    code, out, err = invoke(install_args(directory, tail=tail) + ["--json"], FakeDocker())
    assert code == 0, out
    env = env_values(directory)
    assert env["STUDIO_ATTACHMENT_STORAGE"] == "s3" and env["STUDIO_ATTACHMENT_S3_BUCKET"] == "team-files"
    assert env["STUDIO_ATTACHMENT_S3_SECRET_ACCESS_KEY"] == SECRET and env["STUDIO_ATTACHMENT_S3_REGION"] == "auto"
    assert stat.S_IMODE((directory / ".env").stat().st_mode) == 0o600
    assert SECRET not in out and SECRET not in err and SECRET not in (directory / "compose.yml").read_text(encoding="utf-8")
    code, out, _err = invoke(["config", "--dir", str(directory), "--json"], OpsDocker())
    assert SECRET not in out


def test_s3_secret_from_stdin_and_errors(tmp_path, monkeypatch):
    directory = tmp_path / "stdin"
    monkeypatch.setattr("sys.stdin", io.StringIO(SECRET + "\n"))
    tail = ["--attachment-storage", "s3", "--s3-bucket", "b", "--s3-access-key-id", "AKID", "--s3-secret-stdin", "--s3-path-style"]
    code, out, _err = invoke(install_args(directory, tail=tail) + ["--json"], FakeDocker())
    assert code == 0 and env_values(directory)["STUDIO_ATTACHMENT_S3_PATH_STYLE"] == "true"
    code, out, _err = invoke(install_args(tmp_path / "nobucket", tail=["--attachment-storage", "s3"]) + ["--json"], FakeDocker())
    assert code != 0 and json.loads(out)["error"]["code"] == "S3_BUCKET"
    code, out, _err = invoke(install_args(tmp_path / "halfkeys", tail=["--attachment-storage", "s3", "--s3-bucket", "b", "--s3-access-key-id", "AKID"]) + ["--json"], FakeDocker())
    assert code != 0 and json.loads(out)["error"]["code"] == "S3_KEYS"
    assert not (tmp_path / "nobucket" / ".env").exists()


@pytest.mark.parametrize("lang,question", [("en", "Where should chat attachments be stored?"), ("vi", "Lưu tệp đính kèm chat ở đâu?")])
def test_the_prompt_offers_what_fits_the_topology(tmp_path, monkeypatch, lang, question):
    asked = []
    answers = iter(["single", "fs"])
    monkeypatch.setattr("builtins.input", lambda text: asked.append(text) or next(answers))
    directory = tmp_path / f"ask-{lang}"
    argv = ["--lang", lang, "install", "--name", directory.name, "--dir", str(directory), "--url", "http://localhost:8000", "--admin-email", "you@example.com"]
    code, _out, _err = invoke(argv, FakeDocker())
    assert code == 0
    prompt = [a for a in asked if question in a][0]
    assert "fs" in prompt and "s3" not in prompt  # single host: database or folder
    assert env_values(directory)["STUDIO_ATTACHMENT_STORAGE"] == "fs"


def test_deploy_takes_the_same_flags():
    from superstep.cli import _parser
    from superstep.cli.i18n import Catalog
    parser = _parser(Catalog.load("en"), False)
    args = parser.parse_args(["deploy", "ssh://me@host", "--attachment-storage", "fs"])
    assert args.attachment_storage == "fs"


def test_doctor_reports_the_backend_without_secrets(tmp_path):
    ok = layout(tmp_path / "ok", BASE + "STUDIO_ATTACHMENT_STORAGE=fs\n")
    code, out, _err = invoke(["doctor", "--dir", str(ok), "--json"], OpsDocker(health={"attachment_storage": "fs", "attachment_storage_ok": True,
                                                                                         "attachment_storage_worker_seen": 12.0}))
    body = json.loads(out)
    assert code == 0 and body["attachment_storage"] == {"backend": "fs", "ok": True}
    bad = layout(tmp_path / "bad", BASE + f"STUDIO_ATTACHMENT_STORAGE=s3\nSTUDIO_ATTACHMENT_S3_SECRET_ACCESS_KEY={SECRET}\n")
    code, out, err = invoke(["doctor", "--dir", str(bad)], OpsDocker(health={"attachment_storage": "s3", "attachment_storage_ok": False,
                                                                             "attachment_storage_reason": "S3 error AccessDenied"}))
    assert code != 0 and "s3 is not working: S3 error AccessDenied" in err and SECRET not in err + out
    silent = layout(tmp_path / "silent", BASE)
    code, out, _err = invoke(["doctor", "--dir", str(silent), "--json"], OpsDocker(health={}))
    assert code == 0 and json.loads(out)["attachment_storage"] == {"backend": "db", "ok": None}
