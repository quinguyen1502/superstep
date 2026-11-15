# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0274
- Task ID: TASK-0288
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- Seeded runs produce exact totals, buckets and top workflows on SQLite and Postgres: pass on SQLite (`test_summary_is_exact[sqlite]`); the Postgres parameter runs in CI with `TEST_DATABASE_URL` (no local server).
- `cost_usd` NULL runs count as unpriced and are excluded from the cost sum: pass (`test_summary_is_exact`).
- Non-admin gets 403; the migration upgrades and downgrades cleanly: pass (`test_api_needs_users_manage`, `test_migration_upgrades_and_downgrades`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_usage_api.py tests/test_layers.py tests/test_api_envelope.py tests/test_db_migrations.py`.
- Full backend suite (see the PR), `factory validate --only hygiene`.

## QA Decision

Pass.
