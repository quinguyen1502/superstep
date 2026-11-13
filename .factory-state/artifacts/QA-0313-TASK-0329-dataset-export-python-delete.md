# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0313
- Task ID: TASK-0329
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0329 on `factory/task-0329-dataset-export-python-delete`. Generated projects ran with `backend/.venv` against SQLite. PostgreSQL cases are parameterized and skipped locally without a test database URL. CI runs them.

## Acceptance Criteria Coverage

- Criterion: Generated Python projects pass lookup, Agent insert and upsert, delete, receipt replay, and changed-payload conflict on SQLite and PostgreSQL.
  - Result: pass (SQLite locally, PostgreSQL in CI)
  - Evidence: `test_python_standalone_delete_row_locks_replays_and_skips_missing_rows` runs a generated graph twice that deletes through standalone storage and reads a second binding through the Superstep API, then tests replay, conflict, missed deletes, invalid keys, and a two-thread delete race. `test_generated_python_agent_writes_and_connected_delete` runs an Agent upsert graph twice and calls `dataset_agent` for insert, Find rows, replay, conflict, and rejected arguments.
- Criterion: A mixed graph reads through the Superstep API and deletes through standalone storage.
  - Result: pass
  - Evidence: The delete test's graph deletes from the SQLite binding and finds rows on the API binding in the same run. The test server sees one `find_rows` request per run.
- Criterion: A connected token without delete capability cannot delete. A token with it can.
  - Result: pass
  - Evidence: The same Agent test runs the graph with a read-write token and gets `AUTH_TOKEN_INVALID`, then with `allow_delete` and the row is deleted. The test server sees two `delete_row` requests.
- Criterion: Setup run twice keeps the rows that remain. Schema mismatch fails without changing stored rows.
  - Result: pass
  - Evidence: The delete test repeats setup after the runs and continues with the remaining data. The existing standalone test still covers the schema mismatch.

## UX And Accessibility Coverage

- Not applicable. No UI change.

## Checks Performed

- `pytest -q tests/test_dataset_python_standalone.py` — 4 passed, PostgreSQL skipped.
- `pytest -q tests/test_python_export.py tests/test_dataset_project_export.py tests/test_dataset_export_snapshot.py tests/test_project_export.py tests/test_export_remaining.py tests/test_handoff_exports.py tests/test_dataset_agent_tool.py tests/test_export_fallback_files.py` — 94 passed.
- `factory verify run --profile full` — passed on the TASK-0331 stack tip, which contains this commit.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

- After merging `develop` with TASK-0332: exported `dataset_agent` asks for no fields and returns `{row_id, inserted}` when the tool cannot Find rows, as Studio does. `pytest -q tests/test_dataset_python_standalone.py tests/test_python_export.py tests/test_dataset_project_export.py tests/test_dataset_write_only.py` — 58 passed.

## Gaps Or Untested Areas

- PostgreSQL runs in CI.

## Residual Risk

- Low. The delete path reuses the lock and receipt table that insert and upsert already use.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0329.

## QA Decision

Passed to done.
