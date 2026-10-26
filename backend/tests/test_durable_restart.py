"""TASK-0115: runs survive a server restart. A real uvicorn process (default SQLite database, in-memory job queue) is
killed with SIGKILL and started again on the same database:
- a run paused at a Human node is resumed after the restart;
- an API run that was going (one node finished, the next one sleeping) continues from its progress checkpoint after
  the restart, without running the finished node again;
- a run that keeps being interrupted ends as `error` RUN_INTERRUPTED instead of being retried forever.
TASK-0117 adds the Agent node: a run paused at a tool approval resumes after a restart, and a run killed between two
rounds continues without repeating the finished model call or tool call."""
import http.server, json, os, signal, socket, sqlite3, subprocess, sys, tempfile, threading, time, uuid
from pathlib import Path
import httpx, pytest
from websockets.sync.client import connect
from test_hitl import APPROVAL

BACKEND = Path(__file__).resolve().parents[1]
ADMIN = "durable-admin@example.com"


def H(t): return {"Authorization": f"Bearer {t}"}


class Server:
    """`uvicorn app.main:app` on its own port and database; `restart()` kills it hard and starts it again."""
    def __init__(self, root: Path, **env):
        self.root = root; self.db = str(root / "studio.db"); self.proc = None
        base = {k: v for k, v in os.environ.items() if k not in ("REDIS_URL", "DATABASE_URL", "STUDIO_DEMO_MODE", "OPENAI_API_KEY", "OPENAI_BASE_URL")}
        self.env = {**base, "STUDIO_DB": self.db, "STUDIO_SECRET_KEY_FILE": str(root / "secret.key"), "JWT_SECRET": "durable-test-" + "x" * 32,
                    "STUDIO_IMPORT_DIR": str(root / "imports"), "STUDIO_COOKIE_SECURE": "0", "STUDIO_ADMIN_EMAILS": ADMIN, "TMPDIR": str(root), **env}

    def start(self):
        with socket.socket() as s: s.bind(("127.0.0.1", 0)); self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"],
                                     cwd=BACKEND, env=self.env)
        self.url = f"http://127.0.0.1:{self.port}"
        for _ in range(300):
            try:
                if httpx.get(f"{self.url}/api/health", timeout=1).status_code == 200: return self
            except httpx.HTTPError: pass
            time.sleep(0.1)
        raise AssertionError("server did not start")

    def kill(self):
        self.proc.send_signal(signal.SIGKILL); self.proc.wait(10)

    def restart(self):
        self.kill(); return self.start()

    def run_row(self, rid):
        with sqlite3.connect(self.db) as c:
            c.row_factory = sqlite3.Row; return dict(c.execute("select * from runs where id = ?", (rid,)).fetchone())


@pytest.fixture
def server(request):
    root = Path(tempfile.mkdtemp(prefix="durable-")); srv = Server(root, **getattr(request, "param", {})).start()
    yield srv
    if srv.proc and srv.proc.poll() is None: srv.kill()


