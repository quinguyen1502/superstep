"""Run telemetry: per-run summary metrics + OpenTelemetry traces.

- `summarize(events, ...)` -> the metrics persisted on each run (duration, tokens, cost, error count).
- `Telemetry` turns a run's events into one trace: a root `run` span and one span per node
  (duration, status, error, gen_ai token usage, cost). Node spans are exported live as each node finishes
  ; the engine stays unaware of tracing.
- Exporters come from standard env: OTLP via OTEL_EXPORTER_OTLP_(TRACES_)ENDPOINT / OTEL_* and,
  optionally, LangSmith (its OTLP endpoint) when LANGSMITH_API_KEY is set and LANGSMITH_TRACING is true.
  With none configured (or OTEL_SDK_DISABLED=true) tracing is a no-op and the SDK is never imported.
- Optional spans (STUDIO_OTEL_INSTRUMENT=1 with a traces exporter): HTTP server spans by route template (probes left
  out), SQLAlchemy and Redis client spans without parameter values, under the request or run that made them. Client
  spans outside a request or run are dropped; LangSmith keeps receiving only run and node spans.
- Metrics (STUDIO_OTEL_METRICS=1 + an OTLP endpoint) are pushed to a collector: runs, model usage and errors, HTTP
  requests, jobs, and observable gauges for the readiness probes, the queue, the worker and the process. Every label
  goes through `labels`, which keeps only the bounded set in LABELS: never a user id, run id, raw path or prompt.
"""
from __future__ import annotations
import os, re, sys, threading, time, uuid
from contextlib import contextmanager
from typing import Any, Callable, Optional

TRUE = ("1", "true", "yes", "on")
LANGSMITH_DEFAULT = "https://api.smith.langchain.com"
# Metric labels: bounded values only. Per-user or per-team usage is SQL on the Usage page, never a label.
LABELS = frozenset({"status", "source", "workflow_id", "model", "provider", "code", "direction", "route", "method",
                    "status_class", "state", "primary_provider", "fallback_provider", "kind", "transport", "runtime",
                    "language", "scope"})
# Integration labels are fixed enums; any other value is exported as "other" (tests keep these lists in sync).
ENUMS = {"kind": frozenset({"email", "slack", "teams", "telegram", "webhook", "whatsapp"}),
         "transport": frozenset({"stdio", "http", "managed"}),
         "runtime": frozenset({"docker", "remote", "subprocess"}),
         "language": frozenset({"python", "typescript"}),
         "scope": frozenset({"demo", "approval_callback", "chat_trigger", "public_chat", "api_trigger", "code", "pat",
                             "email_node", "login", "identity_code", "other"})}
LLM_CODES = frozenset({"MODEL_NOT_FOUND"})  # with every PROVIDER_* code
SNAPSHOT_TTL = 5.0  # seconds one probe snapshot serves every gauge callback
PRODUCT_TTL = 30.0  # seconds between two product health queries (approvals, webhooks, schedules)
PROBE_ROUTES = frozenset({"/api/health", "/api/ready"})  # counted, kept out of the latency histogram (and never traced)
SCOPE = "superstep"  # instrumentation scope of run and node spans: the only spans LangSmith receives
HTTP_SCOPE = "superstep.http"
REDIS_KEY_PART = re.compile(r"^[a-z_]{1,24}$")  # key segments kept as the prefix: fixed words, never ids or names


def labels(**values: Any) -> dict:
    """Metric attributes restricted to LABELS; values become strings (None becomes "")."""
    out = {k: "" if v is None else str(v) for k, v in values.items() if k in LABELS}
    for k, allowed in ENUMS.items():
        if k in out and out[k] not in allowed: out[k] = "other"
    return out


def is_llm_code(code: Optional[str]) -> bool: return bool(code) and (code.startswith("PROVIDER_") or code in LLM_CODES)


