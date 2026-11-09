"""token usage, per-run metrics, OpenTelemetry spans (in-memory exporter), clean no-op, history API."""
import asyncio, copy, json, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from app.engine import llm
from app.engine.examples import EXAMPLE
from app.engine.usage import make_usage, price_for
from app.main import app
from app.services import telemetry as tel
from app.services.telemetry import Telemetry, exporter_configs, summarize, trace_url

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def user():
    return c.post("/api/auth/register", json={"email": f"tel{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]

def run_ws(tok, wid, inp):
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": inp}); evs = []
        while True:
            evs.append(ws.receive_json())
            if evs[-1]["type"] == "run_summary": return evs


# ---- pricing / usage ----
def test_price_and_usage_record():
    assert price_for("gpt-4o-mini-2024-07-18") == (0.15, 0.60) and price_for("gpt-4o") == (2.50, 10.00) and price_for("llama3") is None
    u = make_usage("openai", "gpt-4o-mini", 1000, 500)
    assert u["tokens"] == 1500 and u["cost_usd"] == pytest.approx((1000 * 0.15 + 500 * 0.6) / 1e6)
    assert make_usage("openai", "local-model", 10, 10)["cost_usd"] is None
    assert make_usage("mock", "gpt-4o", 10, 10, estimated=True)["cost_usd"] == 0.0


def test_summarize_cost_unknown_propagates():
    evs = [{"type": "node_finished", "usage": make_usage("openai", "gpt-4o-mini", 100, 10)},
           {"type": "node_finished", "usage": make_usage("openai", "unknown", 5, 5)}, {"type": "error"}]
    m = summarize(evs, 0, 1.5)
    assert m == {"duration_ms": 1500.0, "tokens_in": 105, "tokens_out": 15, "cost_usd": None, "error_count": 1}
    assert summarize([{"type": "node_finished"}], 0, 1)["cost_usd"] == 0.0  # no LLM nodes -> free


# ---- env configuration / no-op ----
@pytest.fixture
def clean_env(monkeypatch):
    for k in ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "OTEL_SDK_DISABLED", "OTEL_TRACES_EXPORTER",
              "LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_ENDPOINT", "LANGSMITH_PROJECT", "STUDIO_TRACE_URL"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_no_exporter_is_a_clean_noop(clean_env):
    assert exporter_configs() == []
    t = Telemetry(); assert not t.enabled
    assert t.record_run({"id": "r", "status": "ok", "started": 0, "ended": 1}, [], summarize([], 0, 1)) is None
    assert trace_url("abc") is None


def test_exporter_configs_from_env(clean_env):
    clean_env.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    assert [x["name"] for x in exporter_configs()] == ["otlp"]
    clean_env.setenv("LANGSMITH_API_KEY", "lsv2_x")
    assert [x["name"] for x in exporter_configs()] == ["otlp"]  # LangSmith needs LANGSMITH_TRACING=true too
    clean_env.setenv("LANGSMITH_TRACING", "true"); clean_env.setenv("LANGSMITH_PROJECT", "studio")
    ls = exporter_configs()[1]
    assert ls["endpoint"] == "https://api.smith.langchain.com/otel/v1/traces" and ls["headers"] == {"x-api-key": "lsv2_x", "Langsmith-Project": "studio"}
    clean_env.setenv("OTEL_TRACES_EXPORTER", "none"); assert [x["name"] for x in exporter_configs()] == ["langsmith"]
    clean_env.setenv("OTEL_SDK_DISABLED", "true"); assert exporter_configs() == []
    clean_env.setenv("STUDIO_TRACE_URL", "http://localhost:16686/trace/{trace_id}")
    assert trace_url("ab12") == "http://localhost:16686/trace/ab12"


def test_env_exporters_build_otlp(clean_env):
    clean_env.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9")  # nothing listening; export is async + best effort
    t = Telemetry(); assert t.enabled and t.exporters == ["OTLPSpanExporter"]


# ---- spans ----
def _traced_service():
    from types import SimpleNamespace as NS
    from app.services.run_service import RunService
    exp = InMemorySpanExporter(); runs = []
    svc = RunService(None, NS(add=runs.append), telemetry=Telemetry(exporters=[exp], sync=True))
    return svc, exp, runs


def test_one_trace_per_run_one_span_per_node():
    svc, exp, runs = _traced_service(); sent = []
    from app.services.run_service import RunPlan
    plan = RunPlan("w1", EXAMPLE, {"message": "where is my order A100"})
    async def send(ev): sent.append(ev); return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.execute(plan, send, listen, "u1")) == "ok"
    spans = exp.get_finished_spans(); root = [s for s in spans if s.parent is None]
    assert len(root) == 1 and root[0].name == "run" and root[0].status.status_code == StatusCode.OK
    nodes = [s for s in spans if s.parent is not None]
    finished = [e for e in sent if e["type"] == "node_finished"]
    assert len(nodes) == len(finished) and {s.context.trace_id for s in spans} == {root[0].context.trace_id}
    llm_spans = [s for s in nodes if s.attributes["studio.node.type"] == "llm"]
    assert llm_spans and all(s.attributes["gen_ai.usage.input_tokens"] > 0 and s.attributes["studio.usage.estimated"] for s in llm_spans)
    assert all(s.end_time >= s.start_time and s.status.status_code == StatusCode.OK for s in nodes)
    summary = sent[-1]; assert summary["trace_id"] == format(root[0].context.trace_id, "032x")
    assert runs[0].trace_id == summary["trace_id"] and runs[0].error_count == 0 and root[0].attributes["studio.user.id"] == "u1"


def test_error_span_has_error_status():
    svc, exp, _ = _traced_service(); sent = []
    from app.services.run_service import RunPlan
    plan = RunPlan("w2", {}, {})
    plan.events = lambda: iter([{"type": "node_started", "node": "a"}, {"type": "error", "node": "a", "node_type": "tool", "duration_ms": 3, "errors": ["kaput"]}])
    async def send(ev): sent.append(ev); return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.execute(plan, send, listen, "u1")) == "error"
    spans = exp.get_finished_spans(); node = next(s for s in spans if s.parent is not None); root = next(s for s in spans if s.parent is None)
    assert node.status.status_code == StatusCode.ERROR and node.events[0].attributes["exception.message"] == "kaput"
    assert root.status.status_code == StatusCode.ERROR and root.attributes["studio.run.error_count"] == 1
    assert sent[-1]["metrics"]["error_count"] == 1


