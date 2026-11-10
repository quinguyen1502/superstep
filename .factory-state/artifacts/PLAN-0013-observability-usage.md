# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0013
- Status: Accepted 2026-11-09 (Asia/Saigon) by the owner (pt275u, accepting the plan); REQ-0094, DEC-0094 and DEC-0095 accepted; in progress
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-09
- Related Requirements: REQ-0094
- Related Design: DES-0006
- Related Architecture: DEC-0094, DEC-0095

## Objective

Give operators a Grafana view of server, process, HTTP, database, Redis, queue and worker health, and give Studio admins an in-app Usage page for model tokens, cost, LLM errors and product SLOs, from one OTel instrumentation layer in the backend.

## Context Reviewed

- `backend/app/services/telemetry.py`: per-run traces, `summarize`, five run metrics behind `STUDIO_OTEL_METRICS`, labels `status`/`source`; lazy SDK import.
- `backend/app/api/routes/meta.py`: `/api/health` with hard-coded `ok: true`, no DB query.
- `backend/app/services/job_queue.py`: Redis keys `studio:run-jobs`, `:delayed`, `:processing:<worker>`, leases; no worker heartbeat key.
- `backend/app/engine/providers.py`: 401/403 to `PROVIDER_AUTH_FAILED`, network errors to `PROVIDER_UNREACHABLE`, every other status including 429 to `PROVIDER_BAD_RESPONSE`; `engine/model_policy.py` `FAILOVER_CODES`.
- `backend/app/engine/usage.py`: built-in prices plus `STUDIO_PRICES_FILE` and `STUDIO_PRICES`; unknown model gives `cost_usd` None.
- `backend/app/models/run.py` (`status`, `started`, `ended`, tokens, `cost_usd`, `error_count`, `owner`, `source`, `workflow_id`; indexes only on `owner` and `parent_run_id`), `approval.py` (human waits with `status`, `outcome`, `due_at`), `webhook_delivery.py` (`status` pending/retrying/ok/failed), `workflow_schedule.py` (`enabled`, `next_run`, `note`), `chat_message.py` (`status`, `code`, no index on `created`).
- `frontend/src/pages/settings/sections.ts` and `SettingsPage.tsx`; Activity section with `users.manage`.
- `docker-compose.yml` Jaeger under profile `tracing`; health checks in `Dockerfile`, `backend/Dockerfile`, Render, DigitalOcean templates.
- `handbook/docs/{en,vi}/operate/observability.md`.

## Decisions Made In This Plan

- **Metrics backend: OTel push to a collector, Prometheus scrapes the collector, Grafana reads Prometheus** (DEC-0094). The repo already ships the OTel SDK, the OTLP metric exporter and `STUDIO_OTEL_METRICS`; there is no `prometheus_client`. Push works the same for API, worker and replicas; `/metrics` is not added in the MVP.
- **Liveness versus readiness** (DEC-0095): `/api/health` stays liveness and unchanged; `/api/ready` fails on a dead database or configured Redis. Deploy templates stay on `/api/health`; the handbook explains the switch.
- **Product SLOs in the MVP: approvals, webhooks and schedules only, as a separate task (TASK-0290).** They are single grouped counts on indexed or small tables (human waits by `status`/`due_at`, `webhook_delivery` by `status`, `workflow_schedule` by `enabled`/`next_run`) and they feed three alerts on the minimum list (overdue schedules, webhook failures, waiting approvals). Run success rate is already in the core Usage task. Channel refusal codes move to phase 2: `chat_message` has no index on `created`/`status`, and the refusal semantics differ per channel, which would bloat the first slice.
- **Per-model breakdown in the MVP lives in Grafana** (metric labels from TASK-0287). The Usage page shows totals, top workflows and the unpriced share from `runs` columns; a usage table and in-app per-model, per-user and per-team views are phase 2.
- **Distinct 429 code** `PROVIDER_RATE_LIMITED`: added to `FAILOVER_CODES` and kept at HTTP 502 for API clients, so fallback and client behaviour do not change; only reporting gets sharper.
- **`tzdata` caveat:** without the Python `tzdata` package, a minimal image may not know `Asia/Saigon`, so the schedule dialog rejects the zone a Vietnamese browser reports. The overdue and disabled schedule panel (TASK-0290) shows the fallout; the fix is shipping `tzdata` (TASK-0293, small and independent).

## Work Breakdown

