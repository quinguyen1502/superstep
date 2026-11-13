# Task

## Metadata

- Project: superstep
- Task ID: TASK-0340
- Title: Explain Dataset Studio states and name what is deleted
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
- Priority: P1
- Size: M

## Objective

Every Datasets state a user can reach shows why and what to do, deletions name the row, and CSV issues are readable.

## Scope

### In Scope

- Viewer and non-manager: management controls stay visible but disabled with an inline reason (show-and-explain), per `docs/ui-conventions.md`.
- Empty catalog: one empty state with Create and Import CSV (for users who may create) or a reason (for viewers); no "Select a dataset" while the catalog is empty.
- Not found or no access: a neutral state with a link back to the catalog; no Retry for 404; Retry stays for retryable errors.
- Row delete confirmation names the row by its first unique field, else its row id (DES-0007).
- CSV issue list: column labels instead of keys, sorted by line, the rejected value (truncated), the alert icon, a count per issue type; preview step for import into an existing dataset.
- en/vi strings, both themes, keyboard reachability.

### Out Of Scope

- Grid layout changes (TASK-0341).

## Inputs

- `frontend/src/pages/Datasets.tsx`, `components/datasets/dataset-grid.tsx`, the CSV dialog; review screenshots 42 shots.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- None for the states; the disabled-reason copy for team managers lands with or after TASK-0335.

## Acceptance Criteria

- Screenshots of viewer, empty, not found, row delete, and CSV issues in en/vi light/dark show the explanation and action.
- Delete confirmation shows the row's key value.
- CSV issues are ordered by line and show label, value, and message.

## Tests

- Playwright specs for each state; frontend unit tests for the issue list sort and formatting; locale parity.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0340-dataset-studio-states` from `develop` when implementation begins.
