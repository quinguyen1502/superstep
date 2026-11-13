# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0314
- Task ID: TASK-0330
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0330 on `factory/task-0330-dataset-export-typescript-delete`. Generated modules ran with Deno 2 against SQLite. PostgreSQL cases are parameterized and skipped locally without a test database URL. CI runs them.

## Acceptance Criteria Coverage

- Criterion: Generated TypeScript projects pass lookup, Agent insert and upsert, delete, receipt replay, and changed-payload conflict on SQLite and PostgreSQL.
  - Result: pass (SQLite locally, PostgreSQL in CI)
  - Evidence: `test_typescript_standalone_delete_row_locks_replays_and_skips_missing_rows` and `test_generated_typescript_agent_writes_and_connected_delete`.
- Criterion: A mixed graph reads through the Superstep API and deletes through standalone storage.
  - Result: pass
  - Evidence: The delete test's graph deletes from the SQLite binding and finds rows on the API binding in the same run.
- Criterion: A connected token without delete capability cannot delete.
  - Result: pass
  - Evidence: The Agent test gets `AUTH_TOKEN_INVALID` with a read-write token, then deletes with `allow_delete`.
- Criterion: Setup run twice keeps the rows that remain. Schema mismatch fails without changing stored rows.
  - Result: pass
  - Evidence: The delete test repeats setup and keeps the remaining data. The existing standalone test still covers the schema mismatch.

## UX And Accessibility Coverage

- Not applicable. No UI change.

## Checks Performed

- `pytest -q tests/test_typescript_export.py tests/test_dataset_project_export.py tests/test_dataset_typescript_standalone.py tests/test_project_export.py` — passed, PostgreSQL skipped.
- `deno check` on the generated Agent-write module — passed.
- `factory verify run --profile full` — passed on the TASK-0331 stack tip, which contains this commit.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL runs in CI. The Node.js `node:sqlite` project variant runs only when `STUDIO_DATASET_EXPORT_JS_MODULES` is set, and it was not run for this task. It uses the same generated runtime code as the Deno module.

## Residual Risk

- Low. The delete path reuses the transaction and receipt code that insert and upsert use.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0330.

## QA Decision

Passed to done.
