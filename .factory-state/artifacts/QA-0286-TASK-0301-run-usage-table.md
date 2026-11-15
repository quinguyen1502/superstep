# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0286
- Task ID: TASK-0301
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Two LLM nodes on different models and one RAG node write three rows that sum to the run totals; unpriced rows keep cost NULL: pass (`test_rows_add_up_to_the_run_totals`, `test_priced_rows_sum_to_the_run_cost`).
- Re-finishing does not duplicate: pass (`test_written_once_at_run_end_and_replaced_on_refinish`, `test_unique_key_rejects_duplicates`).
- Migration up and down on SQLite: pass (`test_migrations_upgrade_and_downgrade`, `test_db_migrations`); Postgres left to CI. `tests/test_layers.py` passes; repositories use SQLAlchemy only. Backfill from run events: pass (`test_backfill_from_run_events`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_run_usage.py tests/test_db_migrations.py tests/test_layers.py`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
