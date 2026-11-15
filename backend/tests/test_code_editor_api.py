"""GET /api/meta/runtime and POST /api/code/test (Test with sample state) for the Code mode editor."""
import sys, uuid
import pytest
from fastapi.testclient import TestClient
from app.engine import code_runtime as cr
from app.engine.sandbox import container
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
def admin(): return c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
def editor(): return c.post("/api/auth/register", json={"email": f"ce{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def post_test(tok, **body): return c.post("/api/code/test", json=body, headers=H(tok))


@pytest.fixture
def local(monkeypatch):
    """Sandbox command run with this interpreter (no Docker needed); see test_code_node.py."""
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1")
    monkeypatch.setattr(cr, "unavailable", lambda *_: None)
    monkeypatch.setattr(container, "build_code", lambda **kw: [sys.executable, *kw["command"][1:]])


def test_runtime_describes_the_mode(monkeypatch):
    monkeypatch.delenv("STUDIO_ENABLE_CODE_NODES", raising=False)
    r = c.get("/api/meta/runtime", headers=H(editor())).json()["data"]
    assert r["code_runtime"] == "off" and r["available"] is False and r["problem"] is None
    assert r["packages"] == ["pydantic", "python-dateutil"] and r["limits"]["seconds"] == 30 and "def main(state)" in r["starter"]
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setattr(cr, "unavailable", lambda *_: "Docker is not installed")
    r = c.get("/api/meta/runtime", headers=H(editor())).json()["data"]
    assert r["code_runtime"] == "docker" and r["available"] is False and r["problem"] == "Docker is not installed"
    monkeypatch.setenv("STUDIO_CODE_IMAGE", "mine:2"); monkeypatch.setenv("STUDIO_CODE_PACKAGES", "numpy, pandas")
    assert c.get("/api/meta/runtime", headers=H(editor())).json()["data"]["packages"] == ["numpy", "pandas"]
    assert c.get("/api/meta/runtime").status_code == 401


def test_admin_tests_code_with_a_sample_state(local):
    r = post_test(admin(), source='def main(state):\n    print("n =", len(state["message"]))\n    return state["message"][::-1]', state={"message": "abc"})
    d = r.json()["data"]
    assert r.status_code == 200 and d["ok"] is True and d["value"] == "cba" and d["stdout"] == "n = 3\n" and d["runtime"] == "docker"


def test_a_failing_code_is_a_result_not_an_api_error(local):
    d = post_test(admin(), source="def main(state):\n    return state['missing']", state={}).json()["data"]
    assert d["ok"] is False and d["error"]["code"] == "CODE_FAILED" and "KeyError" in d["error"]["details"]["error"]
    assert 'File "<code>", line 2, in main' in d["traceback"]


def test_bad_source_runtime_off_and_permission_are_errors(local, monkeypatch):
    r = post_test(admin(), source="x = 1", state={})
    assert r.status_code == 400 and r.json()["error"]["code"] == "CODE_INVALID"
    r = post_test(editor(), source="def main(s): return 1", state={})
    assert r.status_code == 403 and r.json()["error"]["code"] == "CODE_WRITE_FORBIDDEN"
    monkeypatch.setattr(cr, "unavailable", lambda *_: "off")
    assert post_test(admin(), source="def main(s): return 1", state={}).json()["error"]["code"] == "CODE_RUNTIME_OFF"


def test_test_runs_are_rate_limited(local, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_TEST_PER_MINUTE", "2")
    tok = admin(); rs = [post_test(tok, source="def main(s): return 1") for _ in range(3)]  # earlier tests in this window count too
    limited = [r for r in rs if r.status_code == 429]
    assert limited and limited[0].json()["error"]["code"] == "RATE_LIMITED" and int(limited[0].headers["Retry-After"]) > 0
