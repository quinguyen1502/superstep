"""upgrade with a backup and automatic rollback (TASK-0153)."""
import json
from pathlib import Path

import pytest

import superstep
from superstep.cli import run
from superstep.cli.upgrade import _changelog_text as read_changelog

SECRET = "superstep-secret-value"
APP = "ghcr.io/quinguyen1502/superstep"
NOTES = "## 1.2.4\n\nShipped the gate.\n"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setattr("superstep.cli.upgrade._changelog_text", lambda: NOTES)


class UpgradeDocker:
    def __init__(self, wait=True, ok=True, logs="fake-upgrade-log"):
        self.wait = wait
        self.ok = ok
        self.log_text = logs
        self.calls = []

    def disk_free_bytes(self, path):
        return 10 ** 12

    def volume_bytes(self, name):
        return 0

    def exec_bytes(self, directory, project, service, command):
        self.calls.append(("exec", service, tuple(command)))
        return b"database-bytes"

    def copy_from(self, directory, project, service, path):
        self.calls.append(("copy_from", service, path))
        return b"database-bytes"

    def copy_to(self, directory, project, service, path, data):
        self.calls.append(("copy_to", service, path))

    def compose(self, directory, project, args):
        self.calls.append(("compose", project, tuple(args)))

    def compose_logs(self, directory, project):
        self.calls.append(("logs", project))
        return self.log_text

    def pull(self, image):
        self.calls.append(("pull", image))

    def load(self, tar):
        self.calls.append(("load", tar))

    def wait_healthy(self, url, timeout=60):
        self.calls.append(("wait", url))
        return self.wait

    def health(self, url):
        self.calls.append(("health", url))
        return {"ok": self.ok}


def invoke(argv, docker):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker)
    return code, out.getvalue(), err.getvalue()


def layout(tmp_path, topology="single", volumes=None, compose_name="inst", version="1.2.3"):
    directory = tmp_path / "inst"
    directory.mkdir(parents=True)
    env = f"JWT_SECRET=abc\nSTUDIO_SECRET_KEY={SECRET}\nSTUDIO_ENV=production\n"
    if topology == "full":
        env += "POSTGRES_PASSWORD=pg-secret\n"
        volumes = volumes or {"pgdata": "inst_pg", "redisdata": "inst_redis", "apidata": "inst_api"}
        image = "ghcr.io/quinguyen1502/superstep-api"
    else:
        volumes = volumes or {"data": "inst_data"}
        image = APP
    compose = f"name: {compose_name}\nservices:\n  superstep:\n    image: {image}:{version}\n"
    (directory / ".env").write_text(env, encoding="utf-8")
    (directory / "compose.yml").write_text(compose, encoding="utf-8")
    record = {
        "name": "inst",
        "topology": topology,
        "sandbox": False,
        "version": version,
        "public_url": "http://localhost:8000",
        "dir": str(directory),
        "remote": None,
        "volumes": volumes,
    }
    (directory / "instance.json").write_text(json.dumps(record), encoding="utf-8")
    return directory


def saved(directory):
    return json.loads((directory / "instance.json").read_text(encoding="utf-8"))


def test_upgrade_to_a_newer_tag_backs_up_pulls_and_restarts(tmp_path):
    directory = layout(tmp_path)
    docker = UpgradeDocker()
    code, out, err = invoke(
        ["upgrade", "--dir", str(directory), "--to", "1.2.4", "--json"],
        docker,
    )
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["ok"] is True and body["version"] == "1.2.4"
    assert body["archive"].endswith(".tar.gz") and Path(body["archive"]).is_file()
    assert "Shipped the gate." in body["changelog"]
    assert saved(directory)["version"] == "1.2.4"
    assert f"{APP}:1.2.4" in (directory / "compose.yml").read_text(encoding="utf-8")
    kinds = [call[0] for call in docker.calls]
    assert kinds.index("exec") < kinds.index("pull")
    assert kinds.index("pull") < kinds.index("compose")
    assert kinds.index("compose") < kinds.index("wait")
    assert ("pull", f"{APP}:1.2.4") in docker.calls
    assert ("health", "http://localhost:8000") in docker.calls


def test_missing_changelog_range_still_upgrades(tmp_path, monkeypatch):
    monkeypatch.setattr("superstep.cli.upgrade._changelog_text", lambda: "## 0.9.0\n\nOlder.\n")
    directory = layout(tmp_path)
    docker = UpgradeDocker()
    code, out, err = invoke(["upgrade", "--dir", str(directory), "--to", "1.2.4"], docker)
    assert code == 0 and out == ""
    assert "The bundled changelog has no entry for this range." in err
    assert "Upgraded to 1.2.4." in err
    assert saved(directory)["version"] == "1.2.4"


