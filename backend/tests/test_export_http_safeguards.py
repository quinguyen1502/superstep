"""exported HTTP Tool requests keep the studio's safeguards. Executed in Python and in
TypeScript (Deno) against a local server: private targets refused by default, redirects not followed, URL credentials
sent as Basic auth (not in the URL), and a stable Idempotency-Key."""
import base64, json, os, subprocess, sys, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

SEEN: list = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        SEEN.append({"path": self.path, "auth": self.headers.get("Authorization"), "key": self.headers.get("Idempotency-Key")})
        if self.path.startswith("/redirect"):
            self.send_response(302); self.send_header("Location", "/ok"); self.send_header("Content-Length", "0"); self.end_headers(); return
        body = json.dumps({"ok": True}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass


@pytest.fixture(scope="module")
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s.server_address[1]
    s.shutdown()


def wf(url):
    return {"name": "Http", "state": [F("message"), F("res", "object")],
            "nodes": [N("start", "start"), N("call", "tool", mode="http", method="GET", url=url, body="", output_field="res"), N("end", "end")],
            "edges": [E("start", "call"), E("call", "end")]}


def run_py(tmp_path, graph, allow, run_id="r1"):
    f = tmp_path / f"h_{uuid.uuid4().hex[:6]}.py"; f.write_text(X.to_python(graph, "Http", 1, {}, {"input": {"message": "x"}}).code)
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    env.pop("STUDIO_HTTP_TOOL_ALLOW_PRIVATE", None)
    env.update(SUPERSTEP_RUN_ID=run_id, **({"STUDIO_HTTP_TOOL_ALLOW_PRIVATE": "1"} if allow else {}))
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def run_ts(tmp_path, base, graph, allow, run_id="r1"):
    f = tmp_path / f"h_{uuid.uuid4().hex[:6]}.ts"; f.write_text(T.to_typescript(graph, "Http", 1, {}, {"input": {"message": "x"}}).code)
    env = {k: v for k, v in base.items() if k not in ("LLM_PROVIDER", "STUDIO_HTTP_TOOL_ALLOW_PRIVATE")}
    env.update(SUPERSTEP_RUN_ID=run_id, **({"STUDIO_HTTP_TOOL_ALLOW_PRIVATE": "1"} if allow else {}))
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys", "--allow-net", str(f)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


RUNNERS = {"python": lambda tp, base, g, allow, run_id="r1": run_py(tp, g, allow, run_id), "typescript": run_ts}


@pytest.fixture(params=["python", "typescript"])
def runner(request):
    if request.param == "typescript":
        if not DENO: pytest.skip("deno is not installed")
        base = request.getfixturevalue("deno_env")
    else:
        base = None
    return lambda tp, g, allow, run_id="r1": RUNNERS[request.param](tp, base, g, allow, run_id)


def test_private_target_is_refused_by_default(tmp_path, server, runner):
    SEEN.clear()
    p = runner(tmp_path, wf(f"http://127.0.0.1:{server}/ok"), allow=False)
    assert p.returncode != 0 and "STUDIO_HTTP_TOOL_ALLOW_PRIVATE" in p.stderr and SEEN == []


def test_basic_auth_and_stable_idempotency_key(tmp_path, server, runner):
    SEEN.clear()
    url = f"http://alice:p%40ss@127.0.0.1:{server}/ok?q=1"
    for _ in range(2): assert runner(tmp_path, wf(url), allow=True).returncode == 0
    p = runner(tmp_path, wf(url), allow=True, run_id="r2")
    assert p.returncode == 0 and '"ok": true' in p.stdout
    assert [s["path"] for s in SEEN] == ["/ok?q=1"] * 3
    assert {s["auth"] for s in SEEN} == {"Basic " + base64.b64encode(b"alice:p@ss").decode()}
    keys = [s["key"] for s in SEEN]
    assert all(k and len(k) == 32 for k in keys) and keys[0] == keys[1] != keys[2]  # same run + request: same key


def test_redirects_are_not_followed(tmp_path, server, runner):
    SEEN.clear()
    p = runner(tmp_path, wf(f"http://127.0.0.1:{server}/redirect"), allow=True)
    assert p.returncode == 0 and [s["path"] for s in SEEN] == ["/redirect"]


def test_non_http_scheme_is_refused(tmp_path, runner):
    p = runner(tmp_path, wf("file:///etc/passwd"), allow=True)
    assert p.returncode != 0 and "only http(s) URLs" in p.stderr
