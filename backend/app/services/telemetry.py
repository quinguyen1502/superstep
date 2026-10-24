"""Run telemetry (TASK-0010, DEC-0012): per-run summary metrics + OpenTelemetry traces.

- `summarize(events, ...)` -> the metrics persisted on each run (duration, tokens, cost, error count).
- `Telemetry` turns a run's events into one trace: a root `run` span and one span per node
  (duration, status, error, gen_ai token usage, cost). Node spans are exported live as each node finishes
  (TASK-0020); the engine stays unaware of tracing.
- Exporters come from standard env: OTLP via OTEL_EXPORTER_OTLP_(TRACES_)ENDPOINT / OTEL_* and,
  optionally, LangSmith (its OTLP endpoint) when LANGSMITH_API_KEY is set and LANGSMITH_TRACING is true.
  With none configured (or OTEL_SDK_DISABLED=true) tracing is a no-op and the SDK is never imported.
"""
from __future__ import annotations
import os, threading
from typing import Any, Optional

TRUE = ("1", "true", "yes", "on")
LANGSMITH_DEFAULT = "https://api.smith.langchain.com"


def summarize(events: list[dict], started: float, ended: float) -> dict:
    """Per-run summary metrics from the run's events (the same numbers the UI and the trace show)."""
    tin = tout = errors = 0; cost: Optional[float] = 0.0; llm = False
    waited = waited_s(events, ended)
    for ev in events:
        if ev.get("type") == "error": errors += 1
        u = ev.get("usage")
        if ev.get("type") == "node_finished" and u:
            llm = True; tin += u.get("tokens_in", 0); tout += u.get("tokens_out", 0)
            cost = None if cost is None or u.get("cost_usd") is None else cost + u["cost_usd"]
    return {"duration_ms": round(max(0.0, ended - started - waited) * 1000, 2), "tokens_in": tin, "tokens_out": tout,
            "cost_usd": (round(cost, 8) if cost is not None else None) if llm else 0.0, "error_count": errors}


def waited_s(events: list[dict], ended: float) -> float:
    """Seconds spent paused at Human nodes: from each `run_waiting` to the next event (resume/cancel/expiry).
    A run that is still waiting has no wait counted yet (its duration is the active time so far)."""
    total = 0.0; since = None; last = None
    for ev in events:
        if since is not None and ev.get("ts"):
            total += max(0.0, ev["ts"] - since); since = None
        elif ev.get("type") == "run_recovered" and ev.get("ts") and last:  # a dead worker's gap is not active time (TASK-0020)
            total += max(0.0, ev["ts"] - last)
        if ev.get("type") == "run_waiting" and ev.get("ts"): since = ev["ts"]
        if ev.get("ts"): last = ev["ts"]
    return total + (max(0.0, ended - since) if since is not None else 0.0)


def _env(name: str) -> str: return (os.environ.get(name) or "").strip()


