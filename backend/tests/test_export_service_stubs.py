"""exported Studio-service stubs and missing targets never fake success.

Each generated file is executed: Python in a fresh interpreter, TypeScript with Deno (skips without it).
Offline example mode (no LLM_PROVIDER) keeps the studio's mock results and says so on stderr; with LLM_PROVIDER set
the unimplemented service stops the run. A subgraph/workflow tool missing at export time fails when reached."""
import os, subprocess, sys, uuid
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

SERVICES = {"name": "Services", "state": [F("message"), F("hits", "list"), F("tool", "object"), F("mail", "object")],
            "nodes": [N("start", "start"), N("r", "retriever", query="{{state.message}}", top_k=2, output_field="hits"),
                      N("m", "mcp", tool="lookup", arguments={"q": "{{state.message}}"}, output_field="tool"),
                      N("mail", "email", to="a@example.com", cc="", bcc="", subject="Hi", body="{{state.message}}", output_field="mail"),
                      N("end", "end")],
            "edges": [E("start", "r"), E("r", "m"), E("m", "mail"), E("mail", "end")]}
MISSING = {"name": "Missing", "state": [F("message")],
           "nodes": [N("start", "start"), N("child", "subgraph", workflow_id="gone1"), N("end", "end")],
           "edges": [E("start", "child"), E("child", "end")]}
EXAMPLE = {"input": {"message": "order A100"}}


def env(live):
    out = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    if live: out["LLM_PROVIDER"] = "openai"  # no key: nothing may reach a provider before the service check
    return out


def py(tmp_path, wf, live):
    f = tmp_path / f"wf_{uuid.uuid4().hex[:6]}.py"; f.write_text(X.to_python(wf, wf["name"], 1, {}, EXAMPLE).code)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env(live), capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def ts(tmp_path, base, wf, live):
    f = tmp_path / f"wf_{uuid.uuid4().hex[:6]}.ts"; f.write_text(T.to_typescript(wf, wf["name"], 1, {}, EXAMPLE).code)
    e = {k: v for k, v in base.items() if k != "LLM_PROVIDER"}
    if live: e["LLM_PROVIDER"] = "openai"
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys=homedir", str(f)], cwd=tmp_path, env=e,
                          capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


def test_python_offline_mock_is_announced(tmp_path):
    p = py(tmp_path, SERVICES, live=False)
    assert p.returncode == 0, p.stderr[-2000:]
    for kind in ("Knowledge base search", "MCP tool", "Send email"): assert f"(offline mock) {kind}" in p.stderr
    assert "(e-mail not sent)" in p.stdout and "Final state:" in p.stdout


def test_python_live_run_refuses_unimplemented_services(tmp_path):
    p = py(tmp_path, SERVICES, live=True)
    # the first service reached is the Retriever: unconfigured in a live run it names what to set
    assert p.returncode != 0 and "Knowledge base search KNOWLEDGE_BASE_1: set SUPERSTEP_URL" in p.stderr
    assert "(e-mail not sent)" not in p.stdout and "Final state:" not in p.stdout


def test_python_missing_subgraph_fails_when_reached(tmp_path):
    code = X.to_python(MISSING, "Missing", 1, {}, EXAMPLE).code
    assert "StateGraph(dict).compile()" not in code
    p = py(tmp_path, MISSING, live=False)
    assert p.returncode != 0 and "LookupError" in p.stderr and "gone1" in p.stderr


def test_typescript_offline_mock_is_announced(tmp_path, deno_env):  # noqa: F811
    p = ts(tmp_path, deno_env, SERVICES, live=False)
    assert p.returncode == 0, p.stderr[-2000:]
    for kind in ("Knowledge base search", "MCP tool", "Send email"): assert f"(offline mock) {kind}" in p.stderr
    assert "Final state:" in p.stdout


def test_typescript_live_run_refuses_unimplemented_services(tmp_path, deno_env):  # noqa: F811
    p = ts(tmp_path, deno_env, SERVICES, live=True)
    assert p.returncode != 0 and "Knowledge base search KNOWLEDGE_BASE_1: set SUPERSTEP_URL" in p.stderr
    assert "Final state:" not in p.stdout


def test_typescript_missing_subgraph_fails_when_reached(tmp_path, deno_env):  # noqa: F811
    code = T.to_typescript(MISSING, "Missing", 1, {}, EXAMPLE).code
    assert "TODO: the subgraph was not found" not in code
    p = ts(tmp_path, deno_env, MISSING, live=False)
    assert p.returncode != 0 and "gone1" in p.stderr
