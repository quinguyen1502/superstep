"""admin and uninstall (TASK-0154)."""
import io
import json
from pathlib import Path

import pytest

from superstep.cli import run

SECRET = "superstep-secret-value"
PASSWORD = "Correct-horse-42"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)


class AdminDocker:
    def __init__(self, stdout=b"Correct-horse-42\n"):
        self.stdout = stdout
        self.calls = []

    def exec_bytes(self, directory, project, service, command, stdin=None):
        self.calls.append(("exec", project, service, tuple(command)))
        self.stdin = stdin
        return self.stdout

    def compose(self, directory, project, args):
        self.calls.append(("compose", project, tuple(args)))

    def remove_volume(self, name):
        self.calls.append(("volume", name))


def invoke(argv, docker):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, docker=docker)
    return code, out.getvalue(), err.getvalue()


def layout(tmp_path, topology="single"):
    directory = tmp_path / "inst"
    directory.mkdir()
    (directory / ".env").write_text(f"STUDIO_SECRET_KEY={SECRET}\n", encoding="utf-8")
    (directory / "compose.yml").write_text("name: inst\nservices: {}\n", encoding="utf-8")
    volumes = {"pgdata": "inst_pg", "redisdata": "inst_redis", "apidata": "inst_api"} if topology == "full" else {"data": "inst_data"}
    record = {
        "name": "inst",
        "topology": topology,
        "version": "0.1.0",
        "dir": str(directory),
        "volumes": volumes,
    }
    (directory / "instance.json").write_text(json.dumps(record), encoding="utf-8")
    return directory


def test_create_shows_the_exec_password_once_and_leaves_instance_json(tmp_path, monkeypatch):
    directory = layout(tmp_path)
    before = (directory / "instance.json").read_text(encoding="utf-8")
    docker = AdminDocker()
    code, out, err = invoke(
        ["admin", "create", "--email", "you@example.com", "--dir", str(directory), "--json"],
        docker,
    )
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["ok"] is True and body["password"] == PASSWORD and body["email"] == "you@example.com"
    assert out.count(PASSWORD) == 1
    assert (directory / "instance.json").read_text(encoding="utf-8") == before
    assert PASSWORD not in before
    assert not (Path.home() / ".superstep" / "cli.json").exists()
    assert docker.calls == [(
        "exec",
        "inst",
        "superstep",
        ("python", "-m", "app.admin_cmd", "create", "--email", "you@example.com"),
    )]
    assert docker.stdin is None
    docker.calls.clear()
    monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    code, out, err = invoke(
        ["admin", "reset-password", "--email", "you@example.com", "--password-stdin", "--dir", str(directory), "--json"],
        docker,
    )
    assert code == 0 and err == ""
    argv = docker.calls[0][3]
    assert "--password" not in argv and PASSWORD not in argv
    assert argv[-1] == "--password-stdin"
    assert docker.stdin == (PASSWORD + "\n").encode("utf-8")
    code, out, err = invoke(
        ["admin", "create", "--email", "you@example.com", "--dir", str(directory)],
        docker,
    )
    assert code == 0 and out == "" and err.count(PASSWORD) == 1


def test_full_topology_execs_the_api_service(tmp_path):
    directory = layout(tmp_path, topology="full")
    docker = AdminDocker()
    code, _out, _err = invoke(
        ["admin", "reset-password", "--email", "you@example.com", "--dir", str(directory), "--json"],
        docker,
    )
    assert code == 0
    assert docker.calls[0][2] == "api"
    assert docker.calls[0][3][:4] == ("python", "-m", "app.admin_cmd", "reset-password")