def setup(srv, wf):
    email = f"d{uuid.uuid4().hex[:6]}@example.com" if wf is APPROVAL else ADMIN  # Code nodes need code.write (an admin)
    jwt = httpx.post(f"{srv.url}/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]["token"]
    saved = httpx.post(f"{srv.url}/api/workflows", json={**wf, "name": f"{wf['name']} {uuid.uuid4().hex[:4]}"}, headers=H(jwt)).json()
    assert saved.get("data"), saved
    wid = saved["data"]["id"]
    tok = httpx.post(f"{srv.url}/api/workflows/{wid}/tokens", json={"name": "d"}, headers=H(jwt)).json()["data"]["token"]
    return jwt, wid, tok


def poll(srv, wid, tok, rid, until=("ok", "error", "waiting", "timeout", "cancelled"), timeout=30):
    for _ in range(int(timeout / 0.2)):
        r = httpx.get(f"{srv.url}/api/hooks/workflows/{wid}/runs/{rid}", headers=H(tok)).json()["data"]
        if r["status"] in until: return r
        time.sleep(0.2)
    raise AssertionError(f"run {rid} did not settle: {r['status']}")


def test_waiting_run_resumes_after_restart(server):
    jwt, wid, tok = setup(server, APPROVAL)
    rid = httpx.post(f"{server.url}/api/hooks/workflows/{wid}/runs", json={"input": {"message": "order 7"}}, headers=H(tok)).json()["data"]["run_id"]
    assert poll(server, wid, tok, rid)["status"] == "waiting"
    server.restart()
    pending = httpx.get(f"{server.url}/api/runs/pending", headers=H(jwt)).json()["data"]
    assert [p["id"] for p in pending] == [rid]  # still waiting, from the database
    ws = server.url.replace("http", "ws") + f"/ws/run?token={jwt}"
    with connect(ws) as w:
        w.send(json.dumps({"resume_run_id": rid, "response": "approved"}))
        while json.loads(w.recv()).get("type") != "run_summary": pass
    done = poll(server, wid, tok, rid)
    assert done["status"] == "ok" and done["final_state"]["decision"] == "approved"


SLOW = lambda log: {  # noqa: E731
    "name": "Slow", "state": [{"name": "a", "type": "string"}, {"name": "b", "type": "string"}],
    "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
              {"id": "first", "type": "tool", "position": {"x": 1, "y": 0}, "data": {"label": "first", "mode": "code", "output_field": "a",
               "code": f"def main(state):\n    open({log!r}, 'a').write('first\\n')\n    return 'done'\n"}},
              {"id": "slow", "type": "tool", "position": {"x": 2, "y": 0}, "data": {"label": "slow", "mode": "code", "output_field": "b",
               "code": f"import time\ndef main(state):\n    open({log!r}, 'a').write('slow\\n')\n    time.sleep(3)\n    return 'late'\n"}},
              {"id": "e", "type": "end", "position": {"x": 3, "y": 0}, "data": {"label": "e"}}],
    "edges": [{"id": "1", "source": "s", "target": "first"}, {"id": "2", "source": "first", "target": "slow"}, {"id": "3", "source": "slow", "target": "e"}]}
CODE = {"STUDIO_ENABLE_CODE_NODES": "1", "STUDIO_CODE_RUNTIME": "subprocess", "STUDIO_RUN_TIMEOUT": "30"}


def start_slow(server):
    log = server.root / "calls.log"
    _, wid, tok = setup(server, SLOW(str(log)))
    rid = httpx.post(f"{server.url}/api/hooks/workflows/{wid}/runs", json={"input": {}}, headers=H(tok)).json()["data"]["run_id"]
    for _ in range(150):  # `first` finished and its progress checkpoint names `slow` as next
        cp = json.loads(server.run_row(rid)["checkpoint"] or "null") or {}
        if "slow" in json.dumps(cp.get("node") or cp.get("nodes")) and log.exists() and "slow" in log.read_text(): break
        time.sleep(0.1)
    else: raise AssertionError("the run never reached the slow node")
    return log, wid, tok, rid


@pytest.mark.parametrize("server", [CODE], indirect=True)
def test_running_run_continues_after_restart(server):
    log, wid, tok, rid = start_slow(server)
    assert server.run_row(rid)["status"] == "running"
    server.restart()
    done = poll(server, wid, tok, rid)
    assert done["status"] == "ok" and done["final_state"] == {"a": "done", "b": "late"}
    assert log.read_text().splitlines() == ["first", "slow", "slow"]  # `first` ran once; the interrupted node again


