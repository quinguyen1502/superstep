# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0350
- Task ID: TASK-0359
- QA Owner: Codex
- Created: 2026-11-15
- Updated: 2026-11-15
- Outcome: pass

## Validation Scope

Seeded Studio browser checks in both themes and the frontend validation suite.

## Acceptance Criteria Coverage

- Pass: Dataset tabs have a continuous top border. Detail menu omits the two tab entries, and the tabs still navigate. Verified in Chrome.
- Pass: Subject Count displays 125 above the first row in the long demo grid. Playwright also verifies filtered totals across pages and pinned scrolling.
- Pass: Group title and disclosure icon centers align within two pixels in both themes.
- Pass: New grid filters show no incomplete-condition error and Apply is disabled until the rule is valid.
- Pass: Playwright drops a CSV on the file input, previews a rejected row, remaps it, imports and checks the exported CSV. Selecting a file through the input also passes in the create flow.
- Pass: The native chooser opens with Enter. The dialog shows the chosen filename, and the disabled checkbox has 2px corners and a visible border in both themes.
- Pass: The Schema Team field uses the new list icon.

## Checks Performed

- Frontend lint and production build passed.
- Frontend unit suite passed (191 tests).
- Chrome Playwright passed all 13 tests across `dataset-csv.spec.ts`, `dataset-phase-three.spec.ts` and `datasets.spec.ts`.
- Seeded Chrome smoke checks and screenshots passed in light and dark.
- Factory hygiene and artifact ID checks passed.

## Observations

Chrome emitted a ResizeObserver notification warning during the keyboard filter test. The unmodified develop checkout reproduces it in the same passing test.

## Gaps Or Untested Areas

Full Factory validation reports missing dependencies in the React Native and separate browser-worker environments in this local checkout. Frontend validation and the Studio workflow use their own installed dependencies.

## QA Decision

Pass for owner review.

## Owner Follow-Up Verification

- Seeded Chrome smoke checks in light and dark verify the row index remains visible on horizontal scroll, the action column has its left separator, the Summary count and selector share one line, the layout controls have visible labels, and Checkbox corners are 3px.
- The typed-editor regression checks a unique conflict followed by a click on another cell, a click outside the grid and Tab. The editor stays focused and Escape still discards the edit. Valid click-away saves and picker edits are covered by the existing scenarios.
- Frontend lint, build and 191 unit tests passed.
- All 13 Chrome Playwright Dataset, CSV and Phase 3 tests passed on the final follow-up diff.

## Pagination and Access Follow-Up Verification

- Chrome demo checks in both themes verified the footer at the viewport bottom for the 125-row table in a 720px window and directly below the 12-row table in a 1000px window. Horizontal and vertical scroll were inspected with frozen columns.
- The Summary control displays the metric and value together with the chevron. The active toolbar remains high contrast on hover in both themes.
- All four desktop Access fields match in width and the controls in each row align within one CSS pixel. The mobile view does not overflow horizontally.
- Frontend lint and build passed. The 191 unit tests passed. The expanded Playwright run passed 19 cases, and the remaining three passed on isolated reruns after replacing stale action-menu assertions and allowing browser rounding in the Access dimension check.

## Row Height Follow-Up Verification

- Chrome reproduced Short and Medium at 45px. After removing the data-cell padding constraint and letting the selection label fill its cell, the seeded grid measured Short at 32px, Medium at 40px, and Tall at 56px in both themes.
- Three Playwright scenarios passed, covering exact heights, pinning, scrolling, layout persistence, row selection, and grouping. Frontend lint passed.

## Full-Height Grid Follow-Up Verification

- In a 1440 by 1200 Chrome viewport the long demo grid previously left 74px below its footer. After the change the footer reaches the viewport bottom in both themes. The 12-row grid still places the footer immediately after its rows.
- Verified a four-cell rectangle using both mouse drag and Shift plus arrow keys. The Clipboard menu copied the rectangle as two tab-separated lines containing the expected values.
- Frontend lint and all three targeted Playwright scenarios passed, covering a tall viewport, pinned scrolling, paste, fill and undo.

## Shortcut and Selection Follow-Up Verification

- Verified the selected range color in light and dark, including hover. The grouping trigger keeps readable icon and text colors while active, and returns to its default presentation after clearing grouping.
- The shortcut sheet reuses the Workflow dialog and accessible key caps, with platform-specific modifiers. Verified button and question-mark entry and focus return. Verified the Sort count reflects applied columns and clears on reset.
- Frontend build, lint and 191 unit tests passed. Browser verification covers the keyboard sheet, applied sorting, grouping and clipboard range selection.