def test_tracing_failure_never_breaks_a_run():
    svc, _, runs = _traced_service()
    svc.telemetry.record_run = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("exporter down"))
    out = svc.record("r1", "w", {}, [], None, "ok", 0.0, "u1")
    assert out["trace_id"] is None and runs[0].status == "ok"


# ---- end to end over the API (mock mode, offline) ----
def test_ws_summary_and_history_metrics_mock_mode(clean_env):
    tok = user(); wid = c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
    evs = run_ws(tok, wid, {"message": "where is my order A100"})
    summary = evs[-1]; m = summary["metrics"]
    assert summary["status"] == "ok" and m["tokens"] > 0 and m["cost_usd"] == 0.0 and summary["trace_url"] is None
    llm_ev = [e for e in evs if e["type"] == "node_finished" and e.get("node_type") == "llm"]
    assert llm_ev and all(e["usage"]["provider"] == "mock" and e["usage"]["estimated"] for e in llm_ev)
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
    assert h["metrics"] == m and h["trace_id"] is None and h["trace_url"] is None
    assert all(e["type"] != "run_summary" for e in h["events"])  # summary is not stored as an event
    other = user()  # ownership: another user cannot read this history
    r = c.get(f"/api/workflows/{wid}/runs", headers=H(other)); assert r.status_code == 404 and r.json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


def test_openai_usage_and_cost_from_provider(monkeypatch):
    def handler(req):
        body = json.loads(req.content); p = body["messages"][0]["content"]
        return httpx.Response(200, json={"model": "gpt-4o-mini", "choices": [{"message": {"content": "order_status" if "Classify" in p else "ok"}}],
                                         "usage": {"prompt_tokens": 1000, "completion_tokens": 200}})
    monkeypatch.setattr(llm.providers, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    tok = user()
    cid = c.post("/api/credentials", json={"name": "o", "provider": "openai", "api_key": "sk-test-0123456789"}, headers=H(tok)).json()["data"]["id"]
    wf = copy.deepcopy(EXAMPLE)
    for n in wf["nodes"]:
        if n["type"] == "llm": n["data"].update(credential_id=cid)
    wid = c.post("/api/workflows", json=wf, headers=H(tok)).json()["data"]["id"]
    evs = run_ws(tok, wid, {"message": "A100?"}); m = evs[-1]["metrics"]
    n_llm = sum(1 for e in evs if e["type"] == "node_finished" and e.get("node_type") == "llm")  # only the branch taken runs
    assert n_llm >= 2 and m["tokens_in"] == 1000 * n_llm and m["tokens_out"] == 200 * n_llm
    assert m["cost_usd"] == pytest.approx(n_llm * (1000 * 0.15 + 200 * 0.6) / 1e6)


def test_health_reports_tracing():
    assert c.get("/api/health").json()["data"]["tracing"] in (True, False)
