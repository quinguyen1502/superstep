"""deploy over SSH (TASK-0155)."""
import json
from pathlib import Path

import pytest

import superstep
from superstep.cli import run
from superstep.cli.docker import Docker
from superstep.cli.ssh import SshError, SshResult

APP = "ghcr.io/quinguyen1502/superstep"
URL = "ssh://user@host"
REMOTE = "/home/operator/.superstep/instances/superstep"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setattr(superstep, "__version__", "1.2.3")


class FakeSsh:
    def __init__(self, fail=False):
        self.fail = fail
        self.files = {}
        self.commands = []
        self.home_dir = "/home/operator"

    def probe(self):
        self.commands.append(("probe",))
        if self.fail:
            raise SshError("connection refused")

    def home(self):
        self.commands.append(("home",))
        return self.home_dir

    def read(self, path):
        self.commands.append(("read", path))
        item = self.files.get(path)
        return None if item is None else item[0]

    def mkdir(self, path, mode=0o700):
        self.commands.append(("mkdir", path, mode))

    def write(self, path, data, mode=0o600):
        self.commands.append(("write", path, mode))
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files[path] = (data, mode)

    def run(self, argv, stdin=None):
        self.commands.append(("run", tuple(argv)))
        if argv[:2] == ["command", "-v"] or argv[:2] == ["crontab", "-l"]:
            return SshResult(1, b"", b"")
        return SshResult(0, b"", b"")


class FakeDocker:
    def __init__(self):
        self.host = None
        self.calls = []
        self.healthy = True

    def docker_ok(self):
        self.calls.append(("docker",))
        return True

    def compose_v2(self):
        self.calls.append(("compose-v2",))
        return True

    def load(self, tar):
        self.calls.append(("load", tar))

    def pull(self, image):
        self.calls.append(("pull", image))

    def compose(self, directory, project, args):
        self.calls.append(("compose", project, list(args)))

    def wait_healthy(self, url, timeout=60):
        self.calls.append(("wait", url))
        return self.healthy

    def health(self, url):
        self.calls.append(("health", url))
        return {"ok": self.healthy}

    def disk_free_bytes(self, path):
        return 10 ** 12

    def volume_bytes(self, name):
        return 0

    def exec_bytes(self, directory, project, service, command):
        self.calls.append(("exec", service))
        return b"database-bytes"

    def copy_from(self, directory, project, service, path):
        self.calls.append(("copy_from", service, path))
        return b"database-bytes"

    def copy_to(self, directory, project, service, path, data):
        self.calls.append(("copy_to", service, path))

    def compose_logs(self, directory, project):
        return "log\n"


def invoke(argv, docker=None, ssh=None):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker or FakeDocker(), ssh=ssh or FakeSsh())
    return code, out.getvalue(), err.getvalue()


def fresh(**extra):
    args = ["deploy", URL, "--yes", "--url", "http://localhost:8000", "--admin-email", "you@example.com", "--json"]
    for key, value in extra.items():
        args.extend([key, value] if value is not None else [key])
    return args


