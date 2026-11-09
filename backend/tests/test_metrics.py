"""OTel metrics: label rules, model usage and errors, the provider 429 code, HTTP by route template, jobs and gauges."""
import asyncio, subprocess, sys, os, time
import httpx, pytest, respx
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.api.http_metrics import HttpMetrics
from app.core.errors import AppError, CATALOG
from app.engine import model_policy, providers
from app.engine.usage import make_usage
from app.services import job_queue as jq
from app.services.health_probes import Probes
from app.services.run_bus import InMemoryRunBus
from app.services.run_worker import RunWorker
from app.services.telemetry import LABELS, Telemetry, labels

FORBIDDEN = {"user_id", "run_id", "user", "owner", "path", "url", "prompt"}


def meter():
    reader = InMemoryMetricReader(); return Telemetry(exporters=[], metric_readers=[reader]), reader


def points(reader) -> dict:
    """{metric name: [(value, attributes)]} from one collection."""
    out = {}
    data = reader.get_metrics_data()
    for rm in (data.resource_metrics if data else []):
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                for p in m.data.data_points:
                    out.setdefault(m.name, []).append((getattr(p, "value", getattr(p, "sum", None)), dict(p.attributes)))
    return out


def assert_bounded(pts: dict):
    for name, items in pts.items():
        for _, attrs in items:
            assert set(attrs) <= LABELS and not (set(attrs) & FORBIDDEN), (name, attrs)


def test_labels_keep_only_the_allowed_set():
    assert labels(model="gpt-4o", user_id="u1", run_id="r1", provider=None) == {"model": "gpt-4o", "provider": ""}
    assert not (LABELS & FORBIDDEN)