@pytest.mark.parametrize("server", [{**CODE, "STUDIO_RECOVER_MAX_ATTEMPTS": "2"}], indirect=True)
def test_run_interrupted_too_often_fails_with_a_code(server):
    log, wid, tok, rid = start_slow(server)
    server.restart()  # attempt 2 starts the slow node again ...
    for _ in range(100):
        if log.read_text().count("slow") == 2: break
        time.sleep(0.1)
    server.restart()  # ... and is interrupted too: recovery gives up
    done = poll(server, wid, tok, rid)
    assert done["status"] == "error" and done["error"]["code"] == "RUN_INTERRUPTED" and done["error"]["details"] == {"attempts": 2}



def ASK_THEN_SLOW(log):  # a Human node, then the slow Code node: the resume claims the run again
    wf = SLOW(log); n = wf["nodes"]
    n.insert(1, {"id": "ask", "type": "human", "position": {"x": 1, "y": 1}, "data": {"label": "ask", "prompt": "Go?", "output_field": "a"}})
    wf["edges"] = [{"id": "0", "source": "s", "target": "ask"}, {"id": "1", "source": "ask", "target": "first"}, *wf["edges"][1:]]
    return wf


@pytest.mark.parametrize("server", [{**CODE, "STUDIO_RECOVER_MAX_ATTEMPTS": "2"}], indirect=True)
def test_resumes_do_not_count_as_interruptions(server):
    """TASK-0123: a resume after a Human node bumps the run's lease too; a restart right after it is the first
    interruption, so the run continues (it used to end as RUN_INTERRUPTED at the limit)."""
    log = server.root / "calls.log"
    jwt, wid, tok = setup(server, ASK_THEN_SLOW(str(log)))
    rid = httpx.post(f"{server.url}/api/hooks/workflows/{wid}/runs", json={"input": {}}, headers=H(tok)).json()["data"]["run_id"]
    assert poll(server, wid, tok, rid)["status"] == "waiting"
    res = httpx.post(f"{server.url}/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(jwt)).json()  # the worker resumes it
    assert res["success"], res
    for _ in range(150):
        if log.exists() and "slow" in log.read_text(): break
        time.sleep(0.1)
    else: raise AssertionError("the run never reached the slow node")
    assert server.run_row(rid)["lease_gen"] == 2  # claimed twice: the start and the resume
    server.restart()
    done = poll(server, wid, tok, rid)
    assert done["status"] == "ok" and done["final_state"]["b"] == "late"
    assert log.read_text().splitlines() == ["first", "slow", "slow"]

# ---- Agent node (TASK-0117) -------------------------------------------------------------------

def agent(tool):
    return {"name": "Agent", "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}, {"name": "steps", "type": "list"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "ag", "type": "agent", "position": {"x": 1, "y": 0}, "data": {"label": "Helper", "prompt": "{{state.message}}", "output_field": "answer",
                                                                                         "steps_field": "steps", "tools": [tool]}},
                      {"id": "e", "type": "end", "position": {"x": 2, "y": 0}, "data": {"label": "e"}}],
            "edges": [{"id": "1", "source": "s", "target": "ag"}, {"id": "2", "source": "ag", "target": "e"}]}


def test_agent_waiting_at_a_tool_approval_resumes_after_restart(server):
    lookup = {"name": "lookup_order", "description": "Find an order", "source": "builtin", "function": "lookup_order", "approval": True}
    jwt, wid, tok = setup(server, agent(lookup))
    rid = httpx.post(f"{server.url}/api/hooks/workflows/{wid}/runs", json={"input": {"message": "Where is order B200?"}}, headers=H(tok)).json()["data"]["run_id"]
    assert poll(server, wid, tok, rid)["status"] == "waiting"
    server.restart()
    assert [p["id"] for p in httpx.get(f"{server.url}/api/runs/pending", headers=H(jwt)).json()["data"]] == [rid]
    ws = server.url.replace("http", "ws") + f"/ws/run?token={jwt}"
    with connect(ws) as w:
        w.send(json.dumps({"resume_run_id": rid, "response": "approved"}))
        while json.loads(w.recv()).get("type") != "run_summary": pass
    done = poll(server, wid, tok, rid)
    assert done["status"] == "ok" and "In transit" in done["final_state"]["answer"]
    assert [(x["tool"], x["approval"]) for x in done["final_state"]["steps"]] == [("lookup_order", "approved")]


