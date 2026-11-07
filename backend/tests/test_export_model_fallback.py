"""TASK-0264 (REQ-0088, DEC-0087): LLM model fallback in exported code, executed in Python and TypeScript (Deno).

The provider call is replaced by a local fake (no network, no paid call): the primary model fails with a status or a
connection error, and the generated fallback logic must follow the studio's rules: fail over on unreachable / 5xx / 404,
once; stop on other errors; offline mock mode calls only the primary mock."""
import os, re, subprocess, sys, uuid
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

WF = {"name": "Fallback", "state": [F("message"), F("answer")],
      "nodes": [N("start", "start"), N("m", "llm", prompt="{{state.message}}", model="first", output_field="answer",
                                       credential_id="primary-cred", fallback={"credential_id": "backup-cred", "model": "second"}),
                N("end", "end")],
      "edges": [E("start", "m"), E("m", "end")]}
EXAMPLE = {"input": {"message": "hello"}}

PY_FAKE = '''class FakeError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}"); self.status_code = status


def call_llm(prompt: str, model: str, provider: Optional[str] = None) -> str:
    print(f"CALL {model} {provider or LLM_PROVIDER}", file=sys.stderr)
    mode = os.environ.get("FAKE_PRIMARY", "ok")
    if model == "first" and mode != "ok":
        if mode == "conn": raise ConnectionError("refused")
        raise FakeError(int(mode))
    if model == "second" and os.environ.get("FAKE_SECOND") == "500": raise FakeError(500)
    return f"from {model}"


def _real_call_llm(prompt: str, model: str, provider: Optional[str] = None) -> str:'''

TS_FAKE = '''async function callLlm(prompt: string, model: string, provider?: string): Promise<string> {
  void prompt;
  console.error(`CALL ${model} ${provider || LLM_PROVIDER}`);
  const mode = env("FAKE_PRIMARY") ?? "ok";
  if (model === "first" && mode !== "ok") {
    if (mode === "conn") throw Object.assign(new Error("refused"), { name: "APIConnectionError" });
    throw Object.assign(new Error(`status ${mode}`), { status: Number(mode) });
  }
  if (model === "second" && env("FAKE_SECOND") === "500") throw Object.assign(new Error("status 500"), { status: 500 });
  return `from ${model}`;
}

async function _realCallLlm(prompt: string, model: string, provider?: string): Promise<string> {'''


def calls(stderr): return re.findall(r"^CALL (\S+) (\S+)", stderr, re.M)


def py_run(tmp_path, live, **fake):
    code = X.to_python(WF, "Fallback", 1, {}, EXAMPLE).code
    head = "def call_llm(prompt: str, model: str, provider: Optional[str] = None) -> str:"
    assert code.count(head) == 1 and "primary-cred" not in code and "backup-cred" not in code
    f = tmp_path / f"fb_{uuid.uuid4().hex[:6]}.py"; f.write_text(code.replace(head, PY_FAKE))
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    if live: env["LLM_PROVIDER"] = "openai"
    env.update(fake)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def ts_run(tmp_path, base, live, **fake):
    code = T.to_typescript(WF, "Fallback", 1, {}, EXAMPLE).code
    head = "async function callLlm(prompt: string, model: string, provider?: string): Promise<string> {"
    assert code.count(head) == 1 and "primary-cred" not in code and "backup-cred" not in code
    f = tmp_path / f"fb_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code.replace(head, TS_FAKE))
    env = {k: v for k, v in base.items() if k != "LLM_PROVIDER"}
    if live: env["LLM_PROVIDER"] = "openai"
    env.update(fake)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys=homedir", str(f)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


CASES = [  # (FAKE_PRIMARY, extra env, expected calls, expected answer or None for a failed run)
    ("ok", {}, [("first", "openai")], "from first"),
    ("503", {}, [("first", "openai"), ("second", "openai")], "from second"),
    ("404", {"LLM_FALLBACK_PROVIDER": "anthropic"}, [("first", "openai"), ("second", "anthropic")], "from second"),
    ("conn", {}, [("first", "openai"), ("second", "openai")], "from second"),
    ("401", {}, [("first", "openai")], None),
    ("400", {}, [("first", "openai")], None),
    ("500", {"FAKE_SECOND": "500"}, [("first", "openai"), ("second", "openai")], None),  # at most two calls
]


def check(p, want_calls, answer):
    assert calls(p.stderr) == want_calls, p.stderr[-2000:]
    if answer is None: assert p.returncode != 0 and "Final state:" not in p.stdout
    else: assert p.returncode == 0 and f'"answer": "{answer}"' in p.stdout, p.stderr[-2000:]


@pytest.mark.parametrize("mode,extra,want,answer", CASES)
def test_python_fallback_rules(tmp_path, mode, extra, want, answer):
    check(py_run(tmp_path, True, FAKE_PRIMARY=mode, **extra), want, answer)


@pytest.mark.parametrize("mode,extra,want,answer", CASES)
def test_typescript_fallback_rules(tmp_path, deno_env, mode, extra, want, answer):  # noqa: F811
    check(ts_run(tmp_path, deno_env, True, FAKE_PRIMARY=mode, **extra), want, answer)


def test_offline_mode_never_fails_over(tmp_path):
    """Offline (no LLM_PROVIDER) the node asks the primary only, as a studio dry run does."""
    assert calls(py_run(tmp_path, False, FAKE_PRIMARY="ok").stderr) == [("first", "None")]
    p = py_run(tmp_path, False, FAKE_PRIMARY="503")
    assert p.returncode != 0 and calls(p.stderr) == [("first", "None")]
