"""status, config, and doctor (TASK-0151)."""
import json
import os
import stat

import pytest

from superstep.cli import run


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)


class OpsDocker:
    def __init__(self, release=None, skew=0, probe="ok", health=None, services=None, volumes=None):
        self.release = release
        self.skew = skew
        self.probe_result = probe
        self.health_body = health or {"version": "1.2.3", "database": "sqlite", "run_bus": "memory"}
        self.services = services or [{"name": "superstep", "state": "running"}]
        self.volumes = volumes or {"inst_data": 4096}
        self.calls = []

    def health(self, url):
        return dict(self.health_body)

    def ps(self, directory, project):
        return list(self.services)

    def volume_bytes(self, name):
        return self.volumes.get(name, 0)

    def registry_version(self):
        return self.release

    def clock_skew_seconds(self, directory, project, service):
        return self.skew

    def probe(self, url):
        self.calls.append(("probe", url))
        return self.probe_result

    def compose(self, directory, project, args):
        self.calls.append(("compose", project, tuple(args)))


def invoke(argv, docker):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker)
    return code, out.getvalue(), err.getvalue()


def layout(tmp_path, env, compose="services: {}\n", **record):
    directory = tmp_path / "inst"
    directory.mkdir(parents=True)
    (directory / ".env").write_text(env, encoding="utf-8")
    os.chmod(directory / ".env", 0o600)
    (directory / "compose.yml").write_text(compose, encoding="utf-8")
    body = {
        "name": "inst",
        "topology": "single",
        "sandbox": False,
        "version": "1.2.3",
        "public_url": "http://localhost:8000",
        "dir": str(directory),
        "remote": None,
        "volumes": {"data": "inst_data"},
    }
    body.update(record)
    (directory / "instance.json").write_text(json.dumps(body), encoding="utf-8")
    return directory


def test_status_json_reports_health_disk_and_release(tmp_path):
    directory = layout(tmp_path, "JWT_SECRET=abc\nSTUDIO_ENV=production\n")
    code, out, err = invoke(["status", "--dir", str(directory), "--json"], OpsDocker(release="9.9.9"))
    body = json.loads(out)
    assert code == 0 and err == ""
    assert body["version"] == "1.2.3"
    assert body["services"] == [{"name": "superstep", "state": "running"}]
    assert body["database"] == "sqlite" and body["run_bus"] == "memory"
    assert body["volumes"] == [{"name": "inst_data", "bytes": 4096}]
    assert body["release"] == "9.9.9"


def test_status_offline_release_is_unknown(tmp_path):
    directory = layout(tmp_path, "JWT_SECRET=abc\n")
    code, out, _err = invoke(["status", "--dir", str(directory), "--json"], OpsDocker(release=None))
    assert code == 0 and json.loads(out)["release"] == "unknown"


def test_doctor_reports_the_three_fixtures(tmp_path):
    unset = layout(tmp_path / "a", "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\n", public_url="http://localhost:8000")
    code, _out, err = invoke(["doctor", "--dir", str(unset)], OpsDocker())
    assert "STUDIO_ENV" in err and code != 0
    placeholder = layout(tmp_path / "b", "JWT_SECRET=dev-secret-change-me\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\n")
    _code, _out, err = invoke(["doctor", "--dir", str(placeholder)], OpsDocker())
    assert "placeholder" in err
    sandbox = layout(
        tmp_path / "c",
        "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\nSTUDIO_TRUSTED_PROXIES=10.0.0.0/8\n",
        compose="services: {}\n",
        topology="full",
        sandbox=True,
        public_url="https://studio.example",
    )
    _code, _out, err = invoke(["doctor", "--dir", str(sandbox)], OpsDocker())
    assert "Docker socket" in err


def test_clean_doctor_exits_zero(tmp_path):
    directory = layout(tmp_path, "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\n")
    code, out, err = invoke(["doctor", "--dir", str(directory), "--json"], OpsDocker())
    body = json.loads(out)
    assert code == 0 and err == "" and body["findings"] == []


def test_clock_skew_threshold(tmp_path):
    directory = layout(tmp_path, "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\n")
    code, out, _err = invoke(["doctor", "--dir", str(directory), "--json"], OpsDocker(skew=30))
    assert code == 0 and json.loads(out)["findings"] == []
    code, out, _err = invoke(["doctor", "--dir", str(directory), "--json"], OpsDocker(skew=31))
    assert code != 0 and any("31" in item for item in json.loads(out)["findings"])


def test_provider_unreachable_and_offline(tmp_path):
    env = "JWT_SECRET=abc\nSTUDIO_SECRET_KEY=key\nSTUDIO_ENV=production\nOPENAI_API_KEY=sk-secret\nOPENAI_BASE_URL=https://models.example\n"
    directory = layout(tmp_path, env)
    code, out, err = invoke(["doctor", "--dir", str(directory), "--json"], OpsDocker(probe="unreachable"))
    text = out + err
    assert code != 0 and "https://models.example" in text and "sk-secret" not in text
    code, out, err = invoke(["doctor", "--dir", str(directory), "--json"], OpsDocker(probe="offline"))
    body = json.loads(out)
    assert code == 0 and body["findings"] == [] and body["notes"] and "sk-secret" not in out + err


def test_config_masks_shows_and_restarts(tmp_path):
    env = "JWT_SECRET=top-secret\nSTUDIO_ADMIN_PASSWORD=pw\nSTUDIO_PUBLIC_URL=http://localhost:8000\n"
    directory = layout(tmp_path, env)
    code, out, _err = invoke(["config", "list", "--dir", str(directory), "--json"], OpsDocker())
    listed = json.loads(out)["settings"]
    assert code == 0
    masked = {item["key"]: item["value"] for item in listed}
    assert masked["JWT_SECRET"] == "***" and masked["STUDIO_ADMIN_PASSWORD"] == "***"
    assert "top-secret" not in out and "pw" not in out
    code, out, _err = invoke(["config", "get", "JWT_SECRET", "--show-secrets", "--dir", str(directory), "--json"], OpsDocker())
    assert code == 0 and json.loads(out)["value"] == "top-secret"
    docker = OpsDocker()
    code, out, _err = invoke(["config", "set", "STUDIO_PUBLIC_URL", "https://studio.example", "--dir", str(directory), "--json"], docker)
    assert code == 0 and json.loads(out)["restarted"] is False and docker.calls == []
    text = (directory / ".env").read_text(encoding="utf-8")
    assert "STUDIO_PUBLIC_URL=https://studio.example" in text
    assert stat.S_IMODE((directory / ".env").stat().st_mode) == 0o600
    code, out, _err = invoke(["config", "set", "JWT_SECRET", "rotated", "--dir", str(directory), "--json"], docker)
    assert code == 0 and json.loads(out)["restarted"] is True
    assert ("compose", "inst", ("restart",)) in docker.calls


def test_commands_have_help(tmp_path):
    for command in ("status", "config", "doctor"):
        code, out, err = invoke([command, "--help"], OpsDocker())
        assert code == 0 and out == "" and "Example:" in err
