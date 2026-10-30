"""login, logout and whoami (TASK-0167). The browser is never opened."""
import json
import stat
from pathlib import Path

import httpx
import pytest

from superstep.cli import run


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SUPERSTEP_URL", raising=False)
    monkeypatch.delenv("SUPERSTEP_TOKEN", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    opened = []
    monkeypatch.setattr("superstep.cli.login.webbrowser.open", lambda url: opened.append(url))
    return opened


def invoke(argv, client=None):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client)
    return code, out.getvalue(), err.getvalue()


def envelope(data, status=200):
    return httpx.Response(status, json={"success": status < 400, "data": data, "error": None if status < 400 else data})


def test_login_help_and_completion_name_the_commands():
    code, out, err = invoke(["login", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep login --url http://localhost:8000 --no-browser" in err
    code, out, err = invoke(["--lang", "vi", "login", "--help"])
    assert "Ví dụ: superstep login --url http://localhost:8000 --no-browser" in err
    code, out, _err = invoke(["completion", "bash"])
    assert code == 0 and "login" in out and "logout" in out and "whoami" in out


def test_login_stores_the_token_without_printing_it_or_opening_a_browser(tmp_path, isolated_home):
    secret = "pat_hidden-secret"
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.url.path == "/api/auth/cli/devices" and request.method == "POST":
            return envelope({"device_code": "dev", "user_code": "abcd", "verification_uri": "/cli/authorize?code=abcd",
                             "expires_in": 600, "interval": 0})
        if request.url.path == "/api/auth/cli/devices/dev":
            return envelope({"status": "approved", "token": secret})
        if request.url.path == "/api/me":
            return envelope({"email": "ada@example.com"})
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)

    code, out, err = invoke(["login", "--url", "http://studio.example", "--no-browser", "--json"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert code == 0 and isolated_home == []
    assert secret not in out and secret not in err
    assert json.loads(out) == {"ok": True, "account": "ada@example.com", "url": "http://studio.example"}
    assert "http://studio.example/cli/authorize?code=abcd" in err and "abcd" in err
    path = Path.home() / ".superstep" / "cli.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["token"] == secret and saved["account"] == "ada@example.com" and saved["url"] == "http://studio.example"
    assert seen[-1][2] == "Bearer " + secret


def test_env_wins_logout_keeps_lang_and_a_missing_route_names_the_server(monkeypatch, isolated_home):
    path = Path.home() / ".superstep"
    path.mkdir()
    (path / "cli.json").write_text(json.dumps({"lang": "vi", "current": "superstep", "url": "http://file.example", "token": "pat_file", "account": "file@example.com"}), encoding="utf-8")
    monkeypatch.setenv("SUPERSTEP_URL", "http://env.example")
    monkeypatch.setenv("SUPERSTEP_TOKEN", "pat_env")
    seen = []

    def handler(request: httpx.Request):
        seen.append(request.headers.get("authorization"))
        return envelope({"email": "env@example.com"})

    code, out, err = invoke(["whoami", "--json"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert code == 0 and err == "" and seen == ["Bearer pat_env"]
    assert json.loads(out)["account"] == "env@example.com"
    code, out, err = invoke(["logout", "--json"])
    assert code == 0 and json.loads(out) == {"ok": True}
    saved = json.loads((path / "cli.json").read_text(encoding="utf-8"))
    assert saved["lang"] == "vi" and saved["current"] == "superstep" and "token" not in saved and "account" not in saved
    monkeypatch.delenv("SUPERSTEP_TOKEN")
    code, out, err = invoke(["whoami"])
    assert code == 1 and out == "" and "superstep login" in err

    def old(request: httpx.Request):
        if request.url.path == "/api/health":
            return envelope({"version": "0.9.0"})
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)

    code, out, err = invoke(["--lang", "en", "login", "--url", "http://old.example", "--no-browser", "--json"], client=httpx.Client(transport=httpx.MockTransport(old)))
    assert code == 1 and isolated_home == []
    body = json.loads(out)
    assert body["ok"] is False and body["error"]["code"] == "SERVER_TOO_OLD" and "0.9.0" in body["error"]["message"]
