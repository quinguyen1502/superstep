# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0297
- Task ID: TASK-0312
- QA Owner: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Pass for task acceptance

## Acceptance Coverage

- Playwright created a team dataset with a unique key through Studio, verified the schema, then created and edited a row against the real API.
- The test introduced a competing API update and verified the stale error, draft preservation, reload, and explicit retry. Enter saved, Escape cancelled, and focus returned to the edited cell.
- Search and sorting updated the grid. A 51-row fixture exercised the next and previous server pages.
- Row and dataset deletion required the displayed name. English and Vietnamese locale checks passed. Desktop light and 390 px mobile dark screenshots were captured and inspected.
- npm build, npm test and npm run lint passed. Factory validation passed with a dependency-installation metadata warning.

## Residual Risk

- Local browser coverage used Chrome. Cross-browser behavior and the full GitHub matrix are reviewed through the pull request.
- CSV and workflow integration remain subsequent tasks. Owner approval still gates merge.

## QA Decision

Task acceptance passed locally.

## Owner-approved Mockup Follow-up

- Two live-API Playwright tests covered sidebar position and button alignment, persisted collapse, inline row creation, single selection, keyboard movement, double-click editing, conflict recovery, row selection, sorting, filtering, pagination and deletion. Mobile verified the folded sidebar, edit button and document width.
- Frontend build, TypeScript, lint, 184 frontend tests and Factory validation passed locally. Captured desktop light and mobile dark evidence. GitHub verifies the updated PR head.

## Screenshot Feedback Verification

- Live-API Chrome tests verified that the tab underline reaches the divider and opening either popover leaves the table header in place. The filter accepted a column and value. The sort popover accepted a column and direction and closed with Escape.
- Verified the default row number, checkbox on hover, retained checkbox when selected, and the enlarged row selection target at 390 px. Opened typed confirmation from each three-dot menu and completed row and dataset deletion.
- Inspected the desktop light grid, Filter popover and mobile dark grid screenshots. Build, lint, 184 frontend tests and both Dataset Playwright tests passed.

## Cell Outline and Filter Layout

- Playwright verified the outline on the full table cell and stronger outline on keyboard focus. It measured the desktop Filter controls on a shared centerline and verified that the popup stacks within a 390 px viewport.
- Inspected desktop light and mobile dark screenshots. Build, lint, 184 frontend tests, both Dataset Playwright tests and Factory validation passed.

## Dataset Actions and Query Popovers

- Playwright opened the dataset editor and typed deletion from the same menu. It verified that save status appears below the table and that the header stays in place after save and when either popover opens.
- Verified the Filter condition row, the empty-value filter and Reset, and the Sort draft, Apply and Reset against the live API. Reviewed desktop light screenshots for both popovers and the grid, plus the mobile dark grid.
- Build, lint, 184 frontend tests, both Dataset Playwright tests and Factory validation passed.

## Direct Grid Editing and Toolbar

- Live-API Playwright verified single-click editing, unframed text input, Enter save, Escape discard, save on leaving a field, and switching editors within one row. It also covered the boolean picker and row-revision conflict recovery.
- Measured the checkbox alignment, full-height hover target, right-aligned Add column, and equal heights of the four toolbar buttons. Verified that toolbar search updates the rows and survives a Filter reset.
- Inspected light desktop and dark mobile screenshots. Build, lint, 184 frontend tests, both Dataset Playwright tests and Factory validation passed.

## Schema Dialog and Scope

- Live-API Playwright verified that an existing team is hidden before membership and becomes selectable after joining. Verified the Name label in Create and Edit, and icons on both Studio navigation links.
- Opened Schema from the dataset menu, verified column management and typed delete confirmation, and verified focus restoration on close. Single click selected an existing cell, while double-click and Enter opened the editor.
- Inspected desktop Schema and Personal scope screenshots and the dark mobile grid. Build, lint, 184 frontend tests, both Dataset Playwright tests, four header alignment cases and Factory validation passed.