def process_cpu_seconds() -> float:
    import resource
    u = resource.getrusage(resource.RUSAGE_SELF); return u.ru_utime + u.ru_stime


def process_rss_bytes() -> Optional[int]:
    """Resident set size from /proc (Linux); the peak from `resource` elsewhere."""
    try:
        with open("/proc/self/statm") as f: return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError, AttributeError):
        try:
            import resource, sys
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return peak if sys.platform == "darwin" else peak * 1024
        except Exception: return None


class _Snapshot:
    """Caches one call of `fn` for `ttl` seconds, so the gauges of one collection share a single probe round."""
    def __init__(self, fn: Callable[[], Optional[dict]], ttl: float = SNAPSHOT_TTL):
        self.fn, self.ttl, self.at, self.value, self._lock = fn, ttl, 0.0, None, threading.Lock()

    def get(self) -> Optional[dict]:
        with self._lock:
            if time.monotonic() - self.at >= self.ttl:
                try: self.value = self.fn()
                except Exception: self.value = None
                self.at = time.monotonic()
            return self.value


def summarize(events: list[dict], started: float, ended: float) -> dict:
    """Per-run summary metrics from the run's events (the same numbers the UI and the trace show)."""
    tin = tout = errors = 0; cost: Optional[float] = 0.0; llm = False
    waited = waited_s(events, ended)
    for ev in events:
        if ev.get("type") == "error": errors += 1
        u = ev.get("usage")
        if ev.get("type") in ("node_finished", "approval_review") and u and u.get("provider") != "workflow":  # a child run reports its own  # approval_review: the AI judge of a step
            llm = True; tin += u.get("tokens_in", 0); tout += u.get("tokens_out", 0)
            cost = None if cost is None or u.get("cost_usd") is None else cost + u["cost_usd"]
        e = ev.get("embedding_usage")
        if ev.get("type") == "node_finished" and e:  # query embeddings of Retriever nodes and knowledge tools: input tokens
            tin += int(e.get("tokens_in") or 0)
            if e.get("cost_usd"): llm = True; cost = None if cost is None else cost + e["cost_usd"]  # an unpriced embedding adds nothing
    return {"duration_ms": round(max(0.0, ended - started - waited) * 1000, 2), "tokens_in": tin, "tokens_out": tout,
            "cost_usd": (round(cost, 8) if cost is not None else None) if llm else 0.0, "error_count": errors}


def waited_s(events: list[dict], ended: float) -> float:
    """Seconds spent paused at Human nodes: from each `run_waiting` to the next event (resume/cancel/expiry).
    A run that is still waiting has no wait counted yet (its duration is the active time so far)."""
    total = 0.0; since = None; last = None
    for ev in events:
        if since is not None and ev.get("ts"):
            total += max(0.0, ev["ts"] - since); since = None
        elif ev.get("type") == "run_recovered" and ev.get("ts") and last:  # a dead worker's gap is not active time
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


def redis_key_prefix(args) -> str:
    """`studio:rl` for `studio:rl:email:<id>:<window>`: leading fixed words of the key, never the ids after them."""
    key = args[1] if len(args) > 1 and isinstance(args[1], (str, bytes)) else ""
    if isinstance(key, bytes): key = key.decode("utf-8", "replace")
    out = []
    for part in key.split(":")[:3]:
        if not REDIS_KEY_PART.match(part): break
        out.append(part)
    return ":".join(out)


def _redis_hook(span, _instance, args, _kwargs) -> None:
    if span is not None and span.is_recording() and (prefix := redis_key_prefix(args)): span.set_attribute("studio.redis.key_prefix", prefix)


def current_request() -> Optional[dict]:
    """{trace_id, span_id} of the request span in context (STUDIO_OTEL_INSTRUMENT), so a queued run can link to it."""
    if "opentelemetry.trace" not in sys.modules: return None
    from opentelemetry import trace
    span = trace.get_current_span(); c = span.get_span_context()
    if not (c.is_valid and span.is_recording()): return None
    return {"trace_id": format(c.trace_id, "032x"), "span_id": format(c.span_id, "016x")}


