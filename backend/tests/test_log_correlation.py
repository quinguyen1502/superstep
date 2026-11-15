"""Structured logs: JSON lines with request, run and trace ids; X-Request-ID echo; token redaction; text format unchanged."""
import asyncio, io, json, logging, subprocess, sys, os
from types import SimpleNamespace as NS
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.api.request_context import RequestContext
from app.core import logging as L
from app.services.telemetry import Telemetry

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def capture(name="studio"):
    """A JSON handler on `name` writing into a buffer; returns (buffer, remove)."""
    buf = io.StringIO(); h = L.json_handler(buf); lg = logging.getLogger(name); lg.addHandler(h); old = lg.level; lg.setLevel(logging.INFO)
    def remove(): lg.removeHandler(h); lg.setLevel(old)
    return buf, remove


def lines(buf): return [json.loads(x) for x in buf.getvalue().splitlines() if x.strip()]


def test_json_line_has_fields_and_ids():
    buf, remove = capture()
    try:
        with L.request_context("req-1"), L.run_context("run-1", "wf-1"):
            L.bind_trace("ab" * 16)
            L.get_logger("t").warning("hello %s", "world")
        L.get_logger("t").warning("outside")
    finally: remove()
    a, b = lines(buf)
    assert a["message"] == "hello world" and a["level"] == "WARNING" and a["logger"] == "studio.t" and a["ts"].endswith("Z")
    assert (a["request_id"], a["run_id"], a["workflow_id"], a["trace_id"]) == ("req-1", "run-1", "wf-1", "ab" * 16)
    assert "request_id" not in b and "run_id" not in b and "trace_id" not in b  # unknown ids are left out


def test_json_redacts_websocket_tokens_and_exceptions():
    buf, remove = capture("uvicorn.access")
    try:
        lg = logging.getLogger("uvicorn.access")
        lg.info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:5", "GET", "/ws/run?token=eyJhbGciOi.secret", "1.1", 101)
        try: raise ValueError("bad token=eyJzecret")
        except ValueError: lg.exception("failed /ws/chat?token=abc")
    finally: remove()
    out = buf.getvalue()
    assert "eyJ" not in out and "abc" not in out and out.count("token=***") >= 3
    assert lines(buf)[1]["exception"].startswith("Traceback")


def test_request_id_is_echoed_or_replaced():
    app = FastAPI(); app.add_middleware(RequestContext); seen = []
    @app.get("/x")
    def x():
        seen.append(L.current_ids()["request_id"]); return {"ok": True}
    c = TestClient(app)
    r = c.get("/x", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123" and seen[-1] == "abc-123"
    for bad in ("x" * 65, "evil\" value", "a b", "<script>"):
        r = c.get("/x", headers={"X-Request-ID": bad})
        rid = r.headers["x-request-id"]
        assert rid != bad and len(rid) == 32 and seen[-1] == rid
    r = c.get("/x"); assert len(r.headers["x-request-id"]) == 32
    assert L.current_ids()["request_id"] == ""  # reset after the request


def test_real_app_echoes_request_id():
    from app.main import app
    r = TestClient(app).get("/api/health", headers={"X-Request-ID": "probe-7"})
    assert r.status_code == 200 and r.headers["x-request-id"] == "probe-7"


def test_run_lines_carry_run_and_trace_ids():
    from app.services.run_service import RunPlan, RunService
    exp = InMemorySpanExporter(); runs = []
    svc = RunService(None, NS(add=runs.append), telemetry=Telemetry(exporters=[exp], sync=True))
    plan = RunPlan("wf-log", {}, {})
    def events():  # runs in the engine thread
        L.get_logger("engine.test").warning("inside the run")
        yield {"type": "node_started", "node": "a"}
        yield {"type": "node_finished", "node": "a", "node_type": "tool", "duration_ms": 1}
    plan.events = events
    async def send(ev): return True
    async def listen(): await asyncio.sleep(3600)
    buf, remove = capture()
    try:
        with L.request_context("req-run"):
            assert asyncio.run(svc.execute(plan, send, listen, "u1")) == "ok"
    finally: remove()
    [line] = [x for x in lines(buf) if x["message"] == "inside the run"]
    assert line["run_id"] == runs[0].id and line["workflow_id"] == "wf-log" and line["request_id"] == "req-run"
    assert line["trace_id"] == runs[0].trace_id and len(line["trace_id"]) == 32


def _run(code: str, **env) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if not k.startswith(("STUDIO_LOG", "OTEL_"))}; e.update(env)
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=60, env=e)


CODE = ("import logging; from app.core import config, logging as L; L.configure(config.log_format(), config.log_level());"
        "logging.getLogger('studio.x').warning('plain %s', 1); logging.getLogger('uvicorn.access').warning('GET /a?token=s3cr3t');")


def test_text_format_is_unchanged_by_default():
    out = _run(CODE)
    assert out.returncode == 0 and out.stderr.splitlines()[0] == "plain 1"  # same as before: Python's last-resort handler
    assert "{" not in out.stderr


def test_json_format_from_env_covers_uvicorn():
    out = _run(CODE, STUDIO_LOG_FORMAT="json")
    a, b = [json.loads(x) for x in out.stderr.splitlines()]
    assert a["message"] == "plain 1" and b["logger"] == "uvicorn.access" and b["message"] == "GET /a?token=***"


def test_level_in_text_format():
    out = _run("import logging; from app.core import logging as L; L.configure('text', 'INFO'); logging.getLogger('studio.x').info('note')")
    assert out.stderr.strip() == "INFO studio.x: note"
