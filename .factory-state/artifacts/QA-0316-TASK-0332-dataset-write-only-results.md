# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0316
- Task ID: TASK-0332
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0332 on `factory/task-0332-dataset-write-only-results`. Backend tests used `backend/.venv` on SQLite. PostgreSQL could not run on this machine (no server package available), so the PostgreSQL parameter of every case runs in CI only. Playwright ran against an isolated local stack with the system Chrome.

## Acceptance Criteria Coverage

- Criterion: A `write` grant and a `write` token never receive a cell value from insert, upsert, dry-run, or a replayed receipt; the response has `row.id`, `row.revision`, and `inserted` only.
  - Result: pass
  - Evidence: `test_write_only_grant_node_gets_identifiers_and_cannot_request_fields`, `test_write_only_token_reproduces_review_probe`, and `test_write_only_dry_run_and_receipt_replay` upsert with only the key against a row holding a secret and get `{"row": {"id", "revision"}, "inserted": false}`; the secret is absent from the response and the run events. Replay returns the same identifier-only result.
- Criterion: A write-only caller that asks for fields gets `DATASET_GRANT_DENIED` and nothing is written.
  - Result: pass
  - Evidence: The node and the token probe with `["ticket", "email", "note"]` get `DATASET_GRANT_DENIED` (403 on the token API); no row is added and the revision stays 1. A receipt made while the grant could read is refused after a downgrade. `test_value_reveal_is_rechecked_under_the_writer_lock` shows the locked re-check writes nothing.
- Criterion: An Agent tool with Insert and Upsert but without Find returns identifiers only to the model, and the trace shows the outcome and count.
  - Result: pass
  - Evidence: `test_agent_tool_without_find_gets_identifiers_only` with a `read_write` grant: the model message is `{"row_id", "inserted"}` and the step shows `{"count": 1, "operation": "upsert_row"}`. With Find on a write grant the model also gets identifiers only.
- Criterion: Upserting identical values twice leaves `revision` and `updated` unchanged and records one audit event.
  - Result: pass
  - Evidence: `test_noop_upsert_keeps_revision_updated_and_audit` and `test_concurrent_noop_and_real_update_are_serialized`.
- Criterion: `read_write` callers and Studio users keep today's full response.
  - Result: pass
  - Evidence: The same tests assert full values for `read_write`; existing Studio, connected, and Agent suites pass unchanged.

## UX And Accessibility Coverage

- Criterion: Access dialog note and the node output picker for a write-only grant, in English and Vietnamese.
  - Result: pass
  - Evidence: `e2e/dataset-write-only.spec.ts` checks the hidden picker, the explanation, the Return identifiers only action and the saved `fields: []`, and the Write note in the Access dialog. Locale parity passed.

## Checks Performed

- `pytest -q tests/test_dataset_*.py tests/test_datasets.py tests/test_agent_node.py tests/test_layers.py tests/test_api_envelope.py tests/test_python_export.py tests/test_typescript_export.py` — passed on SQLite, PostgreSQL skipped.
- `npx playwright test e2e/dataset-write-only.spec.ts e2e/dataset-node-editor.spec.ts e2e/dataset-access.spec.ts e2e/dataset-agent-tool.spec.ts` — 6 passed.
- `npm run lint` — passed.
- `factory verify run --profile full`, `factory validate`, and `factory validate --only hygiene` — see the PR body for the final run.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL and the full E2E shards run in CI. Public-entry writes are covered when TASK-0328 takes this change.

## Residual Risk

- Accepted in DEC-0099: Upsert still reports `inserted: false` for an existing key, so a write-only caller can learn that a key exists. The handbook and `docs/dataset-export.md` say so.
- Stored receipts still contain row values until TASK-0333; they are not returned to write-only callers.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0332.

## QA Decision

Passed. Task moved to review.