def exporter_configs() -> list[dict]:
    """Which span exporters the environment asks for (pure; no SDK import)."""
    if _env("OTEL_SDK_DISABLED").lower() in TRUE: return []
    out = []
    if (_env("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or _env("OTEL_EXPORTER_OTLP_ENDPOINT")) and _env("OTEL_TRACES_EXPORTER").lower() != "none":
        out.append({"name": "otlp"})  # the OTLP exporter reads OTEL_EXPORTER_OTLP_* itself (endpoint, headers, timeout)
    if _env("LANGSMITH_API_KEY") and _env("LANGSMITH_TRACING").lower() in TRUE:
        base = (_env("LANGSMITH_ENDPOINT") or LANGSMITH_DEFAULT).rstrip("/")
        headers = {"x-api-key": _env("LANGSMITH_API_KEY")}
        if _env("LANGSMITH_PROJECT"): headers["Langsmith-Project"] = _env("LANGSMITH_PROJECT")
        out.append({"name": "langsmith", "endpoint": f"{base}/otel/v1/traces", "headers": headers})
    return out


def disable_langchain_tracer() -> None:
    """We export to LangSmith ourselves (OTLP). LANGSMITH_TRACING=true would ALSO switch on LangChain's own
    LangSmith tracer inside nodes, so every LLM call would show up twice. Turn that one off:
    LANGSMITH_TRACING_V2 takes precedence over LANGSMITH_TRACING (and is inherited by import sandboxes),
    and langsmith.configure(enabled=False) covers already-loaded code."""
    os.environ["LANGSMITH_TRACING_V2"] = "false"; os.environ["LANGCHAIN_TRACING_V2"] = "false"
    try:
        import langsmith
        from langsmith import utils as ls_utils
        ls_utils.get_env_var.cache_clear()
        langsmith.configure(enabled=False)
    except Exception:  # langsmith not installed / older API: the env vars are enough
        pass


def trace_url(trace_id: Optional[str], root: Optional[str] = None) -> Optional[str]:
    """Link to the trace viewer when STUDIO_TRACE_URL (e.g. http://localhost:16686/trace/{trace_id}) is set, else to
    the run in LangSmith when tracing goes there (`root`: the span id of the trace's root span)."""
    tpl = _env("STUDIO_TRACE_URL")
    if tpl: return tpl.replace("{trace_id}", trace_id) if trace_id else None
    from .langsmith import run_url
    return run_url(root) if trace_id else None


def _ns(seconds: float) -> int: return int(seconds * 1e9)


class RunSpan:
    """Live root span of one run segment (TASK-0020): node spans are exported as each node finishes."""
    def __init__(self, span, ctx, run: dict, name: str = "run", parent: Optional[dict] = None):
        self.span, self.ctx, self.run, self.name, self.parent = span, ctx, run, name, parent

    @property
    def ids(self) -> dict:
        c = self.span.get_span_context()
        return {"trace_id": format(c.trace_id, "032x"), "span_id": format(c.span_id, "016x")}

    @property
    def ref(self) -> dict:
        """What a checkpoint stores about this segment: enough to parent the next one AND to export this root span
        later if the worker dies before ending it (TASK-0021)."""
        p = {k: self.parent[k] for k in ("trace_id", "span_id")} if self.parent and self.parent.get("span_id") else None
        return {**self.ids, "name": self.name, "started": self.run["started"], "parent": p}


class _IdGenerator:
    """Random ids, except when `forced` (per thread) asks for given ones: used to export the root span of a segment
    whose worker died, with the very span id its already-exported node spans point to (TASK-0021)."""
    def __init__(self):
        from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
        self._rand = RandomIdGenerator(); self._forced = threading.local()

    def force(self, trace_id: Optional[int], span_id: Optional[int]) -> None: self._forced.ids = (trace_id, span_id)

    def generate_trace_id(self) -> int:
        f = getattr(self._forced, "ids", None)
        return f[0] if f and f[0] else self._rand.generate_trace_id()

    def is_trace_id_random(self) -> bool: return True

    def generate_span_id(self) -> int:
        f = getattr(self._forced, "ids", None)
        if f and f[1]: self._forced.ids = None; return f[1]
        return self._rand.generate_span_id()


class Telemetry:
    """Built once per process (api.deps.get_telemetry). `exporters` / `metric_readers` let tests inject in-memory ones.

    Spans are **live** (TASK-0020): `start_run` opens the root span, `node` exports one span per finished/failed node
    right away (BatchSpanProcessor), and `end_run` closes the root with the run's totals. A paused (HITL) or
    recovered run continues the same trace: its new segment is a child of the previous root (`parent`).
    `record_run` does all three at once for runs that never executed live (e.g. cancelled while waiting).
    Optional OTel metrics (STUDIO_OTEL_METRICS=1 + an OTLP endpoint): runs, duration, tokens, cost, errors.
    Without exporters/readers everything is a no-op and the SDK is never imported."""

    def __init__(self, exporters: Optional[list] = None, sync: bool = False, metric_readers: Optional[list] = None):
        self._tracer = None; self._provider = None; self._meter_provider = None; self._m: dict = {}
        if exporters is None: exporters = self._from_env()
        if metric_readers is None: metric_readers = self._metric_readers_from_env()
        if exporters or metric_readers:
            from opentelemetry.sdk.resources import Resource
            res = Resource.create({"service.name": _env("OTEL_SERVICE_NAME") or "superstep"})
        if exporters:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
            self._ids = _IdGenerator()
            self._provider = TracerProvider(resource=res, id_generator=self._ids)  # own provider: never touches the global one
            for ex in exporters: self._provider.add_span_processor(SimpleSpanProcessor(ex) if sync else BatchSpanProcessor(ex))
            self._tracer = self._provider.get_tracer("superstep")
            self.exporters = [type(e).__name__ for e in exporters]
        if metric_readers:
            from opentelemetry.sdk.metrics import MeterProvider
            self._meter_provider = MeterProvider(resource=res, metric_readers=metric_readers)
            m = self._meter_provider.get_meter("superstep")
            self._m = {"runs": m.create_counter("studio.runs", unit="{run}", description="Finished runs"),
                       "duration": m.create_histogram("studio.run.duration", unit="ms", description="Active run time"),
                       "tokens": m.create_counter("studio.tokens", unit="{token}", description="LLM tokens"),
                       "cost": m.create_counter("studio.cost", unit="USD", description="Estimated LLM cost"),
                       "errors": m.create_counter("studio.errors", unit="{error}", description="Error events")}

    @staticmethod
    def _from_env() -> list:
        cfgs = exporter_configs()
        if not cfgs: return []
        if any(c["name"] == "langsmith" for c in cfgs): disable_langchain_tracer()
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        return [OTLPSpanExporter() if c["name"] == "otlp" else OTLPSpanExporter(endpoint=c["endpoint"], headers=c["headers"])
                for c in cfgs]

    @staticmethod
    def _metric_readers_from_env() -> list:
        from ..core import config
        if not config.otel_metrics() or _env("OTEL_SDK_DISABLED").lower() in TRUE: return []
        if not (_env("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or _env("OTEL_EXPORTER_OTLP_ENDPOINT")): return []
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        return [PeriodicExportingMetricReader(OTLPMetricExporter())]  # interval: OTEL_METRIC_EXPORT_INTERVAL

    @property
    def enabled(self) -> bool: return self._tracer is not None

    @property
    def metrics_enabled(self) -> bool: return bool(self._m)

    def flush(self) -> None:
        if self._provider: self._provider.force_flush()
        if self._meter_provider: self._meter_provider.force_flush()

    # ---- live spans ----
    @staticmethod
    def _sc(ref: Optional[dict]):
        if not (ref and ref.get("trace_id") and ref.get("span_id")): return None
        from opentelemetry.trace import SpanContext, TraceFlags
        return SpanContext(int(ref["trace_id"], 16), int(ref["span_id"], 16), is_remote=True, trace_flags=TraceFlags(TraceFlags.SAMPLED))

    def _ctx(self, ref: Optional[dict]):
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan
        sc = self._sc(ref)
        return trace.set_span_in_context(NonRecordingSpan(sc)) if sc else None

    def start_run(self, run: dict, parent: Optional[dict] = None, links: Optional[list] = None) -> Optional[RunSpan]:
        """Open the root span of a run segment. parent = {trace_id, span_id} of the previous segment (resume/recovery);
        links: span refs to link to (a recovered segment links the lost one, TASK-0021)."""
        if not self.enabled: return None
        from opentelemetry import trace
        from opentelemetry.trace import Link
        pctx = self._ctx(parent)
        name = "run" if pctx is None else f"run ({run.get('segment') or 'resumed'})"
        lk = [Link(sc, {"studio.link": "previous_segment"}) for sc in (self._sc(r) for r in links or []) if sc]
        root = self._tracer.start_span(name, context=pctx, start_time=_ns(run["started"]), links=lk, attributes={
            "studio.run.id": run["id"], "studio.workflow.id": run.get("workflow_id") or "adhoc", "studio.user.id": run.get("owner") or ""})
        return RunSpan(root, trace.set_span_in_context(root), run, name, parent if pctx else None)

    def close_lost(self, ref: dict, ended: float) -> None:
        """Export the root span of a segment whose worker died before ending it (TASK-0021): same trace and span id as
        stored in its checkpoint, so its node spans (exported live) get their parent; status ERROR "worker lost"."""
        if not self.enabled or not (ref and ref.get("span_id") and ref.get("started")): return
        from opentelemetry.trace import Status, StatusCode
        self._ids.force(int(ref["trace_id"], 16), int(ref["span_id"], 16))
        try: span = self._tracer.start_span(ref.get("name") or "run", context=self._ctx(ref.get("parent")), start_time=_ns(ref["started"]),
                                            attributes={"studio.run.lost": True, "studio.run.status": "lost"})
        finally: self._ids.force(None, None)
        span.set_status(Status(StatusCode.ERROR, "worker lost the run; continued in a recovered segment"))
        span.end(end_time=_ns(max(ended, ref["started"])))

    def node(self, rs: Optional[RunSpan], ev: dict) -> None:
        """Export one node span now (node_finished or a node error)."""
        if rs is None or ev.get("type") not in ("node_finished", "error") or not ev.get("node"): return
        from opentelemetry.trace import Status, StatusCode
        end = ev.get("ts") or rs.run.get("ended") or rs.run["started"]; start = end - (ev.get("duration_ms") or 0) / 1000
        attrs: dict[str, Any] = {"studio.node.id": ev["node"], "studio.node.type": ev.get("node_type") or "",
                                 "studio.node.label": ev.get("label") or "", "studio.node.iteration": ev.get("iteration") or 1,
                                 "studio.node.duration_ms": ev.get("duration_ms") or 0}
        if (u := ev.get("usage")):
            attrs.update({"gen_ai.system": u["provider"], "gen_ai.request.model": u["model"],
                          "gen_ai.usage.input_tokens": u["tokens_in"], "gen_ai.usage.output_tokens": u["tokens_out"],
                          "studio.usage.estimated": u["estimated"]})
            if u["cost_usd"] is not None: attrs["studio.cost_usd"] = u["cost_usd"]
        span = self._tracer.start_span(f"node {ev.get('label') or ev['node']}", context=rs.ctx, start_time=_ns(start), attributes=attrs)
        if ev["type"] == "error":
            err = ev.get("error") or {}
            span.set_status(Status(StatusCode.ERROR, err.get("message") or ""))
            span.add_event("exception", {"exception.type": err.get("code") or "NODE_FAILED", "exception.message": err.get("message") or ""})
        else:
            span.set_status(Status(StatusCode.OK))
        span.end(end_time=_ns(end))

    def end_run(self, rs: Optional[RunSpan], run: dict, metrics: dict, observe: bool = True) -> Optional[str]:
        """Close the root span with the run totals; record metrics for finished runs. Returns the trace id."""
        if observe: self.observe(run, metrics)
        if rs is None: return None
        from opentelemetry.trace import Status, StatusCode
        root = rs.span
        for k, v in {"studio.run.status": run["status"], "studio.run.error_count": metrics["error_count"],
                     "gen_ai.usage.input_tokens": metrics["tokens_in"], "gen_ai.usage.output_tokens": metrics["tokens_out"]}.items():
            root.set_attribute(k, v)
        if metrics.get("cost_usd") is not None: root.set_attribute("studio.cost_usd", metrics["cost_usd"])
        if run["status"] == "ok": root.set_status(Status(StatusCode.OK))
        elif run["status"] in ("error", "timeout"): root.set_status(Status(StatusCode.ERROR, run["status"]))  # cancelled/waiting stay UNSET
        root.end(end_time=_ns(run["ended"]))
        return rs.ids["trace_id"]

    def record_run(self, run: dict, events: list[dict], metrics: dict, parent: Optional[dict] = None) -> Optional[str]:
        """Post-hoc trace for a run that did not execute live. Returns the trace id (32 hex chars) or None when disabled."""
        rs = self.start_run(run, parent)
        for ev in events: self.node(rs, ev)
        return self.end_run(rs, run, metrics)

    def observe(self, run: dict, metrics: dict) -> None:
        """OTel metrics for a run that reached a final status (a pause is not counted)."""
        if not self._m or run["status"] == "waiting": return
        a = {"status": run["status"], "source": run.get("source") or "ui"}
        self._m["runs"].add(1, a); self._m["duration"].record(metrics["duration_ms"], a)
        self._m["tokens"].add(metrics["tokens_in"], {**a, "direction": "input"}); self._m["tokens"].add(metrics["tokens_out"], {**a, "direction": "output"})
        if metrics.get("cost_usd"): self._m["cost"].add(metrics["cost_usd"], a)
        if metrics["error_count"]: self._m["errors"].add(metrics["error_count"], a)
