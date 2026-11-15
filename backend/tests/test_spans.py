"""Opt-in HTTP, SQL and Redis spans (STUDIO_OTEL_INSTRUMENT): off by default, under the request or run, no values."""
import asyncio, os, subprocess, sys
from types import SimpleNamespace as NS
import fakeredis, pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode
from sqlalchemy import create_engine, text

from app.api.http_spans import HttpSpans
from app.services import job_queue as jq
from app.services.telemetry import Telemetry, _scoped, redis_key_prefix

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = "s3cret-value-42"


@pytest.fixture
def traced(tmp_path):
    exp = InMemorySpanExporter(); t = Telemetry(exporters=[exp], sync=True, metric_readers=[], instrument=True)
    eng = create_engine(f"sqlite:///{tmp_path / 'spans.db'}")
    with eng.begin() as c: c.execute(text("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)"))
    assert t.instrument(eng)
    yield t, exp, eng, fakeredis.FakeRedis(decode_responses=True)
    Telemetry.uninstrument(); eng.dispose()


def work(eng, r):
    with eng.begin() as c: c.execute(text("INSERT INTO notes (body) VALUES (:b)"), {"b": SECRET})
    r.set("studio:rl:email:u123:999", SECRET); r.get("studio:rl:email:u123:999")


def no_values(spans):
    for s in spans:
        for v in (s.attributes or {}).values(): assert SECRET not in str(v) and "u123" not in str(v), (s.name, s.attributes)


def test_off_imports_no_instrumentation():
    code = ("import sys; from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter;"
            "from app.services.telemetry import Telemetry; t = Telemetry(exporters=[InMemorySpanExporter()], metric_readers=[]);"
            "import app.main; print(t.instrumented, t.instrument(None), t.open_http({'type': 'http', 'path': '/x'}),"
            "any(m.startswith('opentelemetry.instrumentation') for m in sys.modules))")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OTEL_", "STUDIO_OTEL"))}
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().splitlines()[-1] == "False False None False"


def test_flag_needs_a_traces_exporter(monkeypatch):
    monkeypatch.setenv("STUDIO_OTEL_INSTRUMENT", "1")
    assert not Telemetry(exporters=[], metric_readers=[]).instrumented
    assert Telemetry(exporters=[InMemorySpanExporter()], sync=True, metric_readers=[]).instrumented


def test_request_has_sql_and_redis_children(traced):
    t, exp, eng, r = traced
    app = FastAPI(); app.add_middleware(HttpSpans, telemetry=lambda: t)
    @app.get("/api/notes/{nid}")
    def note(nid: str): work(eng, r); return {"ok": nid}
    @app.get("/api/health")
    def health(): work(eng, r); return {"ok": True}
    @app.get("/api/boom")
    def boom(): raise RuntimeError("x")
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/api/health").status_code == 200
    assert exp.get_finished_spans() == ()  # probes: no request span, and its SQL and Redis calls have no parent to join
    assert c.get(f"/api/notes/{SECRET}?q={SECRET}").status_code == 200
    spans = exp.get_finished_spans(); [http] = [s for s in spans if s.kind == SpanKind.SERVER]
    assert http.name == "GET /api/notes/{nid}" and http.attributes["http.route"] == "/api/notes/{nid}" and http.attributes["http.response.status_code"] == 200
    kids = [s for s in spans if s.parent is not None and s.parent.span_id == http.context.span_id]
    sql = [s for s in kids if s.instrumentation_scope.name.endswith("sqlalchemy")]
    rds = [s for s in kids if s.instrumentation_scope.name.endswith("redis")]
    assert sql and len(rds) == 2 and {s.name for s in rds} == {"SET", "GET"}
    assert any("INSERT INTO notes" in str(s.attributes.get("db.statement") or s.attributes.get("db.query.text")) for s in sql)
    assert all(s.attributes["studio.redis.key_prefix"] == "studio:rl:email" for s in rds)
    no_values(spans)
    exp.clear(); c.get("/api/boom")
    [http] = [s for s in exp.get_finished_spans() if s.kind == SpanKind.SERVER]
    assert http.status.status_code == StatusCode.ERROR and http.attributes["http.response.status_code"] == 500


