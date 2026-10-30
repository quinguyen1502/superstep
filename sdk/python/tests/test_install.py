"""install, adopt, and the compose wrappers (TASK-0150)."""
import json
import stat
from pathlib import Path

import pytest

import superstep
from superstep.cli import run

SECRET_NAMES = ("JWT_SECRET", "STUDIO_SECRET_KEY")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setattr(superstep, "__version__", "1.2.3")


class FakeDocker:
    def __init__(self, docker_ok=True, compose_v2=True, memory=4 * 1024 ** 3, disk=10 * 1024 ** 3, ports=None, healthy=True):
        self._docker_ok = docker_ok
        self._compose_v2 = compose_v2
        self._memory = memory
        self._disk = disk
        self.ports = ports or {}
        self.healthy = healthy
        self.calls = []

    def docker_ok(self):
        self.calls.append(("docker",))
        return self._docker_ok

    def compose_v2(self):
        self.calls.append(("compose-v2",))
        return self._compose_v2

    def memory_bytes(self):
        return self._memory

    def disk_free_bytes(self, path):
        return self._disk

    def port_owner(self, port):
        return self.ports.get(port)

    def load(self, tar):
        self.calls.append(("load", tar))

    def pull(self, image):
        self.calls.append(("pull", image))

    def compose(self, directory, project, args):
        self.calls.append(("compose", project, args))

    def wait_healthy(self, url):
        self.calls.append(("health", url))
        return self.healthy


def invoke(argv, docker):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker)
    return code, out.getvalue(), err.getvalue()


def install_args(directory, **extra):
    args = ["install", "--yes", "--name", directory.name, "--dir", str(directory), "--url", "http://localhost:8000", "--admin-email", "you@example.com"]
    for item in extra.pop("tail", []):
        args.append(item)
    return args


def env_values(directory):
    values = {}
    for line in (directory / ".env").read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_install_single_and_full_pin_images_and_modes(tmp_path):
    for topology, sandbox, marker in (("single", False, f"{superstep.APP if False else 'ghcr.io/quinguyen1502/superstep'}:1.2.3"), ("full", False, "ghcr.io/quinguyen1502/superstep-api:1.2.3"), ("full", True, "ghcr.io/quinguyen1502/superstep-sandbox:1.2.3")):
        directory = tmp_path / f"{topology}-{sandbox}"
        docker = FakeDocker()
        tail = ["--topology", topology] + (["--sandbox"] if sandbox else [])
        code, out, err = invoke(install_args(directory, tail=tail) + ["--json"], docker)
        body = json.loads(out)
        assert code == 0 and err == "" and body["admin_password"]
        compose = (directory / "compose.yml").read_text(encoding="utf-8")
        assert marker in compose and "build:" not in compose and ":latest" not in compose
        if topology == "single":
            assert 'volumes: ["data:/data"]' in compose
        else:
            assert 'volumes: ["pgdata:/var/lib/postgresql/data"]' in compose
            assert 'volumes: ["redisdata:/data"]' in compose
            assert 'volumes: ["apidata:/data"]' in compose
            assert "inst_pgdata" not in compose
            assert f"{directory.name}_pgdata" in compose
        assert stat.S_IMODE((directory / ".env").stat().st_mode) == 0o600
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        record = json.loads((directory / "instance.json").read_text(encoding="utf-8"))
        assert record["topology"] == topology and record["sandbox"] is sandbox and record["remote"] is None
        assert stat.S_IMODE((directory / "instance.json").stat().st_mode) == 0o600
        assert "JWT_SECRET" not in out and "STUDIO_SECRET_KEY" not in out
        assert env_values(directory)["JWT_SECRET"] not in out
        assert out.count(body["admin_password"]) == 1


def test_second_install_refuses_and_keeps_the_env(tmp_path):
    directory = tmp_path / "inst"
    assert invoke(install_args(directory), FakeDocker())[0] == 0
    original = (directory / ".env").read_bytes()
    code, _out, err = invoke(install_args(directory), FakeDocker())
    assert code != 0 and "already installed" in err
    assert (directory / ".env").read_bytes() == original


def test_images_loads_and_does_not_pull(tmp_path):
    docker = FakeDocker()
    code, _out, _err = invoke(install_args(tmp_path / "inst", tail=["--images", "/tmp/images.tar"]), docker)
    kinds = [call[0] for call in docker.calls]
    assert code == 0 and "load" in kinds and "pull" not in kinds