@pytest.mark.parametrize("mode", ["timeout", "not_ok"])
def test_failed_health_restores_the_previous_tag(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(superstep, "__version__", "1.2.4")
    directory = layout(tmp_path)
    docker = UpgradeDocker(wait=mode != "timeout", ok=mode != "not_ok")
    code, out, err = invoke(
        ["--json", "upgrade", "--dir", str(directory), "--to", "1.2.4"],
        docker,
    )
    assert code != 0 and out
    body = json.loads(out)
    assert body["ok"] is False and body["error"]["code"] == "ROLLED_BACK"
    assert saved(directory)["version"] == "1.2.3"
    compose = (directory / "compose.yml").read_text(encoding="utf-8")
    assert f"{APP}:1.2.3" in compose and f"{APP}:1.2.4" not in compose
    logs = list(directory.glob("upgrade-failed-*.log"))
    assert len(logs) == 1 and "fake-upgrade-log" in logs[0].read_text(encoding="utf-8")
    assert str(logs[0]) in body["error"]["message"]
    log_at = next(index for index, call in enumerate(docker.calls) if call[0] == "logs")
    assert any(call[0] == "compose" and call[2] == ("up", "-d") for call in docker.calls[log_at + 1:])


def test_check_prints_the_difference_and_changes_nothing(tmp_path):
    directory = layout(tmp_path)
    before = (directory / "instance.json").read_text(encoding="utf-8")
    docker = UpgradeDocker()
    code, out, err = invoke(
        ["upgrade", "--check", "--dir", str(directory), "--to", "1.2.4", "--json"],
        docker,
    )
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body == {
        "ok": True,
        "current": "1.2.3",
        "target": "1.2.4",
        "differs": True,
        "changelog": "## 1.2.4\n\nShipped the gate.",
    }
    assert docker.calls == []
    assert (directory / "instance.json").read_text(encoding="utf-8") == before


def test_images_loads_and_does_not_pull(tmp_path):
    directory = layout(tmp_path)
    docker = UpgradeDocker()
    tar = str(tmp_path / "images.tar")
    code, out, _err = invoke(
        ["upgrade", "--dir", str(directory), "--to", "1.2.4", "--images", tar, "--json"],
        docker,
    )
    assert code == 0
    assert ("load", tar) in docker.calls
    assert not any(call[0] == "pull" for call in docker.calls)
    assert json.loads(out)["version"] == "1.2.4"


def test_v01_volume_stops_without_delete_and_is_external(tmp_path):
    volumes = {"pgdata": "langgraph-studio_pgdata", "redisdata": "inst_redis", "apidata": "inst_api"}
    directory = layout(tmp_path, topology="full", volumes=volumes, compose_name="langgraph-studio")
    docker = UpgradeDocker()
    code, _out, _err = invoke(
        ["upgrade", "--dir", str(directory), "--to", "1.2.4", "--json"],
        docker,
    )
    assert code == 0
    assert ("compose", "langgraph-studio", ("down",)) in docker.calls
    assert all("-v" not in call[2] for call in docker.calls if call[0] == "compose")
    text = (directory / "compose.yml").read_text(encoding="utf-8")
    assert "name: langgraph-studio_pgdata\n    external: true\n" in text
    assert "name: inst_redis\n    external: true\n" not in text
    kinds = [call[0] for call in docker.calls]
    assert kinds.index("pull") < kinds.index("compose")


def test_older_target_exits_before_backup(tmp_path):
    directory = layout(tmp_path)
    before = sorted(path.name for path in directory.iterdir())
    docker = UpgradeDocker()
    code, out, _err = invoke(
        ["upgrade", "--dir", str(directory), "--to", "1.0.0", "--json"],
        docker,
    )
    assert code != 0
    body = json.loads(out)
    assert body["ok"] is False and body["error"]["code"] == "DOWNGRADE"
    assert docker.calls == []
    assert sorted(path.name for path in directory.iterdir()) == before
    assert saved(directory)["version"] == "1.2.3"


def test_changelog_reader_finds_the_repo_log():
    assert "## 0.9.0" in read_changelog()


def test_help_and_matching_catalog_keys():
    code, out, err = invoke(["upgrade", "--help"], UpgradeDocker())
    assert code == 0 and out == ""
    assert "--json" in err and "--check" in err
    assert "Example: superstep upgrade --to 0.9.0" in err
    code, out, err = invoke(["--lang", "vi", "upgrade", "--help"], UpgradeDocker())
    assert code == 0 and "Ví dụ: superstep upgrade --to 0.9.0" in err
    root = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((root / "vi.json").read_text(encoding="utf-8"))
    assert en.keys() == vi.keys()
    for key in (
        "help.upgrade",
        "help.to_version",
        "help.check",
        "example.upgrade",
        "upgrade.check",
        "upgrade.changelog_missing",
        "upgrade.current",
        "upgrade.done",
        "error.downgrade",
        "error.rolled_back",
    ):
        assert en[key] and vi[key] and en[key] != vi[key]
