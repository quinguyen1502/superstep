"""CLI parser, catalogs, JSON output, and the server version comparison (TASK-0149)."""
import json
from pathlib import Path

import httpx
import pytest

import superstep
from superstep.cli import run
from superstep.cli.i18n import Catalog

ROOT = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"
SECRET = "jwt-secret-should-not-appear"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)


def invoke(argv, client=None):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client)
    return code, out.getvalue(), err.getvalue()


def transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def health(data, status=200):
    def handler(_request):
        return httpx.Response(status, json={"success": True, "data": data, "error": None})
    return transport(handler)


def test_catalogs_have_the_same_keys():
    en = json.loads((ROOT / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((ROOT / "vi.json").read_text(encoding="utf-8"))
    assert set(en) == set(vi)
    assert all(isinstance(value, str) and value for value in list(en.values()) + list(vi.values()))


def test_help_shows_an_example_on_stderr():
    code, out, err = invoke(["--help"])
    assert code == 0 and out == ""
    assert "Example: superstep version" in err
    code, out, err = invoke(["version", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep version --url http://localhost:8000" in err


def test_help_follows_lang():
    _code, _out, err = invoke(["--lang", "vi", "--help"])
    assert "Ví dụ: superstep version" in err


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_mentions_version(shell):
    code, out, err = invoke(["completion", shell])
    assert code == 0 and err == "" and "version" in out


def test_completion_json_is_one_object():
    code, out, err = invoke(["completion", "bash", "--json"])
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["ok"] is True and body["shell"] == "bash" and "version" in body["script"]


def test_version_json_without_a_server(monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "0.1.0")

    def refuse(_request):
        raise AssertionError("version without --url must not call the server")

    code, out, err = invoke(["version", "--json"], client=transport(refuse))
    assert code == 0 and err == ""
    assert json.loads(out) == {"ok": True, "cli_version": "0.1.0", "server_version": None, "warning": None}


def test_json_flag_works_before_or_after_the_command(monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "0.9.0")
    client = health({"ok": True, "version": "0.9.1", "secret": SECRET})
    for argv in (["--json", "version", "--url", "http://studio.test"], ["version", "--url", "http://studio.test", "--json"]):
        code, out, err = invoke(argv, client=client)
        body = json.loads(out)
        assert code == 0 and err == "" and body["warning"] is None and body["server_version"] == "0.9.1"
        assert SECRET not in out


def test_missing_server_version_warns_and_exits_zero(monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "0.9.0")
    code, out, _err = invoke(["--json", "version", "--url", "http://studio.test"], client=health({"ok": True, "secret": SECRET}))
    body = json.loads(out)
    assert code == 0 and body["server_version"] is None
    assert body["warning"] == "The server did not report a version."
    assert SECRET not in out


def test_minor_mismatch_warns_in_the_selected_language(monkeypatch):
    monkeypatch.setattr(superstep, "__version__", "0.1.0")
    client = health({"ok": True, "version": "0.9.0", "secret": SECRET})
    code, out, err = invoke(["--lang", "vi", "--json", "version", "--url", "http://studio.test"], client=client)
    body = json.loads(out)
    assert code == 0 and err == "" and body["ok"] is True
    assert body["warning"] == "CLI là 0.1.0 và máy chủ là 0.9.0."
    assert SECRET not in out
    code, out, err = invoke(["version", "--url", "http://studio.test"], client=client)
    assert code == 0 and out == "" and "CLI 0.1.0" in err and "Server 0.9.0" in err and SECRET not in err


def test_lang_flag_beats_the_environment_and_the_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "vi_VN.UTF-8")
    folder = tmp_path / ".superstep"
    folder.mkdir()
    (folder / "cli.json").write_text(json.dumps({"lang": "vi"}), encoding="utf-8")
    monkeypatch.setattr(superstep, "__version__", "0.9.0")
    code, out, _err = invoke(["--lang", "en", "version", "--json", "--url", "http://studio.test"], client=health({"ok": True}))
    assert code == 0 and json.loads(out)["warning"] == "The server did not report a version."


def test_file_lang_beats_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    folder = tmp_path / ".superstep"
    folder.mkdir()
    (folder / "cli.json").write_text(json.dumps({"lang": "vi"}), encoding="utf-8")
    monkeypatch.setattr(superstep, "__version__", "0.9.0")
    code, out, _err = invoke(["version", "--url", "http://studio.test", "--json"], client=health({"ok": True}))
    assert code == 0 and json.loads(out)["warning"] == "Máy chủ không trả phiên bản."


def test_lang_environment_selects_vietnamese(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "vi_VN.UTF-8")
    monkeypatch.setattr(superstep, "__version__", "0.9.0")
    code, out, _err = invoke(["version", "--url", "http://studio.test", "--json"], client=health({"ok": True}))
    assert code == 0 and json.loads(out)["warning"] == "Máy chủ không trả phiên bản."


def test_connection_failure_is_json_in_the_selected_language():
    def boom(_request):
        raise httpx.ConnectError("down")
    code, out, err = invoke(["--lang", "vi", "--json", "version", "--url", "http://studio.test"], client=transport(boom))
    body = json.loads(out)
    assert code == 1 and err == ""
    assert body == {"ok": False, "error": {"code": "CONNECTION_FAILED", "message": "Không kết nối được tới máy chủ tại http://studio.test."}}


def test_bad_health_is_an_error():
    code, out, err = invoke(["version", "--url", "http://studio.test"], client=transport(lambda _r: httpx.Response(500, text="nope")))
    assert code == 1 and out == "" and "did not return a health envelope" in err


def test_usage_json_is_one_object():
    code, out, err = invoke(["--json", "nope"])
    body = json.loads(out)
    assert code == 2 and err == "" and body["ok"] is False and body["error"]["code"] == "USAGE"
    assert "Đối số" not in body["error"]["message"] and body["error"]["message"]


def test_messages_round_trip():
    assert Catalog.load("en").format("version.cli", version="1") == "CLI 1"
    assert Catalog.load("vi").format("version.server", version="1") == "Máy chủ 1"
