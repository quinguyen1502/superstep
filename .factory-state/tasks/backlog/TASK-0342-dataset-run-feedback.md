# Task

## Metadata

- Project: superstep
- Task ID: TASK-0342
- Title: Summarize Dataset node runs and offer a Grant shortcut
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix UI
- Priority: P2
- Size: S

## Objective

Run traces for Dataset nodes read as a sentence, Studio Run warns before writing real rows, and managers can grant from the missing-grant hint.

## Scope

### In Scope

- Trace summary for Dataset nodes: operation, dataset, outcome, row count, formatted time; raw JSON behind a disclosure.
- Studio Run notice when the workflow contains Dataset writes or deletes (test runs stay simulated).
- Missing-grant validation hint shows a Grant button for users who manage the dataset; it opens the Access view preselected.

### Out Of Scope

- Changes to trace storage or the row-data boundary.

## Inputs

- Run trace renderer, Dataset node validation, Access view.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- TASK-0341 merged (Access as a view).

## Acceptance Criteria

- A Dataset node trace shows a readable summary without cell values.
- Studio Run of a writing workflow shows the notice once per session.
- A manager fixes a missing grant from the node in two clicks.

## Tests

- Frontend unit tests for the summary; Playwright for the notice and the Grant shortcut.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0342-dataset-run-feedback` from `develop` when implementation begins.
