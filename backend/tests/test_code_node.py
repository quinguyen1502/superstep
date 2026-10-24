"""TASK-0053: Tool node Code mode — main(state) runs in a sandbox (Docker), never in the server process."""
import json, os, subprocess, sys, time
import pytest
from app.core.errors import AppError
from app.engine import code_runtime as cr
from app.engine.runtime import run_stream
from app.engine.sandbox import container
from app.engine.validator import validate


def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t): return {"id": i, "source": s, "target": t}
STATE = [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}, {"name": "data", "type": "object"}]
UPPER = 'def main(state):\n    print("got", state["message"])\n    return state["message"].upper()\n'


def wf(code, field="out", **extra):
    return {"name": "c", "state": STATE, "edges": [E("1", "s", "c"), E("2", "c", "e")],
            "nodes": [N("s", "start"), N("c", "tool", mode="code", code=code, output_field=field, **extra), N("e", "end")]}


def runner(source, state=None, limit=65536):
    """The in-sandbox runner, started with this interpreter (protocol only; no isolation)."""
    with open(cr.RUNNER) as fh: src = fh.read()
    p = subprocess.run([sys.executable, "-I", "-c", src], input=json.dumps({"source": source, "state": state or {}, "stdout_max": limit}),
                       capture_output=True, text=True, timeout=30)
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture
def local(monkeypatch):
    """Run the sandbox command with this interpreter instead of Docker, to test run_code without a daemon."""
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1")
    monkeypatch.setattr(cr, "unavailable", lambda *_: None)
    monkeypatch.setattr(container, "build_code", lambda **kw: [sys.executable, *kw["command"][1:]])


docker = pytest.mark.skipif(os.environ.get("STUDIO_TEST_DOCKER") == "0", reason="Docker tests turned off")


@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1")
    cr._checked.clear()
    if (why := cr.unavailable()): pytest.skip(f"Docker sandbox unavailable: {why}")


# ---- parsing and settings (no execution) ----

def test_problems_parse_only():
    assert cr.problems(UPPER) == []
    assert cr.problems("") == ["the code is empty"]
    assert cr.problems("x = 1") == ["define a top-level function main(state)"]
    assert cr.problems("def main(:")[0].startswith("syntax error on line 1")
    assert cr.problems("def main():\n    return 1") == ["main must take the state as its argument: main(state)"]
    assert cr.problems("x" * (cr.SOURCE_MAX + 1))[0].startswith("the code is larger than")
    assert cr.problems('import os\nos.system("touch /tmp/never")\ndef main(s): return 1') == []  # parsed, never run
    assert not os.path.exists("/tmp/never")


def test_runtime_is_off_until_enabled(monkeypatch):
    monkeypatch.delenv("STUDIO_ENABLE_CODE_NODES", raising=False)
    assert cr.unavailable() == "off"
    with pytest.raises(AppError) as e: cr.run_code(UPPER, {"message": "x"})
    assert e.value.code == "CODE_RUNTIME_OFF"
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "gvisor")
    assert cr.unavailable() == "off"  # an unknown runtime is off: never a silent fallback


def test_container_has_no_network_mounts_or_server_env():
    argv = container.build_code(name="lgsx", image="img", command=["python", "-c", "1"], memory="256m", cpus="0.5", pids=64)
    joined = " ".join(argv)
    assert argv[argv.index("--network") + 1] == "none" and "--read-only" in argv and "-v" not in argv and "--env-file" not in argv
    assert "--cap-drop ALL" in joined and "no-new-privileges:true" in joined and "--pids-limit 64" in joined
    envs = [argv[i + 1] for i, a in enumerate(argv) if a == "-e"]
    assert envs == ["HOME=/tmp", "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1"]


def test_validator_reports_code_problems_and_runtime(monkeypatch):
    monkeypatch.delenv("STUDIO_ENABLE_CODE_NODES", raising=False)
    assert "Code nodes are turned off on this server (set STUDIO_ENABLE_CODE_NODES=1)" in validate(wf(UPPER))
    monkeypatch.setattr(cr, "unavailable", lambda *_: None)
    assert validate(wf(UPPER)) == []
    assert "Node c: define a top-level function main(state)" in validate(wf("x = 1"))
    monkeypatch.setattr(cr, "unavailable", lambda *_: "Docker is not installed")
    assert "Code nodes cannot run on this server: Docker is not installed" in validate(wf(UPPER))
    plain = wf(UPPER); plain["nodes"][1]["data"] = {"label": "c", "function": "lookup_order", "output_field": "out"}
    assert validate(plain) == []  # workflows without Code nodes never need Docker


# ---- the runner protocol ----

def test_runner_returns_value_and_stdout():
    r = runner(UPPER, {"message": "hi"})
    assert r == {"ok": True, "value": "HI", "stdout": "got hi\n"}


def test_runner_traceback_shows_only_user_frames():
    r = runner('def helper(x):\n    return 1 / x\n\ndef main(state):\n    return helper(0)\n')
    assert r["ok"] is False and r["kind"] == "failed" and r["error"] == "ZeroDivisionError: division by zero"
    assert 'File "<code>", line 5, in main' in r["traceback"] and "return 1 / x" in r["traceback"] and "code_runner" not in r["traceback"]