| Order | Task | Purpose | Size | Depends |
| --- | --- | --- | --- | --- |
| 1 | [TASK-0284](../tasks/backlog/TASK-0284-readiness-endpoint.md) | `/api/ready`, worker heartbeat, shared DB/Redis/queue probes; `/api/health` stays liveness | M | acceptance |
| 2 | [TASK-0285](../tasks/backlog/TASK-0285-otel-metrics-surface.md) | OTel metrics surface: label rules, queue/worker/process/probe gauges, in-memory bus flag | M | TASK-0284 |
| 3 | [TASK-0286](../tasks/backlog/TASK-0286-http-metrics.md) | HTTP request count, latency histogram and 5xx by route template | S | TASK-0285 |
| 4 | [TASK-0287](../tasks/backlog/TASK-0287-model-metrics.md) | Model labels, LLM error codes, distinct 429, fallbacks, unpriced usage | M | TASK-0285 |
| 5 | [TASK-0288](../tasks/backlog/TASK-0288-admin-usage-api.md) | `GET /api/admin/usage` from `runs` columns, `runs.started` index | M | acceptance (parallel to 2-4) |
| 6 | [TASK-0289](../tasks/backlog/TASK-0289-usage-settings-section.md) | Settings Usage section at `/settings/usage` | M | TASK-0288 |
| 7 | [TASK-0290](../tasks/backlog/TASK-0290-product-health-panels.md) | Approvals, webhooks, schedules counts on the Usage page and as gauges | S | TASK-0289, TASK-0285 |
| 8 | [TASK-0291](../tasks/backlog/TASK-0291-grafana-compose-profile.md) | Compose `observability` profile: collector, Prometheus, Grafana, dashboard, alert rules | M | TASK-0286, TASK-0287, TASK-0290 |
| 9 | [TASK-0292](../tasks/backlog/TASK-0292-observability-handbook.md) | Handbook observability page en/vi and the minimum alert list | S | TASK-0291 |
| any | [TASK-0293](../tasks/backlog/TASK-0293-ship-tzdata.md) | Ship Python `tzdata` so schedule time zones resolve everywhere | XS | none |

Each task: own branch `factory/task-NNNN-<slug>` from `develop`, own PR, REV and QA artifacts, full Factory verify and validate, all required CI including E2E green before merge. Tasks that add environment variables update `.env.example` and the reference page in the same PR; TASK-0292 writes the full observability page.

## Sequence

1. Owner accepts REQ-0094, DEC-0094 and DEC-0095 (or picks other options); tasks move from backlog to todo.
2. TASK-0284, then TASK-0285; TASK-0288 may start in parallel since it only reads the database.
3. TASK-0286 and TASK-0287 after TASK-0285 (independent of each other).
4. TASK-0289 after TASK-0288; TASK-0290 after TASK-0289 and TASK-0285.
5. TASK-0291 once the metric names from TASK-0286, TASK-0287 and TASK-0290 are merged; TASK-0292 last.
6. TASK-0293 at any point.

## Minimum Alert List (TASK-0291 rules, TASK-0292 docs)

| Alert | Signal |
| --- | --- |
| Instance down | Collector/Prometheus `up` for the Studio job, or no `studio_*` samples for 5 min |
| Database down | `studio.ready.db` failure gauge, or readiness 503 |
| Redis down | `studio.ready.redis` failure gauge when Redis is configured |
| HTTP 5xx | 5xx share of `studio.http.server.requests` above threshold for 5 min |
| Queue backlog | `studio.queue.depth` above threshold, or `studio.queue.oldest_age` above threshold |
| Worker missing | `studio.worker.heartbeat_age` above 3 reap intervals |
| Run error-rate spike | `studio.runs` with status error or timeout over total, above threshold |
| Provider auth or unreachable | `studio.llm.errors` with code `PROVIDER_AUTH_FAILED` or `PROVIDER_UNREACHABLE` above zero for 5 min; `PROVIDER_RATE_LIMITED` as a warning |
| Daily cost | 24 h increase of `studio.cost` above a threshold provisioned as a Grafana variable; the panel shows the unpriced share next to it |
| Overdue schedules | `studio.schedules.overdue` above zero |
| Webhook failures | `studio.webhooks.failed` increase above zero |
| In-memory bus in production | `studio.run_bus.in_memory` equals 1 with production settings |

## Later Phases (not in this plan's MVP)

Filed on 2026-11-10 as REQ-0095 and PLAN-0014 (TASK-0294 to TASK-0308), proposed and awaiting owner acceptance.

- Phase 2, correlation: JSON logs carrying `run_id`, `request_id`, `trace_id`; HTTP, SQL and Redis spans on the same traces (OTel FastAPI/SQLAlchemy/Redis instrumentation, opt-in).
- Phase 2, depth: Postgres and Redis exporters in the Compose profile; SQLAlchemy pool metrics; per-call LLM latency and time to first token; embedding and retrieval usage; channel, MCP, browser and sandbox counters; rate-limit hit counters; channel refusal codes on the Usage page.
- Phase 3, usage data: a usage table written at run end (per node: model, provider, tokens, cost, priced flag); per-model, per-user and per-team views on the Usage page; retention for `runs.events`.
- Phase 4, governance: per-user and per-team budgets; SLO burn-rate alerts; quality signals (thumbs-down, eval results).

## Risks

- Label cardinality: `workflow_id` grows with workflows; acceptable for typical installs, documented, and the collector can drop it if needed.
- Export failures with metrics on and no collector: keep the opt-in flag and the exporter's own timeouts; never block runs on export.
- Readiness probes under load: short timeouts, no table scans; oldest queued age uses an indexed query (TASK-0288 adds the `runs.started` index; TASK-0284 must not depend on it being present, or ships the index itself if it lands first).
- Cost under-reporting: always shown with the unpriced share; the handbook links to `STUDIO_PRICES`.
- Behaviour change risk from the new 429 code: covered by keeping it in `FAILOVER_CODES` and at HTTP 502, with tests.
