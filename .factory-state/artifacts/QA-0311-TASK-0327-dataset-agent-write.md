# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0311
- Task ID: TASK-0327
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0327 on `factory/task-0327-dataset-agent-write`. Backend tests used `backend/.venv` on SQLite. PostgreSQL cases skipped without a test database URL. Playwright ran against an isolated local stack with the system Chrome.

## Acceptance Criteria Coverage

- Criterion: An Agent configured for insert and upsert writes only its allowed fields, and the row appears in Studio.
  - Result: pass
  - Evidence: `tests/test_dataset_agent_tool.py::test_agent_dataset_writes_only_configured_operations_and_fields` inserts and then upserts the same ticket. `e2e/dataset-agent-tool.spec.ts` "Agent Dataset tool upserts only its configured fields and the row appears in Studio" saves an upsert tool, runs it from Studio Run, and finds the row in the dataset grid.
- Criterion: The same tool rejects a field or an operation that was not configured. A read-only tool still cannot write.
  - Result: pass
  - Evidence: The backend test rejects an unconfigured field, `delete_row`, an upsert without its key, nested values, empty values, and values on Find rows. The existing read-only test still rejects an `operation` argument. Saving `delete_row` in the tool settings is an `AGENT_TOOL_DATASET` issue.
- Criterion: A retried call returns the original result. A later call in the run can write again. Revocation applies to the next call.
  - Result: pass
  - Evidence: `test_agent_dataset_write_replays_one_call_and_writes_distinct_calls` repeats each execution with the same receipt key, gets the same result, and gets `DATASET_RECEIPT_CONFLICT` for a changed payload. Two calls in one round write two rows. `test_agent_dataset_write_revocation_and_test_runs` lowers the grant to read between rounds and the second write fails.
- Criterion: A test run does not change stored rows. The trace shows the outcome and count without a second copy of the values.
  - Result: pass
  - Evidence: A mocked test run returns `simulated: true` to the model and adds no row. Trace steps have empty `args` and `{count, operation}`, and the run events do not contain the written value.

## UX And Accessibility Coverage

- Criterion: English and Vietnamese settings, keyboard-reachable controls.
  - Result: pass
  - Evidence: Operation, write-field, and key controls are shadcn checkboxes and a Select with labels. Locale parity passed. The trace row reads "upserted 1 row".

## Checks Performed

- `pytest -q tests/test_dataset_agent_tool.py tests/test_agent_node.py tests/test_dataset_runtime.py tests/test_layers.py tests/test_api_envelope.py` — passed, PostgreSQL skipped.
- `pytest -q tests/test_workflow_tool_runs.py tests/test_parallel_agent_tools.py tests/test_export_fallback_files.py tests/test_model_latency.py tests/test_python_export.py tests/test_agent_node.py` — 115 passed, for the mock model change.
- `npx playwright test e2e/dataset-agent-tool.spec.ts e2e/agent-node.spec.ts` — 4 passed.
- `factory verify run --profile full` — passed.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL and the other E2E shards run in CI.

## Residual Risk

- Public entries still deny Agent writes until TASK-0328. Exported projects do not run Agent writes until TASK-0329 and TASK-0330.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0327.

## QA Decision

Passed to done.
