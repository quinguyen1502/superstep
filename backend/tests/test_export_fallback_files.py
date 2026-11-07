"""TASK-0268 (REQ-0089, DEC-0088): an LLM node with a fallback model AND attachments, executed in Python and TypeScript
(Deno). As in the studio (nodes.py passes the same files to model_policy.run), the fallback model gets the same prompt
and files, once, under the same failover rules; offline mock mode calls only the primary mock. The provider call is a
local fake: no network, no paid call."""
import os, re, subprocess, sys, uuid
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

WF = {"name": "FallbackFiles", "state": [F("message"), F("files", "list"), F("answer")],
      "nodes": [N("start", "start"),
                N("m", "llm", prompt="{{state.message}}", model="first", output_field="answer", include_attachments=True,
                  credential_id="primary-cred", fallback={"credential_id": "backup-cred", "model": "second"}),
                N("end", "end")],
      "edges": [E("start", "m"), E("m", "end")]}
EXAMPLE = {"input": {"message": "hello", "files": [{"name": "a.txt", "type": "text/plain", "text": "alpha"},
                                                   {"name": "b.png", "type": "image/png"}]}}

PY_FAKE = '''class FakeError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}"); self.status_code = status


def call_llm_files(prompt: str, model: str, files: Any, provider: Optional[str] = None) -> str:
    text, images = with_files(prompt, files)
    print(f"CALL {model} {provider or LLM_PROVIDER} {'|'.join(f['name'] for f in files)} {len(text)}", file=sys.stderr)
    mode = os.environ.get("FAKE_PRIMARY", "ok")
    if model == "first" and mode != "ok" and LLM_PROVIDER:
        if mode == "conn": raise ConnectionError("refused")
        raise FakeError(int(mode))
    if model == "second" and os.environ.get("FAKE_SECOND") == "500": raise FakeError(500)
    return f"from {model}"


def _real_call_llm_files(prompt: str, model: str, files: Any, provider: Optional[str] = None) -> str:'''

TS_FAKE = '''async function callLlmFiles(prompt: string, model: string, files: unknown, provider?: string): Promise<string> {
  const list = fileList(files);
  const [text] = withFiles(prompt, list);
  console.error(`CALL ${model} ${provider || LLM_PROVIDER} ${list.map((f) => f.name).join("|")} ${text.length}`);
  const mode = env("FAKE_PRIMARY") ?? "ok";
  if (model === "first" && mode !== "ok" && LLM_PROVIDER) {
    if (mode === "conn") throw Object.assign(new Error("refused"), { name: "APIConnectionError" });
    throw Object.assign(new Error(`status ${mode}`), { status: Number(mode) });
  }
  if (model === "second" && env("FAKE_SECOND") === "500") throw Object.assign(new Error("status 500"), { status: 500 });
  return `from ${model}`;
}

async function _realCallLlmFiles(prompt: string, model: string, files: unknown, provider?: string): Promise<string> {'''


def calls(stderr): return re.findall(r"^CALL (\S+) (\S+) (\S+) (\d+)", stderr, re.M)


def py_run(tmp_path, base, live, **fake):
    code = X.to_python(WF, "FallbackFiles", 1, {}, EXAMPLE).code
    head = "def call_llm_files(prompt: str, model: str, files: Any, provider: Optional[str] = None) -> str:"
    assert code.count(head) == 1 and "primary-cred" not in code and "backup-cred" not in code and "TODO: the studio's fallback" not in code
    f = tmp_path / f"ff_{uuid.uuid4().hex[:6]}.py"; f.write_text(code.replace(head, PY_FAKE))
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    if live: env["LLM_PROVIDER"] = "openai"
    env.update(fake)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def ts_run(tmp_path, base, live, **fake):
    code = T.to_typescript(WF, "FallbackFiles", 1, {}, EXAMPLE).code
    head = "async function callLlmFiles(prompt: string, model: string, files: unknown, provider?: string): Promise<string> {"
    assert code.count(head) == 1 and "primary-cred" not in code and "backup-cred" not in code and "TODO: the studio's fallback" not in code
    f = tmp_path / f"ff_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code.replace(head, TS_FAKE))
    env = {k: v for k, v in base.items() if k != "LLM_PROVIDER"}
    if live: env["LLM_PROVIDER"] = "openai"
    env.update(fake)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys=homedir", str(f)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


@pytest.fixture(params=["python", "typescript"])
def run(request):
    if request.param == "typescript":
        base = request.getfixturevalue("deno_env")
        return lambda tp, live, **fake: ts_run(tp, base, live, **fake)
    return lambda tp, live, **fake: py_run(tp, None, live, **fake)


FILES = "a.txt|b.png"
CASES = [  # (FAKE_PRIMARY, extra env, expected (model, provider) calls, answer or None for a failed run)
    ("ok", {}, [("first", "openai")], "from first"),
    ("503", {}, [("first", "openai"), ("second", "openai")], "from second"),
    ("404", {"LLM_FALLBACK_PROVIDER": "anthropic"}, [("first", "openai"), ("second", "anthropic")], "from second"),
    ("conn", {}, [("first", "openai"), ("second", "openai")], "from second"),
    ("401", {}, [("first", "openai")], None),
    ("503", {"FAKE_SECOND": "500"}, [("first", "openai"), ("second", "openai")], None),  # the fallback is tried once
]


@pytest.mark.parametrize("primary,extra,expected,answer", CASES)
def test_fallback_gets_the_same_files_once(tmp_path, run, primary, extra, expected, answer):
    p = run(tmp_path, True, FAKE_PRIMARY=primary, **extra)
    got = calls(p.stderr)
    assert [(m, pr) for m, pr, _, _ in got] == expected, p.stderr
    assert {fs for _, _, fs, _ in got} == {FILES} and len({n for _, _, _, n in got}) == 1  # same files, same text
    if answer is None:
        assert p.returncode != 0
    else:
        assert p.returncode == 0 and answer in p.stdout, p.stderr


def test_offline_mock_calls_only_the_primary(tmp_path, run):
    p = run(tmp_path, False, FAKE_PRIMARY="503")
    assert p.returncode == 0 and [c[0] for c in calls(p.stderr)] == ["first"]