## Column Controls and Row Confirmation

- Live-API Playwright verified pointer resize, keyboard resize, last-column shrink, width reset, hide and show, and restoring visibility after cancelling Add row. It verified the leading View schema action, fixed column removal label, creation-only constraints hint, and confirmation without a text input for row deletion. Dataset and column removal still use typed confirmation.
- Inspected the Columns menu and the mobile row confirmation. Build, lint, all 312 npm workspace tests, both Dataset Playwright tests, and Factory validation passed.

## Multi-condition Filtering and Multi-column Sort

- Playwright verified that AND excludes and OR includes the fixture row, sort priorities can be reordered before Apply, both active ranks render, and the dataset trigger uses the settings icon. Reviewed both popovers on desktop and the dark mobile grid.
- Backend tests verified AND by default, OR combined with search, multiple sort keys across page boundaries, null placement, legacy single-column sorting and access enforcement. The targeted suite passed 16 checks on SQLite and shared gates, with eight PostgreSQL cases skipped locally. Build, lint, 312 npm workspace tests and two Dataset Playwright tests passed.

## Grid and Dialog Screenshot Follow-up

- Live-API Chrome Playwright verified pointer and keyboard column reordering, visibility, the independent uniqueness indicator, sticky row actions during horizontal scrolling, inline validation and correction, and saving a day selected in the shadcn Calendar.
- Verified direct Schema column removal with typed confirmation, generic row confirmation copy, and dialog geometry with a scrollable body aligned to the outer edge and fixed header and footer. Inspected the Columns, Schema, and Calendar screenshots in desktop light mode and the mobile grid in dark mode.
- Build, lint, all 312 npm workspace tests, 12 Chrome Playwright cases across Dataset and affected dialogs, and Factory validation passed locally. Touch drag was not exercised on a physical device.

## Dataset Preview Follow-up

- Both Dataset Playwright scenarios passed in Chrome with the live API. Verified the Schema header actions, type icons in the picker and calendar suffix, animated drag and keyboard reordering, resizing the final field without inserting another cell, and correcting both invalid email and duplicate unique values.
- Reviewed desktop screenshots for Schema, Filter and Calendar and the dark mobile grid. TypeScript and npm lint passed with existing lint warnings. The isolated local preview remained available during validation.

## Filter Empty States and Invalid Cell Focus

- Both Chrome Dataset scenarios passed. Filter matching stays visible and left-aligned with zero or one condition. Both query popovers show localized empty messages after the last rule is removed.
- A duplicate value and a malformed email blocked clicks on another cell and retained editor focus. Escape discarded the invalid draft and restored the previous value, and the next click selected another cell. TypeScript and strict UI lint passed.

## Row Details and Whole-row Save

- Both Chrome Dataset scenarios passed. Verified matching font family and size when editing a unique cell and the non-editable pointer on the disabled field key.
- Verified view mode, multi-field save in one revision-checked PATCH, rejection of an external row update conflict while retaining the draft, explicit reload, and focus restoration to the row menu after save.
- TypeScript, locale key parity, and strict UI lint passed.

## Unified Row Form

- Both Chrome Dataset scenarios passed. The row menu opens the populated editor directly, the text input's suffix clears its value and retains focus, and cancel preserves the saved value. Conflict recovery reloads the same form and multiple changes still save in a single PATCH.
- TypeScript and strict UI lint passed. The existing local preview picked up the changes.

## Catalog Tooltips and Grid Focus

- Both Chrome Dataset scenarios passed. The expanded catalog has no dataset name tooltip, while the collapsed catalog places it on the right. Only the draft field shows a focus outline during row creation. Clicking outside clears the outline from the draft, selected cell, and invalid editor while preserving their data or draft.
- Verified that clicking another cell still returns focus to an invalid editor and that Escape, keyboard navigation, blur-to-save, and calendar selection continue to work. TypeScript and strict UI lint passed.
