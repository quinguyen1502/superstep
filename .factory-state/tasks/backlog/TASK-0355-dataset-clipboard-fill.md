# Task

## Metadata

- Project: superstep
- Task ID: TASK-0355
- Title: Add range selection, clipboard, and fill handle to the Dataset grid
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0101
- Plan: PLAN-0019
- Phase: 3 Editing
- Priority: P2
- Size: L

## Objective

Users select a cell range, copy and paste with spreadsheets, and drag a fill handle, inside the TanStack and shadcn grid.

## Scope

### In Scope

- Range selection with mouse and Shift+arrows; copy as TSV; paste TSV or CSV from the clipboard with a preview when it adds rows; fill handle copies a value or continues a number or date series.
- Applies through TASK-0354; undo of the last batch.
- Keyboard and screen reader announcements; en/vi.

### Out Of Scope

- Cross-dataset paste; formulas.

## Inputs

- DEC-0097 revisit condition; PolarBase spreadsheet cell services as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- DEC-0101 accepted; TASK-0354 and TASK-0350 merged.

## Acceptance Criteria

- Pasting a 5x20 block from a spreadsheet updates those cells in one batch; fill continues `1, 2, 3`; undo restores the previous values.

## Tests

- Playwright clipboard (granted permissions) and fill tests; unit tests for TSV parsing.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

## Handoff Notes

- Use branch `factory/task-0355-dataset-clipboard-fill` from `develop` when implementation begins.