def test_list_json_has_email_and_role_and_no_password(tmp_path):
    directory = layout(tmp_path)
    docker = AdminDocker(stdout=b"you@example.com\tadmin\n")
    code, out, err = invoke(["admin", "list", "--dir", str(directory), "--json"], docker)
    assert code == 0 and err == ""
    body = json.loads(out)
    assert "password" not in body
    assert body["admins"] == [{"email": "you@example.com", "role": "admin"}]
    assert "pbkdf2" not in out
    code, out, err = invoke(["admin", "list", "--dir", str(directory)], docker)
    assert code == 0 and out == "" and err == "you@example.com admin\n"
    assert "pbkdf2" not in err


def test_a_hash_on_stdout_is_not_shown(tmp_path):
    directory = layout(tmp_path)
    docker = AdminDocker(stdout=b"pbkdf2_sha256$1$salt$hash\n")
    code, out, err = invoke(
        ["admin", "create", "--email", "you@example.com", "--dir", str(directory), "--json"],
        docker,
    )
    assert code != 0
    assert "pbkdf2" not in out and "pbkdf2" not in err


def test_uninstall_keeps_volumes_and_the_directory(tmp_path):
    directory = layout(tmp_path)
    docker = AdminDocker()
    code, out, err = invoke(["uninstall", "--dir", str(directory), "--json"], docker)
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["purged"] is False and body["name"] == "inst"
    assert docker.calls == [("compose", "inst", ("down",))]
    assert SECRET not in out
    assert SECRET in (directory / ".env").read_text(encoding="utf-8")
    assert (directory / "instance.json").is_file()


def test_purge_without_the_name_removes_nothing(tmp_path, monkeypatch):
    directory = layout(tmp_path)
    docker = AdminDocker()
    monkeypatch.setattr("builtins.input", lambda *_args: "nope")
    code, out, _err = invoke(["uninstall", "--purge", "--dir", str(directory), "--json"], docker)
    assert code != 0 and json.loads(out)["error"]["code"] == "CONFIRM"
    assert docker.calls == []
    assert (directory / ".env").is_file()
    code, out, _err = invoke(["uninstall", "--purge", "--yes", "--dir", str(directory), "--json"], docker)
    assert code != 0 and json.loads(out)["error"]["code"] == "CONFIRM"
    assert docker.calls == []
    assert (directory / "instance.json").is_file()


def test_purge_with_the_name_removes_volumes_and_the_directory(tmp_path):
    directory = layout(tmp_path)
    docker = AdminDocker()
    code, out, err = invoke(
        ["uninstall", "--purge", "--yes", "--name", "inst", "--dir", str(directory), "--json"],
        docker,
    )
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["purged"] is True and SECRET not in out
    assert ("compose", "inst", ("down", "-v")) in docker.calls
    assert ("volume", "inst_data") in docker.calls
    assert not directory.exists()


def test_help_and_matching_catalog_keys():
    code, out, err = invoke(["admin", "--help"], AdminDocker())
    assert code == 0 and out == "" and "--json" in err
    assert "Example: superstep admin create --email you@example.com" in err
    code, out, err = invoke(["admin", "create", "--help"], AdminDocker())
    assert code == 0 and out == "" and "--email" in err and "--password" in err
    code, out, err = invoke(["--lang", "vi", "uninstall", "--help"], AdminDocker())
    assert code == 0 and "Ví dụ: superstep uninstall --purge --yes --name superstep" in err
    root = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((root / "vi.json").read_text(encoding="utf-8"))
    assert en.keys() == vi.keys()
    for key in (
        "help.admin",
        "help.admin_create",
        "help.admin_reset",
        "help.admin_list",
        "help.account_email",
        "help.admin_password",
        "help.uninstall",
        "help.purge",
        "example.admin",
        "example.admin_reset",
        "example.admin_list",
        "example.uninstall",
        "admin.created",
        "admin.reset",
        "uninstall.kept",
        "uninstall.purged",
        "prompt.uninstall",
        "error.uninstall_name",
        "error.admin_output",
    ):
        assert en[key] and vi[key] and en[key] != vi[key]
    assert en["admin.row"] == vi["admin.row"] == "{email} {role}"
