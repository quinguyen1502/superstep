# Task

## Metadata

- Project: superstep
- Task ID: TASK-0291
- Title: Grafana Compose profile, starter dashboard and alert rules
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: M

## Objective

Ship an operator stack next to Jaeger: OpenTelemetry Collector, Prometheus and Grafana with a provisioned dashboard and the minimum alert rules.

## Scope

### In Scope

- `docker-compose.yml` profile `observability` (Jaeger also joins it): `otel-collector` (OTLP in, Prometheus exporter out, traces forwarded to Jaeger), `prometheus` scraping the collector, `grafana` with provisioned datasources (Prometheus, Jaeger) and dashboards; pinned image versions; config under `deploy/observability/`.
- Backend and worker env in the profile: `STUDIO_OTEL_METRICS=1`, OTLP endpoint pointing at the collector.
- Starter dashboard JSON: Server (HTTP rate, latency p50/p95/p99, 5xx share, WebSockets, CPU, RSS), Database and Redis (probe status and latency), Queue and workers (depth, oldest age, busy versus capacity, heartbeat, reaped/recovered), Runs and models (runs by status, error rate, tokens and cost by model and workflow, unpriced usage, LLM errors by code, fallbacks), Product (approvals, webhooks, schedules).
- Grafana alert rules for the PLAN-0013 minimum alert list, with thresholds as provisioned variables.
- A CI or script check that the dashboard JSON parses and only references metrics the backend emits.

### Out Of Scope

- Postgres and Redis exporters (phase 2); hosted Grafana or vendor setups; Kubernetes manifests.

## Dependencies

- TASK-0286, TASK-0287 and TASK-0290 merged (metric names final).

## Acceptance Criteria

- `docker compose --profile observability up` shows data on every starter panel after a few runs with the mock model.
- Alert rules load without errors and fire in a manual drill for database down and queue backlog.
- Default Grafana admin password is not hard-coded beyond the local-only default, and the handbook says to change it.

## Validation Plan

- `docker compose --profile observability config` and a local run with screenshots for REV.
- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