def test_incoming_traceparent_is_the_parent(traced):
    t, exp, eng, r = traced
    app = FastAPI(); app.add_middleware(HttpSpans, telemetry=lambda: t)
    @app.get("/x")
    def x(): return {}
    TestClient(app).get("/x", headers={"traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01"})
    [http] = exp.get_finished_spans()
    assert format(http.context.trace_id, "032x") == "a" * 32 and format(http.parent.span_id, "016x") == "b" * 16


def test_calls_outside_a_request_or_run_are_not_traced(traced):
    t, exp, eng, r = traced
    work(eng, r)
    assert exp.get_finished_spans() == ()


def test_run_sql_and_redis_spans_join_the_run_trace(traced):
    t, exp, eng, r = traced
    from app.services.run_service import RunPlan, RunService
    runs = []; svc = RunService(None, NS(add=runs.append), telemetry=t)
    plan = RunPlan("wf-spans", {}, {})
    def events():  # the engine thread
        work(eng, r)
        yield {"type": "node_started", "node": "a"}
        yield {"type": "node_finished", "node": "a", "node_type": "tool", "duration_ms": 1}
    plan.events = events
    async def send(ev): return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.execute(plan, send, listen, "u1")) == "ok"
    spans = exp.get_finished_spans()
    [root] = [s for s in spans if s.name == "run"]
    assert root.parent is None and format(root.context.trace_id, "032x") == runs[0].trace_id
    client = [s for s in spans if s.kind == SpanKind.CLIENT]
    assert any(s.instrumentation_scope.name.endswith("sqlalchemy") for s in client) and sum(s.instrumentation_scope.name.endswith("redis") for s in client) == 2
    assert all(s.context.trace_id == root.context.trace_id and s.parent.span_id == root.context.span_id for s in client)
    no_values(spans)
    from opentelemetry import trace
    assert not trace.get_current_span().get_span_context().is_valid  # detached after the run


def test_queued_run_links_the_request(traced):
    t, exp, eng, r = traced
    app = FastAPI(); app.add_middleware(HttpSpans, telemetry=lambda: t); q = jq.InMemoryJobQueue()
    @app.post("/api/run")
    def run():
        q.enqueue({"run_id": "r1", "workflow_id": "w"}); q.enqueue({"kind": "delivery", "delivery_id": "d"}); return {}
    TestClient(app).post("/api/run")
    [http] = [s for s in exp.get_finished_spans() if s.kind == SpanKind.SERVER]
    job, other = q.dequeue(1), q.dequeue(1)
    assert job["request_span"] == {"trace_id": format(http.context.trace_id, "032x"), "span_id": format(http.context.span_id, "016x")}
    assert "request_span" not in other
    rs = t.start_run({"id": "r1", "workflow_id": "w", "started": 1.0}, request=job["request_span"])
    t.end_run(rs, {"status": "ok", "ended": 2.0, "started": 1.0}, {"error_count": 0, "tokens_in": 0, "tokens_out": 0, "duration_ms": 1}, observe=False)
    [root] = [s for s in exp.get_finished_spans() if s.name == "run"]
    assert root.parent is None and [(l.context.span_id, l.attributes["studio.link"]) for l in root.links] == [(http.context.span_id, "request")]


def test_langsmith_receives_only_run_and_node_spans(traced):
    t, exp, eng, r = traced
    inner = InMemorySpanExporter(); scoped = _scoped(inner)
    app = FastAPI(); app.add_middleware(HttpSpans, telemetry=lambda: t)
    @app.get("/x")
    def x(): work(eng, r); return {}
    TestClient(app).get("/x")
    rs = t.start_run({"id": "r", "workflow_id": "w", "started": 1.0})
    t.end_run(rs, {"status": "ok", "ended": 2.0, "started": 1.0}, {"error_count": 0, "tokens_in": 0, "tokens_out": 0, "duration_ms": 1}, observe=False)
    scoped.export(list(exp.get_finished_spans()))
    assert [s.name for s in inner.get_finished_spans()] == ["run"]


def test_redis_key_prefix_keeps_fixed_words_only():
    assert redis_key_prefix(("GET", "studio:rl:email:abc123:60")) == "studio:rl:email"
    assert redis_key_prefix(("GET", "studio:run:5f3a9")) == "studio:run"
    assert redis_key_prefix(("GET", "user@example.com")) == "" and redis_key_prefix(("PING",)) == ""
