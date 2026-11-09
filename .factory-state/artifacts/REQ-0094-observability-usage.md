# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0094
- Status: Proposed, awaiting owner acceptance (pt274u: "OK, plan the implementation"). Direction already agreed in chat on 2026-11-09; nothing is implemented by this requirement's planning PR.
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-09
- Source: Owner chat 2026-11-09: observability research (pt271u), placement and preview (pt272u), Grafana versus in-app split (pt273u), plan request (pt274u)
- Related: DES-0006, DEC-0094, DEC-0095, PLAN-0013, TASK-0284 to TASK-0293

## Summary And Scope

Superstep records good per-run data (status, duration, `tokens_in`/`tokens_out`, `cost_usd`, `error_count`, one OTel trace per run) and five optional OTel metrics (`studio.runs`, `studio.run.duration`, `studio.tokens`, `studio.cost`, `studio.errors`, labels `status` and `source` only). It has no operator view of the server, database, Redis, queue or workers, and no in-app view of usage and cost across runs. This requirement adds both, on one instrumentation layer:

1. **Honest health and readiness.** `GET /api/ready` next to `GET /api/health` in `backend/app/api/routes/meta.py`. Readiness queries the database (`SELECT 1` with latency), pings Redis when configured, reads queue depth (ready, delayed, processing), the oldest queued run, and the worker's last heartbeat. `/api/health` stays liveness. Today `/api/health` hard-codes `ok: true` and never queries the database, so Docker, Render and DigitalOcean health checks stay green while the database is down; readiness fixes that without silently changing liveness (DEC-0095).
2. **One metrics surface.** Extend `backend/app/services/telemetry.py` (existing OTel traces and run metrics). Metrics leave the process over OTLP to an OpenTelemetry Collector, which Prometheus scrapes and Grafana reads (DEC-0094). LangSmith stays an optional trace destination. No separate microservice.
3. **Operator metrics** for Grafana: HTTP request rate, latency and 5xx by route template; queue depth, delayed and processing jobs, oldest queued age, busy worker slots against `STUDIO_WORKER_CONCURRENCY`, reaped/recovered jobs, worker heartbeat age; process CPU and RSS; database and Redis probe latency and failures; a flag when the in-memory run bus is used in production.
4. **Model metrics.** Labels `model`, `provider`, `workflow_id` on token and cost metrics; LLM error counter by code; fallback counter; unpriced-usage counter; a distinct provider rate-limit code for HTTP 429 (today 429 and 5xx both map to `PROVIDER_BAD_RESPONSE`).
5. **In-app Usage page.** A Settings section at `/settings/usage`, next to Activity (`/settings/activity`), permission `users.manage`, backed by `GET /api/admin/usage`. It shows run outcomes, tokens, cost, top workflows and the share of runs whose cost is unknown, aggregated in SQL from existing `runs` columns. Per-run totals stay on the existing run panel.
6. **Product health panels** derivable from existing tables: waiting approvals (count, oldest), expired approvals, webhook deliveries failed or retrying, overdue schedules and schedules the scheduler disabled (with `note`).
7. **Grafana starter kit.** A Compose profile next to the Jaeger `tracing` profile with the collector, Prometheus and Grafana, a provisioned starter dashboard and alert rules.
8. **Handbook.** `handbook/docs/en/operate/observability.md` and the Vietnamese edition updated together, including the minimum alert list.

Out of scope for this requirement (later phases in PLAN-0013): JSON logs with `run_id`/`request_id`/`trace_id`; HTTP/SQL/Redis spans on the run traces; Postgres/Redis exporters and SQLAlchemy pool metrics; per-call LLM latency and time to first token; embedding usage; channel, MCP, browser and sandbox counters; rate-limit hit counters; a usage table written at run end; per-model, per-user and per-team breakdowns in the app; budgets, SLO burn rates, and quality signals (thumbs-down, evals). Channel refusal codes on the Usage page are phase 2 (DES-0006).

## Business Rules

- One instrumentation layer in the backend; no new service. Superstep keeps working with every exporter off: all metric code is a no-op without a reader, and the OTel SDK import stays lazy as today.
- Metric labels are bounded: `status`, `source`, `model`, `provider`, `workflow_id`, `code`, `route` (route template, never the raw path), `method`, `status_class`. Never `user_id`, `run_id`, a raw URL, a prompt or a secret. Per-user and per-team usage is SQL aggregation on the Usage page, not a metric label.
- Liveness (`/api/health`) keeps answering 200 while the process serves requests; its body stays backward compatible. Readiness (`/api/ready`) returns 503 when the database probe fails, or when Redis is configured and does not answer. Neither endpoint returns secrets, connection strings or hostnames.
- `/api/ready` needs no sign-in (platform probes call it) and returns only status, timings and counts. Detailed per-component reasons stay generic.
- The Usage page and `GET /api/admin/usage` require `users.manage`; the API enforces it, not only the UI.
- Cost is an estimate from `engine/usage.py` prices (`STUDIO_PRICES`, `STUDIO_PRICES_FILE`). A run with unknown prices has `cost_usd` NULL and `studio.cost` skips it, so every cost figure is shown with the unpriced share and never presented as a complete total.
- A new 429 provider code must keep today's behaviour: a 429 still triggers model fallback (`engine/model_policy.py` `FAILOVER_CODES`) and keeps HTTP 502 to API clients unless the owner decides otherwise.
- English UI strings with the matching vi catalog entries; handbook en and vi stay in sync; no factory IDs in product code, tests, scripts or handbook.

## Acceptance Criteria

- `GET /api/ready` exists, queries the database and Redis, reports queue depth, oldest queued age and worker heartbeat age, and returns 503 on a dead database or a configured but dead Redis; `/api/health` behaviour is unchanged and documented as liveness.
- With `STUDIO_OTEL_METRICS=1` and an OTLP endpoint, the backend exports run, model, HTTP, queue, worker and process metrics with only the allowed labels; with no endpoint nothing is imported or exported.
- Provider HTTP 429 surfaces as its own error code, still fails over to the fallback model, and is counted separately from 5xx.
- `/settings/usage` lists for a chosen window: runs by status, success rate, tokens in/out, estimated cost, unpriced share, top workflows by runs and cost, and the product health counts; it is hidden without `users.manage` and the API returns 403.
- `docker compose --profile observability up` starts the collector, Prometheus and Grafana with a provisioned dashboard and alert rules covering the minimum alert list.
- Handbook observability page in en and vi documents readiness, metrics, labels, the Compose profile, the Usage page and the alert list; strict handbook builds pass.
- Each task: own branch from `develop`, own PR, REV/QA artifacts, full Factory verify/validate, all required CI including E2E green before merge.

## Open Questions

- Should Render/DigitalOcean deploy templates move their health check to `/api/ready`? DEC-0095 recommends documenting it and leaving the templates on `/api/health` in the MVP.