class FakeModel:
    """An OpenAI-compatible model and a `ping` API on one local port. The model calls `ping` first; its answer after the
    tool result is slow the first time, so the test can kill the server between the two rounds."""
    def __init__(self):
        self.completions, self.pings, self.answering = [], 0, threading.Event()
        fake = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if self.path.endswith("/ping"): fake.pings += 1; return self.reply({"pong": fake.pings})
                fake.completions.append(body)
                after_tool = any(m.get("role") == "tool" for m in body.get("messages") or [])
                if after_tool and not fake.answering.is_set(): fake.answering.set(); time.sleep(4)
                self.reply(fake.answer(after_tool, bool(body.get("stream"))))
            def reply(self, out):
                stream = isinstance(out, str)
                data = (out if stream else json.dumps(out)).encode()
                self.send_response(200); self.send_header("Content-Type", "text/event-stream" if stream else "application/json")
                self.send_header("Content-Length", str(len(data))); self.end_headers()
                try: self.wfile.write(data)
                except OSError: pass  # the studio was killed while waiting
            def log_message(self, *a): pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler); self.port = self.srv.server_port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    @staticmethod
    def answer(after_tool, stream):
        call = {"id": "t1", "type": "function", "function": {"name": "ping", "arguments": "{}"}}
        msg = {"role": "assistant", "content": "Ping answered."} if after_tool else {"role": "assistant", "content": None, "tool_calls": [call]}
        head = {"id": "x", "created": 1, "model": "m"}
        if not stream:
            return {**head, "object": "chat.completion", "choices": [{"index": 0, "message": msg, "finish_reason": "stop" if after_tool else "tool_calls"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}
        delta = {"role": "assistant", "content": msg["content"]} if after_tool else {"role": "assistant", "tool_calls": [{**call, "index": 0}]}
        rows = [{"choices": [{"index": 0, "delta": delta}]}, {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop" if after_tool else "tool_calls"}]}]
        return "".join(f"data: {json.dumps({**head, 'object': 'chat.completion.chunk', **r})}\n\n" for r in rows) + "data: [DONE]\n\n"


FAKE_MODEL = FakeModel()


@pytest.mark.parametrize("server", [{"OPENAI_API_KEY": "sk-test", "OPENAI_BASE_URL": f"http://127.0.0.1:{FAKE_MODEL.port}/v1",
                                     "STUDIO_HTTP_TOOL_ALLOW_PRIVATE": "1", "STUDIO_RUN_TIMEOUT": "30"}], indirect=True)
def test_agent_run_killed_between_two_rounds_does_not_repeat_finished_calls(server):
    ping = {"name": "ping", "description": "Ping the API", "source": "http", "method": "POST", "url": f"http://127.0.0.1:{FAKE_MODEL.port}/ping"}
    _, wid, tok = setup(server, agent(ping))
    rid = httpx.post(f"{server.url}/api/hooks/workflows/{wid}/runs", json={"input": {"message": "ping it"}}, headers=H(tok)).json()["data"]["run_id"]
    assert FAKE_MODEL.answering.wait(30), "the second model call never came"  # round 1 (model + ping) finished, round 2 is waiting on the model
    server.restart()
    done = poll(server, wid, tok, rid)
    assert done["status"] == "ok" and done["final_state"]["answer"] == "Ping answered."
    first = [b for b in FAKE_MODEL.completions if not any(m.get("role") == "tool" for m in b["messages"])]
    assert len(first) == 1 and FAKE_MODEL.pings == 1  # the finished model call and tool call ran once
    assert len(FAKE_MODEL.completions) == 3  # the interrupted model call ran again
    assert [x["tool"] for x in done["final_state"]["steps"]] == ["ping"]
