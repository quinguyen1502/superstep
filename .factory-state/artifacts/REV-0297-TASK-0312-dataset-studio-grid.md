# Review

## Metadata

- Project: superstep
- Review ID: REV-0297
- Task ID: TASK-0312
- Reviewer: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Approved for QA

## Scope

Reviewed the authenticated Datasets route, catalog and scope selection, schema forms, typed row editors, server-driven grid and both locale catalogs. Reviewed the TanStack Table package and lockfile changes against the accepted decision.

## Findings

- No blocking findings.
- TanStack Table 8.21.3 and its pinned table core are MIT-licensed. The component uses its controlled table state and renders existing shadcn components. The table instance stays within the Dataset grid.
- Row editing uses a revision and preserves the draft when the row changes. Refresh exposes the server value and requires a second explicit save.
- Dataset, column and row removal use the shared typed confirmation. The API remains responsible for access and concurrency.
- CSV and explicit workflow grants are separate tasks.

## References

- [Design](DES-0007-datasets.md)
- [Decision](../decisions/DEC-0097-dataset-grid-and-export.md)
- [Task](../tasks/done/TASK-0312-dataset-studio-grid.md)

## Owner-approved Mockup Follow-up

- Rechecked the flush catalog, compact rail, toolbar, keyboard focus, row selection and typed inline draft against the approved mockup. The implementation uses shadcn controls and Studio theme tokens.
- No blocking findings in the follow-up. Existing shared confirmation remains the row, column and dataset delete path.

## Screenshot Feedback

- Reviewed the grid-specific theme tokens in both themes, the flush tab divider and the anchored shadcn popovers. The sort column and direction can be selected in one opening.
- The numbered gutter remains a click target and the selection checkbox stays available to keyboard and assistive technology users. The three-dot menus use localized labels and keep the shared typed confirmation for all three delete actions.
- The active outline and fill now follow the table cell. Keyboard focus has a stronger outline. Filter uses the existing shadcn controls in one row on wider screens and stacks them on narrow screens.

## Dataset Actions and Query Popovers

- Reviewed the shared dataset actions menu, the save status in the grid footer, and the column label alignment. The dataset menu opens the existing editor and typed deletion confirmation.
- The layout follows the [Polarbase Filter footer](https://github.com/polarbase-team/polarbase/blob/5a717f4a1a64777d8c27cbf5fc09f4833d386d28/client/src/app/shared/field-system/filter/filter-option/filter-option.component.html) and [Sort rules and footer](https://github.com/polarbase-team/polarbase/blob/5a717f4a1a64777d8c27cbf5fc09f4833d386d28/client/src/app/shared/spreadsheet/components/view-options/data-view-options/data-view-options.component.html). Superstep keeps one filter condition and one sort column. Edits in the popovers take effect on Apply, and Reset restores the corresponding defaults.

## Direct Grid Editing and Toolbar

- Used the [Polarbase grid styles](https://github.com/polarbase-team/polarbase/blob/5a717f4a1a64777d8c27cbf5fc09f4833d386d28/client/src/app/shared/spreadsheet/spreadsheet.component.scss) and [search placement](https://github.com/polarbase-team/polarbase/blob/5a717f4a1a64777d8c27cbf5fc09f4833d386d28/client/src/app/shared/spreadsheet/spreadsheet.component.html) as references. Applied the Studio neutral theme to full-cell hover and selection. The header and row checkboxes use the same column center.
- The owner's requested single click opens the unframed typed editor. Switching cells saves the previous value before opening the next editor and uses the returned revision for a second edit on that row. Conflicts retain the draft and require an explicit retry.
- Search stays visible in the toolbar and debounces requests independently of Filter. Filter, Sort, Add row, and Add column share the default button size. The Schema action aligns with the right edge.

## Schema Dialog and Scope

- The dataset menu opens Schema for readers and keeps edit and delete permission-gated. The dialog leaves the grid mounted, supports the existing column actions and returns focus to the dataset menu when closed.
- Reviewed the shared Workflows and Datasets navigation and the single-click selection and double-click editing paths. Enter and F2 remain keyboard editing entry points.
- The scope copy follows the existing ownership and membership rules. The API assigns either personal ownership or a team, checks membership during creation, and metadata edits preserve that ownership.

## Column Controls and Row Confirmation

- TanStack Table manages column sizing and visibility. Superstep renders the resize handle, keyboard sizing and Columns menu. The layout preserves the grid width, and Add row exposes all fields for entry before restoring the previous visibility.
- Reviewed the fixed Remove column label, the leading View schema action, and the hint for immutable column constraints. The owner approved a click-only exception for row deletion. The shared dialog keeps the typed check as its default, and row deletion still sends the expected row revision.

## Multi-condition Filtering and Multi-column Sort

- Filter uses a single AND or OR mode for the current condition list. Search remains an independent restriction. Sort applies the columns in the order shown in the popover, with the existing row ID tie-breaker for stable pagination.
- The row query accepts `filter_mode` and an ordered `sorts` list. Callers that send the existing `sort` and `descending` fields retain their behavior. The repository still applies dataset scope independently of the filter expression.
- Both rule lists are bounded at 12. The dataset menu trigger is a settings icon, and column and row actions keep the three-dot trigger.

## Grid and Dialog Screenshot Follow-up

- The Columns layout follows [Polarbase's column options](https://github.com/polarbase-team/polarbase/blob/5a717f4a1a64777d8c27cbf5fc09f4833d386d28/client/src/app/shared/spreadsheet/components/view-options/column-view-options/column-view-options.component.html). Column order is view state and never mutates the dataset schema. Type and uniqueness indicators render independently.
- The shadcn Calendar shares typed date fields with the row editor, row draft, default values and filters. Native validity errors are localized inline and keep the draft. Dataset and column deletion continue to require typed confirmation.
- Reviewed Studio dialogs and migrated forms and scrollable lists to the shared edge-aligned body. Specialized scrolling panes such as the code editor and chat transcript retain their own scroll behavior.

## Owner Review Completion

- Reviewed the final grid, unified row form, and sidebar behavior with the owner. The owner reported the review complete on 2026-11-12. No open review findings remain.
