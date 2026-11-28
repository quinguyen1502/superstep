# Task

## Metadata

- Project: superstep
- Task ID: TASK-0362
- Title: Fix Dataset cell interactions and polish editor controls
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-15
- Updated: 2026-11-21
- Priority: P1
- Size: S

## Objective

Release the grid when inline option pickers close, open the picker directly when editing a cell, and make long cell values readable from the grid. Polish empty option menus, dark panel tabs, and the template add-field action.

## Acceptance Criteria

- Dismissing a single-select picker releases the grid. Failed saves stay editable.
- Double-click and Enter open the multi-select menu. Closing it saves the checked options, and Escape discards the edit.
- Truncated or multiline content opens in a scrollable preview anchored to the focused cell. The preview is capped at 9 rem and row height stays fixed.
- Optional multiline values can be cleared by deleting their contents. The textarea omits the separate clear button.

- Default value menus show an empty state before options exist.
- Active editor panel tabs display the foreground underline in dark mode.
- Template add-field actions use an unframed icon button and still open the creation dialog.

## Validation Plan

Run frontend lint, build and tests, Dataset browser regressions, and Factory hygiene. Inspect the cell preview in both themes.

## Related Artifacts

- [Dataset grid and controls](../done/TASK-0359-dataset-ui-polish.md)
- [Dataset Phase 3](../../artifacts/REQ-0101-datasets-phase-3.md)

## Review and QA

- Verified that opening the menu from an existing row preserves draft-row and filter picker behavior. The browser tests cover dismissal, the unique-value error and recovery, multi-select cancellation and commit, long-value scrolling, and clearing optional notes.
- Visually inspected the expanded cell in light and dark mode. The content is capped at 9 rem and supports wheel scrolling and Page Up or Page Down.
- 2026-11-21: Frontend build and lint passed, with 191 unit tests and 13 Dataset Playwright tests passing. Factory hygiene and diff checks passed. Repository-wide CI runs on the draft pull request.

- 2026-11-21: Replaced the expanding row with an anchored overlay after owner feedback. Verified the row height, overlay anchor and height cap, wheel and keyboard scrolling, and range selection in both themes. All 13 Dataset Playwright tests passed again.

- 2026-11-21: Joined the focused cell and preview with one continuous border. Anchored the preview to the full cell width and removed the shared edge for both vertical placements. Verified alignment and row height in both themes, flipped placement in a short viewport, and batch range actions. Both focused Playwright tests, frontend lint and build, and Factory hygiene passed.

- 2026-11-21: Added the localized empty state for Select and Multi-select defaults, restored the active underline in dark mode, and used a ghost add-field action in template editors. Build, lint, Factory hygiene, and four Playwright cases passed. Inspected the empty menu and both editor controls at phone width.

- 2026-11-21: The owner requested the remaining delivery steps after reviewing the UI adjustments. Final review found no blocking issues. The production build, lint, 191 frontend unit tests, eight focused Playwright tests, Factory hygiene, and diff checks passed. Recorded the reviewed state in one commit for GitHub CI.