def _scoped(exporter, scopes=(SCOPE,)):
    """Wraps a span exporter so it only sees spans of `scopes` (LangSmith: run and node spans, no HTTP, SQL or Redis)."""
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    class Scoped(SpanExporter):
        def __init__(self, inner): self.inner = inner
        def export(self, spans):
            keep = [s for s in spans if s.instrumentation_scope is not None and s.instrumentation_scope.name in scopes]
            return self.inner.export(keep) if keep else SpanExportResult.SUCCESS
        def shutdown(self): return self.inner.shutdown()
        def force_flush(self, timeout_millis: int = 30000): return self.inner.force_flush(timeout_millis)
    return Scoped(exporter)


def _sampler():
    """Parent-based, always on, except that a database or Redis call outside any request or run is not traced."""
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON, Decision, ParentBased, Sampler, SamplingResult
    from opentelemetry.trace import SpanKind

    class NoOrphanClients(Sampler):
        def should_sample(self, parent_context, trace_id, name, kind=None, attributes=None, links=None, trace_state=None):
            if kind == SpanKind.CLIENT: return SamplingResult(Decision.DROP)
            return ALWAYS_ON.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
        def get_description(self) -> str: return "NoOrphanClients"
    return ParentBased(root=NoOrphanClients())


class RunScope:
    """Makes a run segment's root span the current span of the run's task (and of the engine thread, which copies the
    context), so SQL and Redis spans made while it executes join its trace. Detached when the scope ends."""
    def __init__(self, telemetry: "Telemetry"): self.telemetry, self.token = telemetry, None

    def enter(self, rs: Optional["RunSpan"]) -> None:
        if rs is None or self.token is not None or not self.telemetry.instrumented: return
        from opentelemetry import context
        self.token = context.attach(rs.ctx)

    def close(self) -> None:
        if self.token is None: return
        from opentelemetry import context
        try: context.detach(self.token)
        finally: self.token = None


class RunSpan:
    """Live root span of one run segment: node spans are exported as each node finishes."""
    def __init__(self, span, ctx, run: dict, name: str = "run", parent: Optional[dict] = None):
        self.span, self.ctx, self.run, self.name, self.parent = span, ctx, run, name, parent

    @property
    def ids(self) -> dict:
        c = self.span.get_span_context()
        return {"trace_id": format(c.trace_id, "032x"), "span_id": format(c.span_id, "016x")}

    @property
    def ref(self) -> dict:
        """What a checkpoint stores about this segment: enough to parent the next one AND to export this root span
        later if the worker dies before ending it."""
        p = {k: self.parent[k] for k in ("trace_id", "span_id")} if self.parent and self.parent.get("span_id") else None
        return {**self.ids, "name": self.name, "started": self.run["started"], "parent": p}


