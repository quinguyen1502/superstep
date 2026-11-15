# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0095
- Status: Accepted 2026-11-10 (Asia/Saigon) by the owner (pt280u, "go ahead with phase 2"), together with PLAN-0014. Phase 2 (TASK-0294 to TASK-0305) merged through PRs #354 to #360. The owner approved starting Phase 3 (TASK-0306 to TASK-0308) on 2026-11-11.
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-10
- Source: Owner chat 2026-11-10 (pt279u, asking to file tasks for the remaining work after the observability MVP)
- Related: REQ-0094, DES-0006, DEC-0094, DEC-0095, PLAN-0013, PLAN-0014, TASK-0294 to TASK-0308

## Why A New Requirement

REQ-0094 (accepted 2026-11-09, implemented by TASK-0284 to TASK-0293 and merged through PRs #349 to #353) lists this work explicitly as out of scope and as later phases of PLAN-0013. This requirement takes over those later phases without changing any accepted REQ-0094 rule, DEC-0094 or DEC-0095.

## Summary And Scope

Phase 2, correlation and depth:

1. Structured JSON logs carrying `request_id`, `run_id` and `trace_id`.
2. HTTP, SQL and Redis spans on top of the existing run and node traces (opt-in).
3. Database and Redis server metrics beyond the MVP probe gauges, plus SQLAlchemy pool usage.
4. Per-call LLM latency and time to first token.
5. Embedding usage (tokens and cost) next to chat model usage.
6. Channel, MCP, browser and sandbox activity counters.
7. Rate-limit hit counters for Superstep's own limits, next to the provider 429 count that already exists.
8. A usage table written at run end (none exists today; the MVP aggregates `runs` columns).
9. Per-model, per-user and per-team breakdowns on Settings, Usage.
10. Channel refusal codes on the Usage page, with the `chat_messages` index they need.

Phase 3, governance:

11. Per-user and per-team monthly budgets with warnings at 80 and 100 percent (DEC-0096).
12. SLO targets with burn-rate alerts and an error-budget view.
13. Quality signals: thumbs-down rate and workflow test results.

## Business Rules

- Every REQ-0094 business rule still applies: one instrumentation layer, no new service, everything a no-op with exporters off, lazy OTel imports.
- DEC-0094 stays: metrics leave by OTLP to the collector, Prometheus scrapes the collector, Grafana reads Prometheus and Jaeger, no app `/metrics` endpoint. Database and Redis server metrics prefer collector receivers so Prometheus keeps one app-side target.
- DEC-0095 stays: `/api/health` is liveness and unchanged; `/api/ready` checks the database and Redis; deploy templates stay on `/api/health`. No task in this requirement switches deploy health checks.
- Split of surfaces: Grafana is for operators (server, infrastructure, model latency and cost alerts); Settings, Usage at `/settings/usage` (`users.manage`) is for studio admins (product usage, per-model, per-user and per-team figures, SLOs, budgets, quality).
- Metric labels stay bounded (`model`, `provider`, `workflow_id`, fixed enums). Never `user_id`, `run_id`, team ids, raw URLs, server or connection names, limiter keys, prompts or secrets. Per-user and per-team figures are SQL aggregations only.
- Logs and spans never contain prompts, inputs, outputs, SQL parameter values, Redis values or secrets.
- Cost is always shown with the unpriced share; unpriced usage is never counted as zero.
- Schema changes through SQLAlchemy models and Alembic migrations; layers per DEC-0009; en and vi strings and handbook pages updated together; no factory ids in product code, tests, scripts or the handbook.

## Acceptance Criteria

- Each task in PLAN-0014 meets its own acceptance criteria on its own branch and PR with REV and QA artifacts, full Factory verify and validate, and all required CI including E2E green before merge.
- After phase 2, an operator can follow one run from a log line to its trace with SQL and Redis spans, and see database, Redis, model latency, embedding, integration and rate-limit panels in the starter dashboard; a studio admin sees per-model, per-user, per-team and channel refusal data on the Usage page.
- After phase 3, admins can set budgets, see SLO error budgets and quality signals on the Usage page, and Grafana has burn-rate alerts.

## Open Questions

- Default SLO targets (TASK-0307; recommended 99 percent run success and 99.5 percent API availability over 30 days).
- Collector receivers versus standalone Postgres and Redis exporters (TASK-0296; recommended receivers).
