# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0289
- Task ID: TASK-0304
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Two codes show as two rows with counts; started messages are not refusals: pass (`test_chat_refusals_by_code_and_platform`).
- The query uses the new index: pass (`test_refusal_query_uses_the_status_created_index`, SQLite `EXPLAIN QUERY PLAN`).
- Migration up and down: pass (`test_migrations_upgrade_and_downgrade`); en/vi parity: pass.

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_run_usage.py tests/test_db_migrations.py`; `npx vitest run src/lib/__tests__/locales.test.ts`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
