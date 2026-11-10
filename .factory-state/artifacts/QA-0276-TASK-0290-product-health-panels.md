# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0276
- Task ID: TASK-0290
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- Seeded approvals, deliveries and schedules give exact counts in API tests; gauges report the same values: pass (`test_health_counts_are_exact`).
- A schedule disabled because of an unknown time zone appears with its note: pass (same test).
- Queries use existing indexes or add one in a migration; no full scan of `runs.events`: pass (migration `0059_usage_indexes`; no `events` column read).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_usage_api.py tests/test_metrics.py`; `npx playwright test e2e/usage.spec.ts`.
- Full backend suite (see the PR), `factory validate --only hygiene`.

## QA Decision

Pass.