def test_metrics_off_does_not_import_the_metrics_sdk():
    code = ("import sys, os; os.environ.pop('STUDIO_OTEL_METRICS', None); os.environ.pop('OTEL_EXPORTER_OTLP_ENDPOINT', None);"
            "from app.services.telemetry import Telemetry; t = Telemetry(); t.watch(None); t.model_event({'type': 'node_finished', 'usage': {}}, 'w');"
            "t.http_request('/x', 'GET', 200, 1.0); t.jobs('reaped', 1);"
            "print(any(m.startswith('opentelemetry.sdk.metrics') for m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         capture_output=True, text=True, timeout=60, env={k: v for k, v in os.environ.items() if not k.startswith("OTEL_")})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"


def test_run_metrics_carry_the_workflow_id():
    t, reader = meter()
    t.observe({"status": "ok", "source": "api", "workflow_id": "wf1", "owner": "u1", "id": "r1"},
              {"duration_ms": 5, "tokens_in": 3, "tokens_out": 2, "cost_usd": None, "error_count": 0})
    pts = points(reader); assert_bounded(pts)
    assert pts["studio.runs"] == [(1, {"status": "ok", "source": "api", "workflow_id": "wf1"})]
    assert "studio.cost" not in pts  # an unpriced run is skipped


def test_model_usage_cost_and_unpriced():
    t, reader = meter()
    t.model_event({"type": "node_finished", "usage": make_usage("openai", "gpt-4o-mini", 1000, 500)}, "wf1")
    t.model_event({"type": "node_finished", "usage": make_usage("openai", "local-model", 10, 5)}, "wf1")
    t.model_event({"type": "approval_review", "usage": make_usage("openai", "gpt-4o-mini", 100, 10)}, None)
    t.model_event({"type": "node_finished", "usage": make_usage("workflow", "child-wf", 7, 7)}, "wf1")  # counted by the child run
    pts = points(reader); assert_bounded(pts)
    tokens = {(a["model"], a["direction"], a["workflow_id"]): v for v, a in pts["studio.llm.tokens"]}
    assert tokens[("gpt-4o-mini", "input", "wf1")] == 1000 and tokens[("local-model", "output", "wf1")] == 5
    assert tokens[("gpt-4o-mini", "input", "adhoc")] == 100 and not any(m == "child-wf" for m, _, _ in tokens)
    cost = {(a["model"], a["workflow_id"]): v for v, a in pts["studio.llm.cost"]}
    assert set(cost) == {("gpt-4o-mini", "wf1"), ("gpt-4o-mini", "adhoc")}
    assert cost[("gpt-4o-mini", "wf1")] == pytest.approx((1000 * 0.15 + 500 * 0.6) / 1e6)
    assert pts["studio.llm.unpriced"] == [(1, {"model": "local-model", "provider": "openai"})]


def test_llm_errors_and_fallbacks():
    t, reader = meter()
    attempts = [{"attempt": 1, "provider": "openai", "model": "gpt-4o", "status": "error", "code": "PROVIDER_RATE_LIMITED"},
                {"attempt": 2, "provider": "anthropic", "model": "claude", "status": "ok"}]
    t.model_event({"type": "node_finished", "model_attempts": attempts, "usage": make_usage("anthropic", "claude", 1, 1)}, "wf")
    t.model_event({"type": "error", "code": "PROVIDER_BAD_RESPONSE", "provider": "openai", "model": "gpt-4o"}, "wf")
    t.model_event({"type": "error", "code": "PROVIDER_AUTH_FAILED"}, "wf")
    t.model_event({"type": "error", "code": "CODE_FAILED"}, "wf")  # not a model error
    pts = points(reader); assert_bounded(pts)
    errors = {(a["code"], a["provider"]): v for v, a in pts["studio.llm.errors"]}
    assert errors == {("PROVIDER_RATE_LIMITED", "openai"): 1, ("PROVIDER_BAD_RESPONSE", "openai"): 1, ("PROVIDER_AUTH_FAILED", "unknown"): 1}
    assert pts["studio.llm.fallbacks"] == [(1, {"primary_provider": "openai", "fallback_provider": "anthropic", "code": "PROVIDER_RATE_LIMITED"})]


@respx.mock
def test_http_429_is_rate_limited_and_502_to_clients():
    respx.post("http://gpu:8000/v1/chat/completions").respond(429, json={"error": {"message": "slow down"}})
    with pytest.raises(providers.ProviderError) as e:
        providers.request("openai_compatible", "POST", "http://gpu:8000/v1/chat/completions", {}, {"model": "m"}, model="m")
    assert e.value.code == "PROVIDER_RATE_LIMITED" and CATALOG["PROVIDER_RATE_LIMITED"][0] == 502
    assert AppError("PROVIDER_RATE_LIMITED", **e.value.params).status == 502
    respx.post("http://gpu:8000/v1/x").respond(503, json={"error": "busy"})
    with pytest.raises(providers.ProviderError) as e: providers.request("openai_compatible", "POST", "http://gpu:8000/v1/x", {}, {})
    assert e.value.code == "PROVIDER_BAD_RESPONSE"  # 5xx keeps its code


def test_sdk_429_maps_to_rate_limited():
    class RateLimitError(Exception): status_code = 429
    assert providers._map_http_error(RateLimitError("too many"), "openai", "gpt-4o").code == "PROVIDER_RATE_LIMITED"
    class ServerError(Exception): status_code = 500
    assert providers._map_http_error(ServerError("boom"), "openai", "gpt-4o").code == "PROVIDER_BAD_RESPONSE"
    assert "PROVIDER_RATE_LIMITED" in model_policy.FAILOVER_CODES


def http_app(t):
    app = FastAPI()
    @app.get("/items/{item_id}")
    def item(item_id: str): return {"id": item_id}
    @app.get("/boom")
    def boom(): raise RuntimeError("boom")
    @app.get("/api/health")
    def health(): return {"ok": True}
    @app.get("/stream")
    def stream(): return StreamingResponse(iter([b"a", b"b"]), media_type="text/plain")
    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept(); await sock.send_text("hi"); await sock.close()
    app.add_middleware(HttpMetrics, telemetry=lambda: t)
    return app


def test_http_requests_by_route_template():
    t, reader = meter(); c = TestClient(http_app(t), raise_server_exceptions=False)
    assert c.get("/items/abc?secret=1").status_code == 200
    assert c.get("/boom").status_code == 500
    assert c.get("/stream").text == "ab"
    assert c.get("/nope/123").status_code == 404
    assert c.get("/api/health").status_code == 200
    with c.websocket_connect("/ws") as ws: assert ws.receive_text() == "hi"
    pts = points(reader); assert_bounded(pts)
    reqs = {(a["route"], a["status_class"]): v for v, a in pts["studio.http.server.requests"]}
    assert reqs == {("/items/{item_id}", "2xx"): 1, ("/boom", "5xx"): 1, ("/stream", "2xx"): 1, ("unmatched", "4xx"): 1,
                    ("/api/health", "2xx"): 1}
    timed = {a["route"] for _, a in pts["studio.http.server.duration"]}
    assert "/api/health" not in timed and "/items/{item_id}" in timed
    assert all("abc" not in str(a) and "secret" not in str(a) for _, a in pts["studio.http.server.requests"])
    assert pts["studio.ws.connections"] == [(0, {})]


def test_http_middleware_passes_through_when_metrics_are_off():
    t = Telemetry(exporters=[], metric_readers=[]); c = TestClient(http_app(t))
    assert c.get("/items/1").json() == {"id": "1"} and not t.metrics_enabled


def test_reaped_and_recovered_jobs_are_counted():
    t, reader = meter()
    class Q(jq.InMemoryJobQueue):
        def reap(self): return 2
    w = RunWorker(Q(), lambda: None, telemetry=t)
    assert asyncio.run(w.reap()) == 2
    t.jobs("recovered", 3)
    pts = points(reader)
    assert pts["studio.jobs.reaped"] == [(2, {})] and pts["studio.jobs.recovered"] == [(3, {})]


class FakeDb:
    def ping(self): return True


class FakeRuns:
    def oldest_started(self, status): return time.time() - 30


def test_gauges_report_probes_queue_worker_and_process():
    t, reader = meter()
    q = jq.InMemoryJobQueue(); q.enqueue({"a": 1}); q.enqueue_at({"b": 1}, time.time() + 60); q.heartbeat(1, 2)
    w = RunWorker(q, lambda: None); w.busy, w.capacity = 1, 2
    t.watch(Probes(FakeDb(), FakeRuns(), q, InMemoryRunBus(), False, False), w)
    t.watch(Probes(FakeDb(), FakeRuns(), q, InMemoryRunBus(), False, False), w)  # once per process
    pts = points(reader); assert_bounded(pts)
    assert pts["studio.ready.db"] == [(1, {})] and "studio.ready.redis" not in pts  # Redis not configured
    depth = {a["state"]: v for v, a in pts["studio.queue.depth"]}
    assert depth == {"ready": 1, "delayed": 1, "processing": 0}
    assert pts["studio.queue.oldest_age"][0][0] >= 29 and pts["studio.worker.heartbeat_age"][0][0] < 5
    assert pts["studio.worker.busy"] == [(1, {})] and pts["studio.worker.capacity"] == [(2, {})]
    assert pts["studio.run_bus.in_memory"] == [(1, {})]
    assert pts["studio.process.rss"][0][0] > 0 and pts["studio.process.cpu_time"][0][0] > 0


def test_in_memory_flag_is_zero_with_redis():
    import fakeredis
    from app.services.run_bus import RedisRunBus
    t, reader = meter(); bus = RedisRunBus("redis://fake", client=fakeredis.FakeRedis(decode_responses=True))
    t.watch(Probes(FakeDb(), FakeRuns(), jq.InMemoryJobQueue(), bus, True, True))
    pts = points(reader)
    assert pts["studio.run_bus.in_memory"] == [(0, {})] and pts["studio.ready.redis"] == [(1, {})]
    assert "studio.worker.busy" not in pts  # no worker in this process


def test_studio_app_labels_routes_through_its_middleware(monkeypatch):
    from app.api import deps
    from app.main import app
    t, reader = meter(); monkeypatch.setattr(deps, "get_telemetry", lambda: t)
    c = TestClient(app)
    tok = c.post("/api/auth/register", json={"email": f"m{time.time_ns()}@example.com", "password": "secret12"}).json()["data"]["token"]
    wid = c.get("/api/workflows", headers={"Authorization": f"Bearer {tok}"}).json()["data"][0]["id"]
    assert c.get(f"/api/workflows/{wid}", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    routes = {a["route"] for _, a in points(reader)["studio.http.server.requests"]}
    assert {"/api/auth/register", "/api/workflows", "/api/workflows/{wid}"} <= routes and not any(wid in r for r in routes)