def env_values(ssh, remote=REMOTE):
    values = {}
    for line in ssh.files[f"{remote}/.env"][0].decode("utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def record(ssh, remote=REMOTE):
    return json.loads(ssh.files[f"{remote}/instance.json"][0].decode("utf-8"))


def command_text(ssh):
    return "\n".join(" ".join(str(part) for part in item) for item in ssh.commands)


def test_fresh_host_installs_over_ssh():
    docker, ssh = FakeDocker(), FakeSsh()
    code, out, err = invoke(fresh(), docker, ssh)
    assert code == 0 and err == ""
    body = json.loads(out)
    saved = record(ssh)
    assert docker.host == URL
    assert body["remote"] == URL and saved["remote"] == URL
    assert saved["dir"] == REMOTE
    assert body["admin_password"] and out.count(body["admin_password"]) == 1
    assert body["admin_password"] not in ssh.files[f"{REMOTE}/instance.json"][0].decode("utf-8")
    assert env_values(ssh)["JWT_SECRET"] not in out
    assert ("pull", f"{APP}:1.2.3") in docker.calls
    assert ("compose", "superstep", ["up", "-d"]) in docker.calls
    assert ssh.files[f"{REMOTE}/.env"][1] == 0o600
    assert ("mkdir", REMOTE, 0o700) in ssh.commands
    text = command_text(ssh)
    for word in ("pip", "pip3", "apt-get", "yum", "dnf"):
        assert word not in text
    assert " uv " not in f" {text} "


def test_second_deploy_upgrades_without_new_secrets(monkeypatch):
    docker, ssh = FakeDocker(), FakeSsh()
    assert invoke(fresh(), docker, ssh)[0] == 0
    first = ssh.files[f"{REMOTE}/.env"][0]
    monkeypatch.setattr(superstep, "__version__", "1.2.4")
    code, out, err = invoke(fresh(), docker, ssh)
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["version"] == "1.2.4" and "admin_password" not in body
    assert ssh.files[f"{REMOTE}/.env"][0] == first
    assert record(ssh)["remote"] == URL
    assert ("pull", f"{APP}:1.2.4") in docker.calls
    assert any(name.startswith("superstep-backup-") for name in (path.rsplit("/", 1)[-1] for path in ssh.files))
    assert env_values(ssh)["JWT_SECRET"] not in out


def test_human_output_prints_the_admin_password_once():
    docker, ssh = FakeDocker(), FakeSsh()
    args = ["deploy", URL, "--yes", "--url", "http://localhost:8000", "--admin-email", "you@example.com"]
    code, out, err = invoke(args, docker, ssh)
    assert code == 0 and out == ""
    password = env_values(ssh)["STUDIO_ADMIN_PASSWORD"]
    assert err.count(password) == 1
    assert env_values(ssh)["JWT_SECRET"] not in err
    assert env_values(ssh)["STUDIO_SECRET_KEY"] not in err


def test_failed_upgrade_keeps_the_previous_secrets(monkeypatch):
    docker, ssh = FakeDocker(), FakeSsh()
    assert invoke(fresh(), docker, ssh)[0] == 0
    first = env_values(ssh)
    docker.healthy = False
    monkeypatch.setattr(superstep, "__version__", "1.2.4")
    code, out, err = invoke(fresh(), docker, ssh)
    assert code != 0 and err == ""
    assert json.loads(out)["error"]["code"] == "ROLLED_BACK"
    assert env_values(ssh)["JWT_SECRET"] == first["JWT_SECRET"]
    assert env_values(ssh)["STUDIO_SECRET_KEY"] == first["STUDIO_SECRET_KEY"]
    assert record(ssh)["version"] == "1.2.3"
    assert record(ssh)["remote"] == URL


def test_upgrade_flag_without_an_instance_writes_nothing():
    docker, ssh = FakeDocker(), FakeSsh()
    code, out, err = invoke(fresh(**{"--upgrade": None}), docker, ssh)
    assert code != 0 and err == ""
    assert json.loads(out)["error"]["code"] == "NO_INSTANCE"
    assert ssh.files == {}
    assert docker.calls == []


def test_images_load_and_do_not_pull(tmp_path):
    docker, ssh = FakeDocker(), FakeSsh()
    tar = tmp_path / "images.tar"
    tar.write_bytes(b"not-a-real-tar")
    code, out, err = invoke(fresh(**{"--images": str(tar)}), docker, ssh)
    assert code == 0 and err == ""
    assert docker.host == URL
    assert ("load", str(tar)) in docker.calls
    assert not any(call[0] == "pull" for call in docker.calls)


def test_schedule_writes_the_remote_script():
    docker, ssh = FakeDocker(), FakeSsh()
    code, out, err = invoke(fresh(**{"--schedule": "daily", "--keep": "7"}), docker, ssh)
    assert code == 0 and err == ""
    script = ssh.files[f"{REMOTE}/backup.sh"][0].decode("utf-8")
    assert "superstep_data" in script and "keep=7" in script
    assert "pip" not in script and "uv" not in script
    assert ssh.files[f"{REMOTE}/backup.sh"][1] == 0o700
    assert json.loads(out)["timer"] == "cron"
    text = command_text(ssh)
    for word in ("pip", "pip3", "apt-get", "yum", "dnf"):
        assert word not in text


def test_ssh_failure_leaves_the_host_empty():
    docker, ssh = FakeDocker(), FakeSsh(fail=True)
    code, out, err = invoke(fresh(), docker, ssh)
    assert code != 0 and err == ""
    assert json.loads(out)["error"]["code"] == "SSH"
    assert ssh.files == {}
    assert docker.calls == []
    docker, ssh = FakeDocker(), FakeSsh()
    code, out, err = invoke(["deploy", "http://example", "--json"], docker, ssh)
    assert code != 0 and ssh.commands == [] and ssh.files == {} and docker.calls == []
    assert json.loads(out)["error"]["code"] == "SSH_TARGET"


def test_dir_overrides_the_remote_home():
    docker, ssh = FakeDocker(), FakeSsh()
    code, _out, err = invoke(fresh(**{"--dir": "/srv/inst"}), docker, ssh)
    assert code == 0 and err == ""
    assert record(ssh, "/srv/inst")["dir"] == "/srv/inst"
    assert record(ssh, "/srv/inst")["remote"] == URL
    assert not any(item[0] == "home" for item in ssh.commands)


def test_help_and_matching_catalog_keys():
    code, out, err = invoke(["deploy", "--help"])
    assert code == 0 and out == "" and "--json" in err and "--upgrade" in err and "--images" in err and "--answers" in err
    assert "Example: superstep deploy ssh://user@host --yes --url http://localhost:8000 --admin-email you@example.com" in err
    code, out, err = invoke(["--lang", "vi", "deploy", "--help"])
    assert code == 0 and "Ví dụ: superstep deploy ssh://user@host --yes --url http://localhost:8000 --admin-email you@example.com" in err
    root = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((root / "vi.json").read_text(encoding="utf-8"))
    assert en.keys() == vi.keys()
    for key in (
        "help.deploy",
        "help.deploy_target",
        "help.force_upgrade",
        "example.deploy",
        "deploy.installed",
        "error.ssh",
        "error.ssh_target",
        "error.no_remote",
    ):
        assert en[key] and vi[key] and en[key] != vi[key]


def test_docker_host_reaches_the_engine(monkeypatch):
    seen = {}

    def fake_run(args, **kwargs):
        seen["args"] = args
        seen["env"] = kwargs.get("env")

        class Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        return Proc()

    monkeypatch.setattr("superstep.cli.docker.subprocess.run", fake_run)
    Docker().pull("example:1")
    assert seen["env"] is None
    Docker(host=URL).load("images.tar")
    assert seen["args"][:3] == ["docker", "load", "-i"]
    assert seen["env"]["DOCKER_HOST"] == URL
