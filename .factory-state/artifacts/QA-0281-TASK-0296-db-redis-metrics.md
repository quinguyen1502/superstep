# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0281
- Task ID: TASK-0296
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Non-empty Postgres and Redis panels against the Compose services: not verified locally (no Docker); config validated with `otelcol-contrib validate` and the dashboard checked against the receivers' metric names (`test_dashboard_uses_emitted_metrics_only`). Without Redis the Redis receiver reports nothing and the panels show no data.
- Pool gauges with `STUDIO_OTEL_METRICS=1`, no-ops without a reader: pass (`test_pool_gauges_from_the_pool_counters`).
- Monitoring credentials from environment variables, none committed: pass (`test_collector_reads_postgres_and_redis_without_committed_credentials`).
- Alert rules parse, use known metrics and resolve thresholds to numbers: pass (`test_alert_rules_cover_the_minimum_list`); all rule and panel expressions parse with `promtool check rules`.

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_metrics.py tests/test_observability_stack.py`.
- `otelcol-contrib validate --config deploy/observability/otel-collector.yaml` with dummy environment values; `promtool check rules` over every dashboard and alert expression (92 expressions, phase 2 total).
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
