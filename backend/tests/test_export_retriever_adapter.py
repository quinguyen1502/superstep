"""the exported Retriever adapter, executed in Python and TypeScript (Deno) against a
local stand-in for the Superstep knowledge base search API (same path and envelope). Configured only by SUPERSTEP_URL,
SUPERSTEP_TOKEN and <PREFIX>_ID; unconfigured it is an announced offline mock, or an error in a live run."""
import json, os, subprocess, sys, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

LOG: list = []
HITS = [{"text": "Refunds arrive in 5 days.", "filename": "policy.pdf", "score": 0.91}]


class Studio(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LOG.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if self.path == "/api/knowledge-bases/kb-good/search" and self.headers.get("Authorization") == "Bearer tok":
            status, out = 200, {"success": True, "data": HITS[: body["top_k"]], "error": None}
        else:
            status, out = 404, {"success": False, "data": None, "error": {"code": "KB_NOT_FOUND", "message": "Knowledge base not found"}}
        raw = json.dumps(out).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def log_message(self, *a): pass


@pytest.fixture(scope="module")
def studio():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Studio)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}/"
    s.shutdown()


WF = {"name": "Kb", "state": [F("question"), F("hits", "list")],
      "nodes": [N("start", "start"), N("r", "retriever", knowledge_base_id="kb-studio-id", query="{{state.question}}", top_k=1, output_field="hits"),
                N("end", "end")],
      "edges": [E("start", "r"), E("r", "end")]}
EXAMPLE = {"input": {"question": "when do refunds arrive"}}


def clean(env):
    return {k: v for k, v in env.items() if k not in KEYS and k != "PYTHONPATH" and not k.startswith(("SUPERSTEP_", "KNOWLEDGE_BASE_"))}


def run_py(tmp_path, extra):
    code = X.to_python(WF, "Kb", 1, {}, EXAMPLE).code
    assert 'retrieve("KNOWLEDGE_BASE_1", ' in code and "kb-studio-id" not in code
    f = tmp_path / f"k_{uuid.uuid4().hex[:6]}.py"; f.write_text(code)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env={**clean(os.environ), **extra}, capture_output=True, text=True,
                          timeout=120, stdin=subprocess.DEVNULL)


def run_ts(tmp_path, base, extra):
    code = T.to_typescript(WF, "Kb", 1, {}, EXAMPLE).code
    assert 'retrieve("KNOWLEDGE_BASE_1", ' in code and "kb-studio-id" not in code
    f = tmp_path / f"k_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys", "--allow-net", str(f)], cwd=tmp_path,
                          env={**clean(base), **extra}, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


@pytest.fixture(params=["python", "typescript"])
def run(request):
    if request.param == "typescript":
        base = request.getfixturevalue("deno_env")
        return lambda tp, **e: run_ts(tp, base, e)
    return lambda tp, **e: run_py(tp, e)


def test_configured_search_returns_the_studio_hits(tmp_path, studio, run):
    LOG.clear()
    p = run(tmp_path, SUPERSTEP_URL=studio, SUPERSTEP_TOKEN="tok", KNOWLEDGE_BASE_1_ID="kb-good", LLM_PROVIDER="")
    assert p.returncode == 0, p.stderr
    assert "Refunds arrive in 5 days." in p.stdout and "(offline mock)" not in p.stderr
    assert LOG == [{"path": "/api/knowledge-bases/kb-good/search", "auth": "Bearer tok", "body": {"query": "when do refunds arrive", "top_k": 1}}]


def test_a_studio_error_stops_the_run(tmp_path, studio, run):
    p = run(tmp_path, SUPERSTEP_URL=studio, SUPERSTEP_TOKEN="tok", KNOWLEDGE_BASE_1_ID="kb-gone")
    assert p.returncode != 0 and "KB_NOT_FOUND" in p.stderr


def test_unconfigured_offline_is_an_announced_mock(tmp_path, run):
    p = run(tmp_path)
    assert p.returncode == 0 and "(offline mock) Knowledge base search" in p.stderr and "KNOWLEDGE_BASE_1_ID" in p.stderr


def test_unconfigured_live_run_is_refused(tmp_path, run):
    p = run(tmp_path, LLM_PROVIDER="openai", SUPERSTEP_URL="http://127.0.0.1:9")
    assert p.returncode != 0 and "set SUPERSTEP_TOKEN, KNOWLEDGE_BASE_1_ID" in p.stderr


def test_agent_knowledge_tools_share_the_prefix_of_their_base():
    tool = lambda name, kid: {"name": name, "description": name, "source": "knowledge", "knowledge_base_id": kid, "top_k": 2,  # noqa: E731
                              "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}
    g = {"name": "Ag", "state": [F("message"), F("answer"), F("hits", "list")],
         "nodes": [N("start", "start"), N("r", "retriever", knowledge_base_id="kb-a", query="q", output_field="hits"),
                   N("ag", "agent", prompt="{{state.message}}", output_field="answer", tools=[tool("docs", "kb-b"), tool("faq", "kb-a")]),
                   N("end", "end")],
         "edges": [E("start", "r"), E("r", "ag"), E("ag", "end")]}
    for code, call in ((X.to_python(g, "Ag", 1, {}, {}).code, "retrieve"), (T.to_typescript(g, "Ag", 1, {}, {}).code, "await retrieve")):
        assert f'{call}("KNOWLEDGE_BASE_2", ' in code and f'{call}("KNOWLEDGE_BASE_1", ' in code
        assert "kb-a" not in code and "kb-b" not in code and "KNOWLEDGE_BASE_1, KNOWLEDGE_BASE_2" in code