def test_missing_docker_writes_nothing(tmp_path):
    directory = tmp_path / "inst"
    code, _out, err = invoke(install_args(directory), FakeDocker(docker_ok=False))
    assert code != 0 and "Docker is not available" in err and not directory.exists()


def test_missing_compose_writes_nothing(tmp_path):
    directory = tmp_path / "inst"
    code, _out, err = invoke(install_args(directory), FakeDocker(compose_v2=False))
    assert code != 0 and "Compose v2" in err and not directory.exists()


def test_taken_port_names_the_process_and_a_free_port_is_written(tmp_path):
    blocked = tmp_path / "blocked"
    code, _out, err = invoke(install_args(blocked), FakeDocker(ports={8000: "nginx"}))
    assert code != 0 and "nginx" in err and not blocked.exists()
    free = tmp_path / "free"
    code, _out, _err = invoke(install_args(free, tail=["--port", "9000"]), FakeDocker(ports={8000: "nginx"}))
    assert code == 0 and '"9000:8000"' in (free / "compose.yml").read_text(encoding="utf-8")


def test_low_memory_and_disk_warn_and_still_install(tmp_path):
    docker = FakeDocker(memory=512 * 1024 ** 2, disk=1024 ** 3)
    code, out, _err = invoke(install_args(tmp_path / "inst") + ["--json"], docker)
    warnings = json.loads(out)["warnings"]
    assert code == 0 and any("memory" in item for item in warnings) and any("disk" in item for item in warnings)


def test_sandbox_requires_full(tmp_path):
    directory = tmp_path / "inst"
    code, _out, err = invoke(install_args(directory, tail=["--sandbox"]), FakeDocker())
    assert code != 0 and "--sandbox" in err and not directory.exists()


def test_adopt_writes_the_record_and_does_not_touch_docker(tmp_path):
    compose = tmp_path / "hand"
    compose.mkdir()
    (compose / "compose.yml").write_text("name: hand\nservices: {}\n", encoding="utf-8")
    (compose / ".env").write_text("OLD=1\n", encoding="utf-8")
    docker = FakeDocker()
    code, out, _err = invoke(["adopt", str(compose), "--json"], docker)
    record = json.loads((compose / "instance.json").read_text(encoding="utf-8"))
    assert code == 0 and record["name"] == "hand" and record["remote"] is None
    assert (compose / ".env").read_text(encoding="utf-8") == "OLD=1\n"
    assert docker.calls == []
    assert "admin_password" not in out


def test_start_stop_restart_and_logs(tmp_path):
    directory = tmp_path / "inst"
    assert invoke(install_args(directory), FakeDocker())[0] == 0
    docker = FakeDocker()
    code, _out, err = invoke(["start", "--dir", str(directory)], docker)
    assert code == 0 and "http://localhost:8000" in err
    assert ("compose", "inst", ["up", "-d"]) in docker.calls
    assert ("health", "http://localhost:8000") in docker.calls
    docker.calls.clear()
    assert invoke(["stop", "--dir", str(directory)], docker)[0] == 0
    assert ("compose", "inst", ["stop"]) in docker.calls
    docker.calls.clear()
    assert invoke(["restart", "--dir", str(directory)], docker)[0] == 0
    assert ("compose", "inst", ["restart"]) in docker.calls
    docker.calls.clear()
    code, out, err = invoke(["logs", "api", "--follow", "--dir", str(directory), "--json"], docker)
    assert code == 0 and err == "" and json.loads(out)["ok"] is True
    assert ("compose", "inst", ["logs", "api", "-f"]) in docker.calls


def test_each_new_command_has_help_and_json(tmp_path):
    for command in ("install", "adopt", "start", "stop", "restart", "logs"):
        code, out, err = invoke([command, "--help"], FakeDocker())
        assert code == 0 and out == "" and "Example:" in err
    directory = tmp_path / "inst"
    code, out, err = invoke(install_args(directory) + ["--json"], FakeDocker())
    assert code == 0 and err == "" and json.loads(out)["ok"] is True


def test_answers_file_supplies_url_and_email(tmp_path):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"url": "http://localhost:8000", "admin_email": "you@example.com"}), encoding="utf-8")
    directory = tmp_path / "inst"
    code, _out, _err = invoke(["install", "--yes", "--answers", str(answers), "--dir", str(directory)], FakeDocker())
    assert code == 0 and env_values(directory)["STUDIO_ADMIN_EMAILS"] == "you@example.com"
