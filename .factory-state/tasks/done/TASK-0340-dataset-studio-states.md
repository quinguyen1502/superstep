# Task

## Metadata

- Project: superstep
- Task ID: TASK-0340
- Title: Explain Dataset Studio states and name what is deleted
- Status: done
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
- Review: [REV-0329](../../artifacts/REV-0329-TASK-0340-dataset-studio-states.md)
- QA: [QA-0329](../../artifacts/QA-0329-TASK-0340-dataset-studio-states.md)

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
- 2026-11-13: Owner accepted REQ-0100 and PLAN-0018. Started on `factory/task-0340-dataset-studio-states` after TASK-0338 and merged `develop` once it landed. Users without `resources.manage` see every create, edit, import, and delete control disabled with an inline reason. The empty catalog offers Create, Import CSV, and the handbook. A missing dataset shows a neutral not-found state with a link back and no Retry. Row deletion names the first unique value or the row ID. CSV issues are sorted by line with column labels, the rejected value, and per-kind counts, and the preview header shows each mapped field. TASK-0335 is not merged, so the team-manager reason is a follow-up. Review REV-0329. QA QA-0329. Moved to done.

## Handoff Notes

- Branch `factory/task-0340-dataset-studio-states`. Ready PR into `develop`; merge when every required check is green.
- Follow-up for TASK-0335: once team managers can manage their team's datasets, `editable` in `frontend/src/pages/Datasets.tsx` must use the per-dataset permission, and the disabled reason needs a team-manager variant (for example, "Only managers of this team can change it").
