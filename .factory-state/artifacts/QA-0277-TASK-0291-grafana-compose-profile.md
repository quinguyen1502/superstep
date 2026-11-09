# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0277
- Task ID: TASK-0291
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- `docker compose --profile observability up` shows data on every starter panel after a few runs with the mock model: partly verified without Docker. With the same config files on local binaries, server, database, queue, worker, run and token panels showed data after mock-model runs; Redis, cost and error panels have no data on a SQLite, mock-model, error-free stack, as expected.
- Alert rules load without errors and fire in a manual drill for database down and queue backlog: rules load with health ok; the drill ran for a stopped backend (Worker missing firing, Instance down pending). Database-down and queue-backlog drills need Postgres or Redis and were not run.
- Default Grafana admin password is local-only and documented: pass (127.0.0.1 port binding, `GRAFANA_ADMIN_PASSWORD`, handbook says to change it).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_observability_stack.py`; `otelcol-contrib validate`; `promtool check config`; Grafana 11.3.1 provisioning API.
- `factory validate --only hygiene`.

## QA Decision

Pass.
