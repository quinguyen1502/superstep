# Review

## Metadata

- Project: superstep
- Review ID: REV-0286
- Task ID: TASK-0301
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`backend/app/models/run_usage.py`, migration `0060_run_usage`, `backend/app/repositories/run_usage.py`, `backend/app/services/run_usage.py`, `run_service` (write at run end), run and user data deletion, `admin_cmd usage-backfill`, `backend/tests/test_run_usage.py`.

## Findings

### Blocking

- None.

### Non-Blocking

- Rows are replaced per run (delete and insert in one transaction) and protected by the unique key, so a re-finish or recovery never duplicates.
- Child runs write their own rows; the models block therefore includes subworkflow calls, while the cards keep counting top-level runs (the handbook says the table can be higher).
- Error rows come from failed model attempts in the run events.
- Migrations were tested on SQLite only; no Postgres was available in the implementation environment. CI runs the Postgres migration job.

## Review Decision

Approved for QA.
