# Task

## Metadata

- Project: superstep
- Task ID: TASK-0355
- Title: Add range selection, clipboard paste, and fill to the Dataset grid
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

Users select a cell range, copy and paste with spreadsheets, and fill a selection, using the TanStack Table cell selection feature and writing custom code only for what the library does not cover.

## Scope

### In Scope

- Library: TanStack Table v9 cell selection feature for click, drag, Shift+arrow extension, and multi-range selection, and its selected-range data API for copy; TSV escaping as in the TanStack cell selection guide; the browser Clipboard API; a maintained TSV/CSV parser for paste (for example Papa Parse) instead of a hand-written parser.
- Custom (no library support, high value): mapping pasted TSV onto typed columns from the anchor cell, with a preview when the paste would add rows, sent as one TASK-0354 batch.
- Custom (small, high value): fill down and fill right of the selected range (Ctrl+D, Ctrl+R, and a menu item) copying the first row or column, and one-step undo of the last batch.
- Keyboard and screen reader announcements; en/vi.

### Out Of Scope

- Drag fill handle and series continuation (no library support; lower value; revisit after use).
- Multi-level undo history; cross-dataset paste; formulas.
- Source-installed grids (Gigatable) or young single-maintainer grids (MonkeyTab), evaluated in DEC-0101.

## Inputs

- DEC-0101; TanStack Table v9 cell selection guide; PolarBase spreadsheet cell services as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- DEC-0101 accepted (2026-11-13); TASK-0354 and TASK-0350 (TanStack Table v9 upgrade) merged.

## Acceptance Criteria

- Selection and copy use the TanStack cell selection API with no custom selection model.
- Pasting a 5x20 block from a spreadsheet updates those cells in one batch; Ctrl+D fills the selection with the first row's values; undo restores the previous values.
- The PR lists every custom module and why the library could not cover it.

## Tests

- Playwright clipboard (granted permissions), fill down, and undo tests; unit tests for the paste mapping.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): rescoped library-first per DEC-0101; drag fill handle and series fill moved out of scope.

## Handoff Notes

- Use branch `factory/task-0355-dataset-clipboard-fill` from `develop` when implementation begins.
