# Decision

- Decision ID: DEC-0094
- Project: superstep
- Status: Proposed 2026-11-09, recommendation A, awaiting owner acceptance with REQ-0094
- Created/Updated: 2026-11-09
- Related: REQ-0094, PLAN-0013, TASK-0285, TASK-0291

## Context

- The backend already depends on `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`, builds its own `MeterProvider` in `services/telemetry.py` when `STUDIO_OTEL_METRICS=1` and an OTLP endpoint are set, and exports with `PeriodicExportingMetricReader(OTLPMetricExporter())`.
- There is no `prometheus_client` and no `/metrics` route. Docker Compose has Jaeger under the `tracing` profile receiving OTLP on 4318.
- The API and the worker can run as separate processes (`STUDIO_WORKER=0` on the API, a worker service in Compose), and deployments may run several replicas.
- The owner chose OpenTelemetry for tracing, with LangSmith optional.

## Options

- **A (recommended): OTel push to an OpenTelemetry Collector.** Every process pushes OTLP metrics; the collector's Prometheus exporter exposes them on one endpoint that Prometheus scrapes; Grafana reads Prometheus (and Jaeger for traces). Reuses the existing reader, dependency and env vars; works the same for API, worker and replicas without per-process scrape targets; the collector can also forward traces to Jaeger, Tempo or a vendor. Cost: one more container in the Compose profile, and metrics need `STUDIO_OTEL_METRICS=1` plus an endpoint.
- **B: in-process Prometheus `/metrics`** via `prometheus_client` or the OTel Prometheus reader. Simple for one process, but needs a scrape target per process and replica, multiprocess mode for several uvicorn workers, a route that must be protected, and a second metrics configuration next to OTLP.
- **C: both A and B.** Most flexible, most surface; no current need.

## Decision

Option A. `/metrics` is not added in the MVP; if a deployment cannot run a collector, an OTel Prometheus reader behind an opt-in flag can be added later without changing metric names.

Consequences:

- `STUDIO_OTEL_METRICS` stays opt-in (default off) so installs without a collector do not log export failures; the Compose `observability` profile and the handbook turn it on.
- Metric names keep the `studio.` prefix; Prometheus sees them as `studio_*` with unit suffixes added by the collector. The starter dashboard uses those names.
- Gauges (queue depth, heartbeat age, process CPU/RSS) are OTel observable gauges registered on the same meter; callbacks never block the event loop and use short timeouts.
- Process CPU/RSS come from the standard library (`resource`, `/proc` on Linux) to avoid a new dependency; host metrics stay with the platform or the collector's host metrics receiver.
