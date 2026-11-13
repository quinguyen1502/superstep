# Review

## Metadata

- Project: superstep
- Review ID: REV-0311
- Task ID: TASK-0327
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for Agent Dataset insert and upsert against REQ-0099, DEC-0098, DES-0007, and the TASK-0327 acceptance criteria. `allow_delete`, `delete_row`, the public-entry rule, and the export runtimes were checked to stay unchanged.

## Reference Artifacts

- REQ-0099-dataset-writes.md
- DEC-0098-dataset-delete-and-public.md
- DES-0007-datasets.md
- PLAN-0017-dataset-writes.md
- docs/backend-architecture.md

## Findings

### Blocking

- None.

### Non-Blocking

- The branch stacks on TASK-0326 instead of starting from `develop`, as the task handoff suggested. Both tasks edit the Dataset settings components and the locale catalogs, and the stack avoids a conflict. The PR targets the TASK-0326 branch until that merges.
- The offline mock model now fills an enum parameter with its first allowed value and fills a Dataset write tool's `values` with the task text. This lets the Studio Run Playwright case write a row without a provider key. Tools without enums or write values behave as before, and the Agent, workflow-tool, parallel-tool, and export suites still pass.
- Model-facing `values` properties allow string, number, boolean, or null. The tool settings do not carry column types, so the server applies the column type rules and returns `DATASET_VALUE_INVALID` to the model.

## Standards And Architecture Alignment

- A tool may enable `find_rows`, `insert_row`, and `upsert_row` only. `delete_row` is not accepted in the tool settings or in a model call.
- The model sees an `operation` enum of the enabled operations, a `values` object limited to the configured write fields, and filters only when Find rows is enabled. A lookup-only tool keeps its previous schema and still rejects any `operation` argument.
- A write runs through `DatasetRuntimeService.execute` with the workflow write grant, the existing field, type, unique-key, and row-size rules, and a receipt keyed by the Agent tool step and the model's call id.
- Saving a write tool requires edit access to the dataset, existing write fields, and a unique upsert key.
- Trace steps keep `args` empty and record the count and operation. Row values appear only in the model message.

## Design Alignment

- Tool settings use shadcn checkboxes, the shared column picker, and the binding notice with the matching grant. Find-only controls hide when Find rows is off. English and Vietnamese keys match.

## Validation Review

- Backend tests cover allowed fields and operations, rejection of an unconfigured field or operation, receipt replay and conflict, distinct calls writing again, revocation on the next call, a simulated test run, a unique conflict that leaves the other row, and authoring checks.
- Playwright covers the existing read-only tool and a new upsert tool whose row appears in Studio.

## Assumptions

- A logical tool call is the Agent tool step plus the model's call id. A recovered step that replays the same model output gets the same receipt.

## Required Follow-Up

- None for this task. TASK-0328 opens public entries. TASK-0329 and TASK-0330 add Agent writes to the exported runtimes.

## Review Decision

Approved for QA. No blocking findings.
