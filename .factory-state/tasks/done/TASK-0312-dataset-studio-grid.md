# Task

## Metadata

- Project: superstep
- Task ID: TASK-0312
- Title: Dataset catalog, schema editor and grid
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Studio

## Objective

Create and operate a dataset entirely from Studio.

## Scope

Dataset navigation, personal/team lists, schema form, TanStack Table and shadcn editors with server-driven grid controls.

## Inputs

Dataset schema and row APIs, docs/ui-conventions.md and the approved design.

## Expected Outputs

Accessible Studio screens for dataset creation, column management and typed row editing.

## Dependencies

[TASK-0310](../done/TASK-0310-dataset-schema.md), [TASK-0311](../done/TASK-0311-dataset-rows.md)

## Acceptance Criteria

- A user can create a team dataset, set a unique key, add or edit a row, filter and sort pages, and cancel or retry an edit.
- Enter and Escape work as designed, stale conflicts keep the draft, and deletions use shared confirmation. Dataset and column deletion require the name. Row deletion requires a confirmation click.
- Both themes and both locales render correctly.
- The catalog starts at the left edge, collapses, and places Create beside the title. The grid supports selection, keyboard movement, inline editing and inline row creation.
- Filter and Sort open without moving the grid. Row numbers give way to selection checkboxes on hover, keyboard focus or selection, and delete actions appear in three-dot menus.
- The active outline follows the full cell perimeter. The Filter condition shares one row on wider screens and stacks on narrow screens. Filter and Sort have Apply and Reset actions.
- Schema, edit and delete are available from the dataset actions menu. Schema opens in a dialog over the grid and is available to readers. Save feedback appears below the grid without shifting the table header.
- A single click selects an editable cell. Double-click, Enter or F2 opens its unframed editor. Enter or leaving a text field saves it, and Escape discards the draft. Search is independent of the Filter popover. Row and header checkboxes share an axis, and cell hover fills the grid cell.
- The Workflows and Datasets header links each include an icon. Create and Edit label the dataset name as Name. Create explains personal ownership and the team membership requirement.
- View schema appears first in the dataset menu. The column removal menu uses a fixed label, and the editor explains when Required and Unique are set. Users can resize and hide columns in the current view.
- Filter applies multiple conditions using Match all (AND) or Match any (OR). Sort supports ordered columns with independent directions. The dataset actions use a settings icon.
- Columns supports pointer and keyboard reordering and an eye toggle for each field. Row actions stay pinned during horizontal scroll. Draft fields use the cell editor appearance, expose localized validation feedback, and use the shadcn Calendar for dates.
- Schema shows Remove column beside Edit. Row deletion uses generic confirmation copy. Dataset form headers and footers remain in place when their body scrolls to the dialog edge.

## Validation Plan

Run npm test, lint and build, plus Playwright for create/edit/filter/delete on desktop and a narrow viewport.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)
- [Review](../../artifacts/REV-0297-TASK-0312-dataset-studio-grid.md)
- [QA](../../artifacts/QA-0297-TASK-0312-dataset-studio-grid.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-12: Created during owner-approved requirements planning.
- 2026-11-12: Started on an explicit stack over TASK-0311. Implemented the protected Studio area, dataset and schema forms, and server-driven editable grid. Build, lint, locale checks and Playwright passed. Moved to review.

- 2026-11-12: The owner approved the revised catalog and spreadsheet mockup. Applied the full-width workbench, compact sidebar, inline grid row drafts and keyboard navigation on the existing review branch.
- 2026-11-12: Addressed the owner's screenshot feedback on tab alignment, grid colors, filter and sort popovers, delete menus and row numbering.
- 2026-11-12: Applied the follow-up feedback on full-cell selection and horizontal Filter controls.
- 2026-11-12: Moved dataset editing into the actions menu and save feedback to the grid footer. Aligned header labels with icons and used Polarbase's rule-row and action-footer patterns for Filter and Sort.
- 2026-11-12: Applied the direct-edit, checkbox alignment, standalone search, neutral selection, action sizing, and full-cell hover feedback.
- 2026-11-12: Moved Schema to a dialog, unified the Studio resource navigation, clarified ownership in Create, and restored double-click editing.
- 2026-11-12: Added TanStack column sizing and visibility controls and applied the owner's confirmation and wording feedback.
- 2026-11-12: Added server-driven multi-condition filtering and multi-column sorting. Changed the dataset action trigger to a settings icon.
- 2026-11-12: Applied the screenshot feedback on Columns, sticky actions, schema removal, inline drafts, validation, date picking and scrollable dialog bodies.

- 2026-11-12: Replaced the grid and Columns fingerprint with a localized Unique badge, keeping the field type icon.
- 2026-11-12: Matched the calendar suffix and field icons, added animated column reordering, removed the grid spacer, moved Add column into the schema header, and aligned Filter and inline error layouts.

- 2026-11-12: Kept Filter matching left-aligned, added empty query states, retained the invalid cell editor until corrected or discarded, and adjusted header label alignment.

- 2026-11-12: Added read-only row details and a whole-row editor with a single revision-checked save. Matched inline value typography and clarified the disabled field-key cursor.

- 2026-11-12: Opened the row form directly for viewing or editing, tightened the field labels, and moved the clear action into the text input.

- 2026-11-12: Limited dataset name tooltips to the collapsed sidebar and placed them to the right of the icons.

- 2026-11-12: Separated grid selection from the keyboard tab stop, kept draft focus independent, and cleared cell highlighting on outside clicks.

- 2026-11-12: The owner completed the Studio review and authorized continuation of the Dataset plan.

## Handoff Notes

Studio is stacked on the Dataset rows branch for PR #368. Keep follow-up tasks stacked until the integration PRs are merged.
