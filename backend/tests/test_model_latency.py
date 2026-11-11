"""Per-call model latency and time to first token; embedding tokens and cost in metrics and in run totals."""
import json
import httpx, pytest, respx
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.engine import embeddings, llm, model_policy, providers
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.usage import make_usage, merge
from app.services.telemetry import LABELS, Telemetry, summarize

LM = "http://localhost:1234/v1"


def sse(parts):
    chunk = lambda p: {"id": "x", "object": "chat.completion.chunk", "created": 1, "model": "m", "choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}]}
    usage = {"id": "x", "object": "chat.completion.chunk", "created": 1, "model": "m", "choices": [], "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}}
    return "".join(f"data: {json.dumps(chunk(p))}\n\n" for p in parts) + f"data: {json.dumps(usage)}\n\ndata: [DONE]\n\n"


@pytest.fixture
def metered():
    reader = InMemoryMetricReader(); t = Telemetry(exporters=[], metric_readers=[reader])
    llm.observe(t.model_call); embeddings.observe(t.embedding_call)
    yield t, reader
    llm.unobserve(t.model_call); embeddings.unobserve(t.embedding_call)


def histograms(reader) -> dict:
    """{metric name: [(count, attributes)]}; counters as (value, attributes)."""
    out = {}
    data = reader.get_metrics_data()
    for rm in (data.resource_metrics if data else []):
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                for p in m.data.data_points:
                    out.setdefault(m.name, []).append((getattr(p, "count", getattr(p, "value", None)), dict(p.attributes)))
    return out


@respx.mock
def test_streamed_call_records_duration_and_ttft(metered):
    t, reader = metered
    respx.post(f"{LM}/chat/completions").respond(text=sse(["Hel", "lo"]), headers={"content-type": "text/event-stream"})
    usage, got = [], []
    assert llm.call_llm("hi", "m", {"provider": "lmstudio"}, usage.append, got.append) == "Hello"
    pts = histograms(reader)
    assert pts["studio.llm.duration"] == [(1, {"model": "m", "provider": "lmstudio", "status": "ok"})]
    assert pts["studio.llm.ttft"] == [(1, {"model": "m", "provider": "lmstudio", "status": "ok"})]
    assert usage[0]["duration_ms"] >= usage[0]["ttft_ms"] >= 0
    for items in pts.values():
        for _, a in items: assert set(a) <= LABELS and {"model", "provider"} <= set(a)


@respx.mock
def test_non_streamed_call_records_duration_only(metered):
    t, reader = metered
    respx.post(f"{LM}/chat/completions").respond(json={"id": "x", "object": "chat.completion", "created": 1, "model": "m",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "whole"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}})
    usage = []
    llm.call_llm("hi", "m", {"provider": "lmstudio"}, usage.append, None)
    pts = histograms(reader)
    assert [c for c, _ in pts["studio.llm.duration"]] == [1] and "studio.llm.ttft" not in pts
    assert "duration_ms" in usage[0] and "ttft_ms" not in usage[0]


def test_mock_calls_are_not_measured(metered):
    t, reader = metered
    llm.call_llm("hi", "gpt-4o-mini", None, None, lambda d: None, mock=True)
    assert "studio.llm.duration" not in histograms(reader)


@respx.mock
def test_failed_primary_and_fallback_record_two_durations(metered):
    t, reader = metered
    respx.post(f"{LM}/chat/completions").respond(429, json={"error": {"message": "slow down"}})
    respx.post("http://localhost:11434/api/chat").respond(json={"model": "llama3.2", "message": {"role": "assistant", "content": "ok"},
                                                              "done": True, "prompt_eval_count": 3, "eval_count": 1})
    creds = {"alt": {"provider": "ollama"}}
    data = {"model": "m", "fallback": {"model": "llama3.2", "credential_id": "alt"}}
    out = model_policy.run(data, {"provider": "lmstudio"}, creds.__getitem__,
                           lambda model, cred: llm.call_llm("hi", model, cred, None, None), None, lambda _: None)
    assert out == "ok"
    got = {(a["provider"], a["status"]) for _, a in histograms(reader)["studio.llm.duration"]}
    assert got == {("lmstudio", "PROVIDER_RATE_LIMITED"), ("ollama", "ok")}


def test_status_label_is_bounded():
    assert llm.call_status(providers.ProviderError("PROVIDER_UNREACHABLE", "x")) == "PROVIDER_UNREACHABLE"
    assert llm.call_status(ValueError("secret detail")) == "error"


def test_usage_merge_sums_durations_and_keeps_the_first_ttft():
    a = {**make_usage("openai", "gpt-4o", 1, 1), "duration_ms": 10.0, "ttft_ms": 2.0}
    b = {**make_usage("openai", "gpt-4o", 1, 1), "duration_ms": 5.0, "ttft_ms": 9.0}
    m = merge(a, b)
    assert m["duration_ms"] == 15.0 and m["ttft_ms"] == 2.0
    assert "duration_ms" not in merge(make_usage("x", "y", 1, 1), make_usage("x", "y", 1, 1))


# ---- embeddings ----

@respx.mock
def test_embedding_tokens_and_cost_by_source(metered):
    t, reader = metered
    respx.post(f"{LM}/embeddings").respond(json={"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [0.5]}],
                                                 "usage": {"prompt_tokens": 1000, "total_tokens": 1000}})
    embeddings.embed(["a", "b"], "text-embedding-3-small", {"provider": "lmstudio"})
    respx.post(f"{LM}/embeddings").respond(json={"data": [{"index": 0, "embedding": [1.0]}]})  # no usage: estimated
    embeddings.embed(["query"], "my-local-embedder", {"provider": "lmstudio"}, source="query")
    pts = histograms(reader)
    tokens = {(a["model"], a["source"]): v for v, a in pts["studio.embedding.tokens"]}
    assert tokens == {("text-embedding-3-small", "ingest"): 1000, ("my-local-embedder", "query"): 2}
    assert pts["studio.embedding.cost"] == [(pytest.approx(0.00002), {"model": "text-embedding-3-small", "provider": "lmstudio", "source": "ingest"})]
    assert pts["studio.embedding.unpriced"] == [(1, {"model": "my-local-embedder", "provider": "lmstudio", "source": "query"})]


def test_mock_embedder_records_nothing(metered, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    t, reader = metered
    assert len(embeddings.embed(["a"], None, None)[0]) == embeddings.MOCK_DIMS
    assert not any(k.startswith("studio.embedding") for k in histograms(reader))


@respx.mock
def test_ollama_reports_embedding_tokens():
    respx.post("http://localhost:11434/api/embed").respond(json={"embeddings": [[0.1]], "prompt_eval_count": 7})
    _, u = providers.get("ollama").embed_with_usage(["x"], "nomic-embed-text", {"provider": "ollama"})
    assert u["tokens_in"] == 7 and u["kind"] == "embedding" and not u["estimated"] and u["cost_usd"] is None


def rag_wf():
    return {"name": "rag", "state": [{"name": "question", "type": "string"}, {"name": "context", "type": "list"}],
            "nodes": [{"id": "start", "type": "start", "data": {}},
                      {"id": "r", "type": "retriever", "data": {"label": "Retrieve", "knowledge_base_id": "kb1", "query": "{{state.question}}",
                                                                "top_k": 2, "output_field": "context"}},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "r"}, {"id": "2", "source": "r", "target": "end"}]}


@respx.mock
def test_rag_run_counts_query_embedding_in_its_totals():
    respx.post(f"{LM}/embeddings").respond(json={"data": [{"index": 0, "embedding": [1.0]}], "usage": {"prompt_tokens": 50000}})
    def retrieve(kb, q, k):
        embeddings.embed([q], "text-embedding-3-small", {"provider": "lmstudio"}, source="query"); return [{"text": "hit", "score": 1.0}]
    evs = list(run_stream(rag_wf(), {"question": "refund?"}, ports=Ports(retrieve=retrieve)))
    fin = next(e for e in evs if e["type"] == "node_finished" and e["node"] == "r")
    assert "usage" not in fin and fin["embedding_usage"]["tokens_in"] == 50000 and fin["embedding_usage"]["kind"] == "embedding"
    m = summarize(evs, 0.0, 1.0)
    assert m["tokens_in"] == 50000 and m["tokens_out"] == 0 and m["cost_usd"] == pytest.approx(0.001)


def test_unpriced_embedding_adds_tokens_but_keeps_the_run_cost():
    e = {**make_usage("ollama", "nomic-embed-text", 12, 0), "kind": "embedding"}
    evs = [{"type": "node_finished", "node": "a", "usage": make_usage("openai", "gpt-4o", 1000, 0)},
           {"type": "node_finished", "node": "r", "embedding_usage": e}]
    m = summarize(evs, 0.0, 1.0)
    assert m["tokens_in"] == 1012 and m["cost_usd"] == pytest.approx(0.0025)