class _IdGenerator:
    """Random ids, except when `forced` (per thread) asks for given ones: used to export the root span of a segment
    whose worker died, with the very span id its already-exported node spans point to."""
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

    Spans are **live**: `start_run` opens the root span, `node` exports one span per finished/failed node
    right away (BatchSpanProcessor), and `end_run` closes the root with the run's totals. A paused (HITL) or
    recovered run continues the same trace: its new segment is a child of the previous root (`parent`).
    `record_run` does all three at once for runs that never executed live (e.g. cancelled while waiting).
    Optional OTel metrics (STUDIO_OTEL_METRICS=1 + an OTLP endpoint): runs, duration, tokens, cost, errors.
    Without exporters/readers everything is a no-op and the SDK is never imported."""

    def __init__(self, exporters: Optional[list] = None, sync: bool = False, metric_readers: Optional[list] = None,
                 instrument: Optional[bool] = None):
        self._tracer = None; self._provider = None; self._meter_provider = None; self._m: dict = {}
        if instrument is None:
            from ..core import config
            instrument = config.otel_instrument()
        if exporters is None: exporters = self._from_env()
        self.instrumented = bool(exporters) and bool(instrument)  # HTTP, SQL and Redis spans (opt-in)
        if metric_readers is None: metric_readers = self._metric_readers_from_env()
        if exporters or metric_readers:
            from opentelemetry.sdk.resources import Resource
            res = Resource.create({"service.name": _env("OTEL_SERVICE_NAME") or "superstep",
                                   "service.instance.id": uuid.uuid4().hex[:12]})  # API and worker processes stay apart
        if exporters:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
            self._ids = _IdGenerator()
            extra = {"sampler": _sampler()} if self.instrumented else {}
            self._provider = TracerProvider(resource=res, id_generator=self._ids, **extra)  # own provider: never touches the global one
            for ex in exporters: self._provider.add_span_processor(SimpleSpanProcessor(ex) if sync else BatchSpanProcessor(ex))
            self._tracer = self._provider.get_tracer(SCOPE)
            self._http_tracer = self._provider.get_tracer(HTTP_SCOPE)
            self.exporters = [type(e).__name__ for e in exporters]
        if metric_readers:
            from opentelemetry.sdk.metrics import MeterProvider
            self._meter_provider = MeterProvider(resource=res, metric_readers=metric_readers)
            m = self._meter_provider.get_meter("superstep")
            self._m = {"runs": m.create_counter("studio.runs", unit="{run}", description="Finished runs"),
                       "duration": m.create_histogram("studio.run.duration", unit="ms", description="Active run time"),
                       "tokens": m.create_counter("studio.tokens", unit="{token}", description="LLM tokens"),
                       "cost": m.create_counter("studio.cost", unit="USD", description="Estimated LLM cost"),
                       "errors": m.create_counter("studio.errors", unit="{error}", description="Error events"),
                       "llm_tokens": m.create_counter("studio.llm.tokens", unit="{token}", description="LLM tokens by model"),
                       "llm_cost": m.create_counter("studio.llm.cost", unit="USD", description="Estimated LLM cost by model (priced calls only)"),
                       "llm_unpriced": m.create_counter("studio.llm.unpriced", unit="{call}", description="LLM calls with no known price"),
                       "llm_errors": m.create_counter("studio.llm.errors", unit="{error}", description="Failed LLM calls by code"),
                       "llm_fallbacks": m.create_counter("studio.llm.fallbacks", unit="{call}", description="Calls answered by the fallback model"),
                       "llm_duration": m.create_histogram("studio.llm.duration", unit="ms", description="Time of one model call (each fallback attempt on its own)"),
                       "llm_ttft": m.create_histogram("studio.llm.ttft", unit="ms", description="Time to the first streamed token of one model call"),
                       "embedding_tokens": m.create_counter("studio.embedding.tokens", unit="{token}", description="Input tokens sent to embedding models"),
                       "embedding_cost": m.create_counter("studio.embedding.cost", unit="USD", description="Estimated embedding cost (priced models)"),
                       "embedding_unpriced": m.create_counter("studio.embedding.unpriced", unit="{call}", description="Embedding calls to models with no price"),
                       "channel_messages": m.create_counter("studio.channel.messages", unit="{message}", description="Channel messages sent and received (approvals, chat triggers)"),
                       "mcp_calls": m.create_counter("studio.mcp.calls", unit="{call}", description="MCP tool calls"),
                       "mcp_duration": m.create_histogram("studio.mcp.duration", unit="ms", description="Time of one MCP tool call"),
                       "browser_sessions": m.create_counter("studio.browser.sessions", unit="{session}", description="Browser sessions opened and ended"),
                       "browser_actions": m.create_counter("studio.browser.actions", unit="{action}", description="Browser actions by result"),
                       "sandbox_executions": m.create_counter("studio.sandbox.executions", unit="{execution}", description="Code node executions"),
                       "sandbox_duration": m.create_histogram("studio.sandbox.duration", unit="ms", description="Time of one Code node execution"),
                       "rate_limit_hits": m.create_counter("studio.rate_limit.hits", unit="{request}", description="Requests refused by a product limit"),
                       "http_requests": m.create_counter("studio.http.server.requests", unit="{request}", description="HTTP requests"),
                       "http_duration": m.create_histogram("studio.http.server.duration", unit="ms", description="HTTP request duration"),
                       "ws": m.create_up_down_counter("studio.ws.connections", unit="{connection}", description="Open WebSocket connections"),
                       "jobs_reaped": m.create_counter("studio.jobs.reaped", unit="{job}", description="Jobs requeued after their lease expired"),
                       "jobs_recovered": m.create_counter("studio.jobs.recovered", unit="{job}", description="Unfinished runs requeued at start-up")}
            self._meter = m
        self._watching = False

    @staticmethod
    def _from_env() -> list:
        cfgs = exporter_configs()
        if not cfgs: return []
        if any(c["name"] == "langsmith" for c in cfgs): disable_langchain_tracer()
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        return [OTLPSpanExporter() if c["name"] == "otlp" else _scoped(OTLPSpanExporter(endpoint=c["endpoint"], headers=c["headers"]))
                for c in cfgs]  # LangSmith: run and node spans only

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

    def start_run(self, run: dict, parent: Optional[dict] = None, links: Optional[list] = None,
                  request: Optional[dict] = None) -> Optional[RunSpan]:
        """Open the root span of a run segment. parent = {trace_id, span_id} of the previous segment (resume/recovery);
        links: span refs to link to (a recovered segment links the lost one, ). request: the HTTP span that queued the
        run; with STUDIO_OTEL_INSTRUMENT a run started inside a request links that request's span too."""
        if not self.enabled: return None
        from opentelemetry import trace
        from opentelemetry.context import Context
        from opentelemetry.trace import Link
        pctx = self._ctx(parent)
        name = "run" if pctx is None else f"run ({run.get('segment') or 'resumed'})"
        lk = [Link(sc, {"studio.link": "previous_segment"}) for sc in (self._sc(r) for r in links or []) if sc]
        if self.instrumented and (req := request or current_request()) and (sc := self._sc(req)):
            lk.append(Link(sc, {"studio.link": "request"}))
        root = self._tracer.start_span(name, context=pctx if pctx is not None else Context(), start_time=_ns(run["started"]), links=lk, attributes={
            "studio.run.id": run["id"], "studio.workflow.id": run.get("workflow_id") or "adhoc", "studio.user.id": run.get("owner") or ""})
        return RunSpan(root, trace.set_span_in_context(root), run, name, parent if pctx else None)

    def close_lost(self, ref: dict, ended: float) -> None:
        """Export the root span of a segment whose worker died before ending it: same trace and span id as
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
        a = labels(status=run["status"], source=run.get("source") or "ui", workflow_id=run.get("workflow_id") or "adhoc")
        self._m["runs"].add(1, a); self._m["duration"].record(metrics["duration_ms"], a)
        self._m["tokens"].add(metrics["tokens_in"], {**a, "direction": "input"}); self._m["tokens"].add(metrics["tokens_out"], {**a, "direction": "output"})
        if metrics.get("cost_usd"): self._m["cost"].add(metrics["cost_usd"], a)  # an unpriced run (cost None) is skipped
        if metrics["error_count"]: self._m["errors"].add(metrics["error_count"], a)

    # ---- opt-in HTTP, SQL and Redis spans ----
    def scope(self) -> RunScope: return RunScope(self)

    def instrument(self, engine=None) -> bool:
        """SQLAlchemy (this engine) and Redis client spans on this provider; once per process. No-op unless instrumented."""
        if not self.instrumented: return False
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy.engine import EngineTracer
        from opentelemetry.metrics import NoOpUpDownCounter
        if engine is not None and not getattr(engine, "_studio_traced", False):  # this engine only: no global create_engine patch
            EngineTracer(self._provider.get_tracer("opentelemetry.instrumentation.sqlalchemy"), engine,
                         NoOpUpDownCounter("db.client.connections.usage"), enable_commenter=False)
            engine._studio_traced = True
        if not RedisInstrumentor().is_instrumented_by_opentelemetry:
            RedisInstrumentor().instrument(tracer_provider=self._provider, request_hook=_redis_hook)
        return True

    @staticmethod
    def uninstrument() -> None:
        if "opentelemetry.instrumentation.sqlalchemy.engine" in sys.modules:
            from opentelemetry.instrumentation.sqlalchemy.engine import EngineTracer
            EngineTracer.remove_all_event_listeners()
        if "opentelemetry.instrumentation.redis" in sys.modules:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().uninstrument()

    def open_http(self, scope) -> Optional[tuple]:
        """Start the server span of a request (W3C `traceparent` honoured) and make it current. None when not
        instrumented or for the probe routes."""
        if not self.instrumented or scope["type"] not in ("http", "websocket") or scope.get("path") in PROBE_ROUTES: return None
        from opentelemetry import context, trace
        from opentelemetry.trace import SpanKind
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope.get("headers") or [] if k in (b"traceparent", b"tracestate")}
        method = scope.get("method") or "GET" if scope["type"] == "http" else "WS"
        span = self._http_tracer.start_span(method, context=TraceContextTextMapPropagator().extract(headers), kind=SpanKind.SERVER,
                                            attributes={"http.request.method": method, "url.scheme": scope.get("scheme") or "http"})
        return span, method, context.attach(trace.set_span_in_context(span))

    @staticmethod
    def close_http(handle: tuple, route: str, status: Optional[int]) -> None:
        from opentelemetry import context
        from opentelemetry.trace import Status, StatusCode
        span, method, token = handle
        try:
            span.update_name(f"{method} {route}"); span.set_attribute("http.route", route)
            if status is not None:
                span.set_attribute("http.response.status_code", status)
                if status >= 500: span.set_status(Status(StatusCode.ERROR))
            span.end()
        finally: context.detach(token)

    # ---- model, HTTP and job metrics ----
    def model_event(self, ev: dict, workflow_id: Optional[str]) -> None:
        """Per-model metrics from one run event: usage of a node or an AI review, failed attempts, fallbacks, LLM errors."""
        if not self._m: return
        wf = workflow_id or "adhoc"; u = ev.get("usage")
        if ev.get("type") in ("node_finished", "approval_review") and u and u.get("provider") != "workflow":  # a child run reports its own
            a = labels(model=u.get("model"), provider=u.get("provider"), workflow_id=wf)
            self._m["llm_tokens"].add(int(u.get("tokens_in") or 0), {**a, "direction": "input"})
            self._m["llm_tokens"].add(int(u.get("tokens_out") or 0), {**a, "direction": "output"})
            if u.get("cost_usd") is None: self._m["llm_unpriced"].add(1, labels(model=u.get("model"), provider=u.get("provider")))
            elif u["cost_usd"]: self._m["llm_cost"].add(u["cost_usd"], a)
        attempts = [x for x in ev.get("model_attempts") or [] if isinstance(x, dict)]
        failed = [x for x in attempts if x.get("status") == "error"]
        for x in failed: self._m["llm_errors"].add(1, labels(code=x.get("code"), provider=x.get("provider"), model=x.get("model")))
        answered = next((x for x in attempts if x.get("status") == "ok" and x.get("attempt") == 2), None)
        if answered and failed:
            self._m["llm_fallbacks"].add(1, labels(primary_provider=failed[0].get("provider"), fallback_provider=answered.get("provider"),
                                                   code=failed[0].get("code")))
        if ev.get("type") == "error" and not attempts and is_llm_code(ev.get("code")):
            self._m["llm_errors"].add(1, labels(code=ev["code"], provider=ev.get("provider") or "unknown", model=ev.get("model") or "unknown"))

    def embedding_call(self, u: dict) -> None:
        """One provider embedding call (engine.embeddings.observe), in a run or not: tokens and cost by model and source."""
        if not self._m: return
        a = labels(model=u.get("model"), provider=u.get("provider"), source=u.get("source") or "ingest")
        self._m["embedding_tokens"].add(int(u.get("tokens_in") or 0), a)
        if u.get("cost_usd") is None: self._m["embedding_unpriced"].add(1, a)
        elif u["cost_usd"]: self._m["embedding_cost"].add(u["cost_usd"], a)

    def activity_event(self, event: str, f: dict) -> None:
        """One integration event (engine.activity.emit) as counters and histograms; fields are bounded by `labels`."""
        if not self._m: return
        m = self._m
        if event == "channel": m["channel_messages"].add(1, labels(kind=f.get("kind"), direction=f.get("direction"), status=f.get("status")))
        elif event == "mcp":
            a = labels(transport=f.get("transport"), status=f.get("status"), code=f.get("code"))
            m["mcp_calls"].add(1, a); m["mcp_duration"].record(f.get("duration_ms") or 0.0, a)
        elif event == "browser_session": m["browser_sessions"].add(1, labels(status=f.get("status")))
        elif event == "browser_action": m["browser_actions"].add(1, labels(status=f.get("status"), code=f.get("code")))
        elif event == "sandbox":
            a = labels(runtime=f.get("runtime"), language=f.get("language"), status=f.get("status"))
            m["sandbox_executions"].add(1, a); m["sandbox_duration"].record(f.get("duration_ms") or 0.0, a)
        elif event == "rate_limit": m["rate_limit_hits"].add(1, labels(scope=f.get("scope")))

    def model_call(self, rec: dict) -> None:
        """One measured provider call (engine.llm.observe): duration, and time to first token for streamed calls."""
        if not self._m or rec.get("kind") != "llm": return
        a = labels(model=rec.get("model"), provider=rec.get("provider"), status=rec.get("status") or "ok")
        if rec.get("duration_ms") is not None: self._m["llm_duration"].record(rec["duration_ms"], a)
        if rec.get("ttft_ms") is not None: self._m["llm_ttft"].record(rec["ttft_ms"], a)

    def http_request(self, route: str, method: str, status: int, ms: float) -> None:
        if not self._m: return
        a = labels(route=route, method=method, status_class=f"{status // 100}xx")
        self._m["http_requests"].add(1, a)
        if route not in PROBE_ROUTES: self._m["http_duration"].record(ms, a)

    def websocket(self, delta: int) -> None:
        if self._m: self._m["ws"].add(delta)

    def jobs(self, kind: str, n: int) -> None:
        """`kind`: reaped (lease expired) or recovered (requeued at start-up)."""
        if self._m and n: self._m[f"jobs_{kind}"].add(n)

    def watch(self, probes, worker=None, product: Optional[Callable[[], Optional[dict]]] = None,
              pool: Optional[Callable[[], dict]] = None) -> None:
        """Observable gauges, read at each export: readiness probes, queue and heartbeat (every process), busy slots and
        capacity of this process's worker, process CPU and memory, this process's SQLAlchemy pool (`pool()`:
        Database.pool_status) and, where a worker runs, the product health counts from `product()` (UsageService.gauges).
        Once per process; a no-op without metrics."""
        if not self._m or self._watching: return
        from opentelemetry.metrics import Observation
        self._watching = True; m = self._meter; snap = _Snapshot(probes.ready)

        def gauge(name: str, unit: str, desc: str, read: Callable[[], list]) -> None:
            def cb(_options):  # runs on the exporter thread, never on the event loop
                try: return [Observation(v, a) for v, a in read() if v is not None]
                except Exception: return []
            m.create_observable_gauge(name, callbacks=[cb], unit=unit, description=desc)

        def part(key: str) -> dict: return (snap.get() or {}).get(key) or {}
        def ok(key: str) -> list:
            v = part(key).get("ok"); return [] if v is None else [(1 if v else 0, {})]
        gauge("studio.ready.db", "1", "Database probe (1 ok, 0 failing)", lambda: ok("database"))
        gauge("studio.ready.db.latency", "ms", "Database probe latency", lambda: [(part("database").get("latency_ms"), {})])
        gauge("studio.ready.redis", "1", "Redis probe when REDIS_URL is set (1 ok, 0 failing)", lambda: ok("redis"))
        gauge("studio.ready.redis.latency", "ms", "Redis probe latency", lambda: [(part("redis").get("latency_ms"), {})])
        gauge("studio.queue.depth", "{job}", "Jobs by state", lambda: [(part("queue").get(s), labels(state=s)) for s in ("ready", "delayed", "processing")])
        gauge("studio.queue.oldest_age", "s", "Age of the oldest queued run", lambda: [(part("queue").get("oldest_queued_age_s"), {})])
        gauge("studio.worker.heartbeat_age", "s", "Age of the newest worker heartbeat", lambda: [(part("worker").get("heartbeat_age_s"), {})])
        gauge("studio.run_bus.in_memory", "1", "1 when the run bus is in-memory (no REDIS_URL)", lambda: [(1 if (snap.get() or {}).get("run_bus") == "memory" else 0, {})])
        if worker is not None:
            gauge("studio.worker.busy", "{slot}", "Busy job slots of this worker", lambda: [(worker.busy, {})])
            gauge("studio.worker.capacity", "{slot}", "Job slots of this worker", lambda: [(worker.capacity, {})])
        gauge("studio.process.rss", "By", "Resident memory of this process", lambda: [(process_rss_bytes(), {})])
        if pool is not None:  # no probe here: the pool's own counters, read without a database round trip
            gauge("studio.db.pool.in_use", "{connection}", "Database connections checked out of this process's pool", lambda: [(pool().get("in_use"), {})])
            gauge("studio.db.pool.idle", "{connection}", "Idle database connections in this process's pool", lambda: [(pool().get("idle"), {})])
            gauge("studio.db.pool.overflow", "{connection}", "Connections beyond the pool size in this process", lambda: [(pool().get("overflow"), {})])
        m.create_observable_counter("studio.process.cpu_time", unit="s", description="CPU time of this process",
                                    callbacks=[lambda _o: [Observation(process_cpu_seconds())]])
        if worker is None or product is None: return
        health = _Snapshot(product, PRODUCT_TTL)
        def count(group: str, key: str) -> list: return [(((health.get() or {}).get(group) or {}).get(key), {})]
        gauge("studio.approvals.waiting", "{approval}", "Human steps waiting for an answer", lambda: count("approvals", "waiting"))
        gauge("studio.approvals.oldest_age", "s", "Age of the oldest waiting human step", lambda: count("approvals", "oldest_age_s"))
        gauge("studio.webhooks.failed", "{delivery}", "Webhook deliveries that failed in the last hour", lambda: count("webhooks", "failed"))
        gauge("studio.webhooks.retrying", "{delivery}", "Webhook deliveries waiting for a retry", lambda: count("webhooks", "retrying"))
        gauge("studio.schedules.overdue", "{schedule}", "Enabled schedules more than 5 minutes late", lambda: count("schedules", "overdue"))
        gauge("studio.schedules.disabled", "{schedule}", "Schedules the scheduler turned off", lambda: count("schedules", "disabled"))
        gauge("studio.browser.active", "{session}", "Browser sessions open now (all processes)", lambda: count("browsers", "active"))
