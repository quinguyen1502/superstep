# Task

## Metadata

- Project: superstep
- Task ID: TASK-0291
- Title: Grafana Compose profile, starter dashboard and alert rules
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-14
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
- 2026-11-10: Compose profile `observability`: `otel-collector` (contrib 0.114.0; OTLP in, Prometheus exporter on :8889 with `add_metric_suffixes: false`, traces forwarded to Jaeger), `prometheus` (v2.55.1, scrapes only the collector, `honor_labels`), `grafana` (11.3.1, 127.0.0.1 only, provisioned Prometheus and Jaeger datasources, the Superstep overview dashboard and alert rules); Jaeger joins the profile. Config under `deploy/observability/`. The backend has no `/metrics` endpoint and no Prometheus client.
- 2026-11-10: Backend and worker env: Compose cannot set variables per profile, so `deploy/observability/observability.env` (passed as a second `--env-file`) sets `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`, `STUDIO_OTEL_METRICS=1`, `OTEL_METRIC_EXPORT_INTERVAL=15000`, the Jaeger trace URL and `STUDIO_GRAFANA_URL`; the api and worker environment pass these through. `GRAFANA_ADMIN_PASSWORD` (local-only default `admin`), `GRAFANA_PORT`, `PROMETHEUS_RETENTION` in `.env.example`.
- 2026-11-10: Starter dashboard (36 panels): Server, Database and Redis, Queue and workers, Runs and models, Product. Alert rules: the 12 alerts of the minimum list (provider rate limit as a separate warning rule) plus "Approvals waiting too long".
- 2026-11-10: Deviation: thresholds are YAML anchors under `x-thresholds` at the top of the rules file, not Grafana environment variables, because Grafana does not interpolate environment variables inside query models.
- 2026-11-10: Check: `backend/tests/test_observability_stack.py` parses the dashboard and rules, checks every series and label against the instruments created in `services/telemetry.py` and its label allowlist, and checks the Compose wiring (pinned images, mounted files exist, collector and Prometheus ports agree, Grafana bound to 127.0.0.1).
- 2026-11-10: Local smoke test without Docker (the box has none): the pinned otelcol-contrib, Prometheus and Grafana binaries ran with these files (`otelcol validate`, `promtool check config` passed). The backend with `STUDIO_OTEL_METRICS=1` pushed to the collector; every dashboard and alert query parsed in Prometheus; Grafana loaded the dashboard and all 15 rules with health ok. Drill: stopping the backend took "Worker missing" to firing and "Instance down" to pending. Database-down and queue-backlog drills were not run (no Postgres or Redis on the box); `docker compose config` was not run (no Docker).
- 2026-11-10: Review REV-0277 and QA-0277. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0277-TASK-0291-grafana-compose-profile.md`
- QA: `.factory-state/artifacts/QA-0277-TASK-0291-grafana-compose-profile.md`

## Integration

- Merged into develop via PR #352 at `790e0ce5`. The lifecycle was reconciled on 2026-11-14.