def test_runner_not_json_invalid_and_clipped_stdout():
    assert runner("def main(s):\n    return {1, 2}")["kind"] == "not_json"
    assert runner("def main(s):\n    return {1, 2}")["type"] == "set"
    assert runner("x = 1")["kind"] == "invalid"
    assert runner("def main(:")["kind"] == "invalid"
    r = runner('def main(s):\n    print("x" * 5000)\n    return 1', limit=100)
    assert r["value"] == 1 and len(r["stdout"]) < 200 and "more bytes]" in r["stdout"]
    assert runner("import sys\ndef main(s):\n    sys.exit(3)")["error"].startswith("SystemExit")


# ---- run_code and the node, with the sandbox command run locally ----

def test_run_stream_writes_the_value_and_traces_stdout(local):
    events = list(run_stream(wf(UPPER), {"message": "xin chào"}))
    done = next(e for e in events if e["type"] == "node_finished" and e["node"] == "c")
    assert done["delta"] == {"out": "XIN CHÀO"} and done["code_output"]["stdout"] == "got xin chào\n"
    assert done["code_output"]["runtime"] == "docker" and events[-1]["state"]["out"] == "XIN CHÀO"


def test_failures_carry_the_traceback(local):
    err = next(e for e in run_stream(wf('def main(state):\n    raise ValueError("bad input")'), {"message": "x"}) if e["type"] == "error")
    assert err["code"] == "CODE_FAILED" and err["node"] == "c" and "ValueError: bad input" in err["errors"][0]
    assert 'File "<code>", line 2, in main' in err["code_output"]["traceback"]
    err = next(e for e in run_stream(wf("def main(state):\n    return object()"), {"message": "x"}) if e["type"] == "error")
    assert err["code"] == "CODE_RESULT_NOT_JSON"


def test_object_results_and_retry(local, tmp_path):
    out = list(run_stream(wf('def main(state):\n    return {"n": len(state["message"]), "ok": True}', field="data"), {"message": "abc"}))
    assert out[-1]["state"]["data"] == {"n": 3, "ok": True}
    flag = tmp_path / "once"  # fails on the first attempt only; the local runner can see this path
    code = f'import os\ndef main(state):\n    if not os.path.exists({str(flag)!r}):\n        open({str(flag)!r}, "w").close(); raise RuntimeError("first")\n    return "second"'
    out = list(run_stream(wf(code, retry={"max_attempts": 2, "initial_interval": 0.1}), {"message": "x"}))
    assert out[-1]["type"] == "run_finished" and out[-1]["state"]["out"] == "second"


def test_time_limit_and_cancel_stop_the_call(local, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_MAX_SECONDS", "1")
    t = time.monotonic()
    with pytest.raises(AppError) as e: cr.run_code("def main(s):\n    while True: pass", {})
    # the loop never ends on its own, so any bound proves the kill; 15 s leaves room for a loaded CI runner (TASK-0109)
    assert e.value.code == "CODE_TIMEOUT" and time.monotonic() - t < 15
    t = time.monotonic()
    with pytest.raises(AppError) as e: cr.run_code("import time\ndef main(s):\n    time.sleep(20)", {}, timeout=10, cancelled=lambda: time.monotonic() - t > 0.3)
    assert e.value.code == "CODE_FAILED" and "cancelled" in e.value.message and time.monotonic() - t < 5


def test_size_limits(local):
    with pytest.raises(AppError) as e: cr.run_code(UPPER, {"message": "x" * (cr.STATE_MAX + 1)})
    assert e.value.code == "CODE_TOO_LARGE" and e.value.details["what"] == "state"
    with pytest.raises(AppError) as e: cr.run_code('def main(s):\n    return "x" * (2 * 1024 * 1024)', {})
    assert e.value.code == "CODE_TOO_LARGE" and e.value.details["what"] == "result"


# ---- the real sandbox (skips without Docker and the studio-code image) ----

@docker
def test_docker_runs_the_code(sandbox):
    r = cr.run_code('import dateutil, pydantic\n' + UPPER, {"message": "hi"})
    assert r.value == "HI" and r.stdout == "got hi\n" and r.runtime == "docker"


@docker
def test_docker_hides_server_env_files_and_network(sandbox, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "server-only-secret")
    code = ('import os, socket\ndef main(state):\n    try:\n        socket.create_connection(("1.1.1.1", 53), timeout=2); net = True\n'
            '    except OSError:\n        net = False\n'
            '    return {"env": sorted(k for k in os.environ if k.startswith(("JWT", "STUDIO", "DATABASE"))), "net": net,\n'
            '            "app": os.path.exists("/app") or os.path.exists(' + repr(os.getcwd()) + ')}')
    assert cr.run_code(code, {}).value == {"env": [], "net": False, "app": False}


@docker
def test_docker_time_and_memory_limits(sandbox, monkeypatch):
    with pytest.raises(AppError) as e: cr.run_code("def main(s):\n    while True: pass", {}, timeout=2)
    assert e.value.code == "CODE_TIMEOUT"
    monkeypatch.setenv("STUDIO_CODE_MEMORY", "64m")
    with pytest.raises(AppError) as e: cr.run_code("def main(s):\n    b = bytearray(200 * 1024 * 1024)\n    return len(b)", {})
    assert e.value.code in ("CODE_MEMORY", "CODE_FAILED")  # killed by the OOM killer, or MemoryError inside Python
