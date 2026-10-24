"""TASK-0056: the host subprocess runtime for Code nodes (no Docker), and how it is made visible."""
import logging, os, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.engine import code_runtime as cr
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.main import app
from app.services.run_service import code_runtime_of

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
UPPER = 'def main(state):\n    print("got", state["message"])\n    return state["message"].upper()\n'


def wf(code):
    return {"name": f"sp-{uuid.uuid4().hex[:6]}", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "edges": [{"id": "1", "source": "s", "target": "c"}, {"id": "2", "source": "c", "target": "e"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "c", "type": "tool", "position": {"x": 1, "y": 0}, "data": {"label": "c", "mode": "code", "code": code, "output_field": "out"}},
                      {"id": "e", "type": "end", "position": {"x": 2, "y": 0}, "data": {"label": "e"}}]}


@pytest.fixture
def host(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    monkeypatch.setattr(cr, "_announced", False)


def test_subprocess_runs_without_docker(host, monkeypatch):
    monkeypatch.setattr(cr.container, "docker_exe", lambda: "/nonexistent/docker")
    assert cr.unavailable() is None
    r = cr.run_code(UPPER, {"message": "hi"})
    assert r.value == "HI" and r.stdout == "got hi\n" and r.runtime == "subprocess"


def test_subprocess_gets_no_server_environment_and_its_own_folder(host, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "server-only-secret"); monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    code = ('import os\ndef main(state):\n    return {"env": sorted(k for k in os.environ if k.startswith(("JWT", "STUDIO", "DATABASE"))),\n'
            '            "cwd": os.getcwd(), "home": os.path.realpath(os.environ["HOME"])}')
    v = cr.run_code(code, {}).value
    assert v["env"] == [] and "lgs-code-" in v["cwd"] and v["home"] == v["cwd"]
    assert not os.path.exists(v["cwd"])  # the folder is removed afterwards


def test_timeout_kills_the_whole_process_group(host, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_MAX_SECONDS", "1")
    pidfile = tmp_path / "child.pid"
    code = (f'import subprocess, time\ndef main(state):\n    p = subprocess.Popen(["sleep", "30"])\n'
            f'    open({str(pidfile)!r}, "w").write(str(p.pid))\n    time.sleep(30)')
    t = time.monotonic()
    with pytest.raises(AppError) as e: cr.run_code(code, {})
    if e.value.code == "CODE_FAILED" and "BlockingIOError" in (e.value.output or {}).get("traceback", ""):
        # the runner caps RLIMIT_NPROC, which counts every process of this user: on a busy shared host the cap is
        # already reached, so the code cannot fork its grandchild and there is nothing to test (TASK-0109)
        pytest.skip("process limit reached: the sandboxed code cannot fork on this host (RLIMIT_NPROC counts all user processes)")
    assert e.value.code == "CODE_TIMEOUT" and e.value.output["runtime"] == "subprocess" and time.monotonic() - t < 6
    pid = int(pidfile.read_text()); time.sleep(0.3)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # the grandchild died with the group


def test_failures_and_trace_carry_the_runtime(host):
    events = list(run_stream(wf(UPPER), {"message": "x"}))
    done = next(e for e in events if e["type"] == "node_finished" and e["node"] == "c")
    assert done["code_output"]["runtime"] == "subprocess" and code_runtime_of(events) == "subprocess"
    err = next(e for e in run_stream(wf("def main(s):\n    raise RuntimeError('boom')"), {"message": "x"}) if e["type"] == "error")
    assert err["code"] == "CODE_FAILED" and err["code_output"]["runtime"] == "subprocess"
    assert code_runtime_of([{"code_output": {"runtime": "docker"}}]) == "docker" and code_runtime_of([{"type": "run_started"}]) is None


def test_first_unisolated_call_is_announced_once(host):
    calls = []
    ports = Ports(code_audit=lambda: calls.append(1))
    for _ in range(2): list(run_stream(wf(UPPER), {"message": "x"}, ports=ports))
    assert calls == [1]


def test_start_up_warning(host, caplog):
    with caplog.at_level(logging.WARNING): cr.warn_if_unisolated()
    assert any("WITHOUT Docker limiting" in r.getMessage() for r in caplog.records)


def test_no_silent_fallback_from_docker(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.delenv("STUDIO_CODE_RUNTIME", raising=False)
    cr._checked.clear(); monkeypatch.setattr(cr.container, "docker_exe", lambda: "/nonexistent/docker")
    assert cr.unavailable() == "Docker is not installed"
    with pytest.raises(AppError) as e: cr.run_code(UPPER, {"message": "x"})
    assert e.value.code == "CODE_RUNTIME_UNAVAILABLE"
    cr._checked.clear()


def test_api_run_history_audit_and_runtime(host):
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    assert c.get("/api/meta/runtime", headers=H(tok)).json()["data"]["code_runtime"] == "subprocess"
    wid = c.post("/api/workflows", json=wf(UPPER), headers=H(tok)).json()["data"]["id"]
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": {"message": "hi"}})
        while ws.receive_json()["type"] not in ("run_finished", "error"): pass
    for _ in range(50):  # the run row is written right after the last event
        hist = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
        if hist: break
        time.sleep(0.05)
    assert hist[0]["code_runtime"] == "subprocess" and hist[0]["final_state"]["out"] == "HI"
    audit = c.get("/api/admin/audit", params={"q": "code_runtime"}, headers=H(tok)).json()["data"]["items"]
    assert any(x["action"] == "system.code_runtime_subprocess" for x in audit)
