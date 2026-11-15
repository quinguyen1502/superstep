# Review

## Metadata

- Project: superstep
- Review ID: REV-0350
- Task ID: TASK-0359
- Reviewer: Codex
- Created: 2026-11-15
- Updated: 2026-11-15
- Outcome: approved for QA

## Review Scope

Review the Dataset detail tabs, grid, filter, CSV import and display controls, and the shared Checkbox style.

## Reference Artifacts

- [TASK-0359](../tasks/done/TASK-0359-dataset-ui-polish.md)
- [UI conventions](../../docs/ui-conventions.md)

## Findings

- No blocking findings.
- The summary row uses the same visible column order and pinned offsets as grid headers. The virtualizer accounts for the header height and updates after resize.
- The grid filter retains its apply guard and follows the existing Sort behavior. The node filter keeps its existing feedback.
- Browsing and dropping both use the existing CSV preview and validation path. The native file control remains focusable, and actions still obey their existing permissions.
- Feedback, accessible names and hints use locale catalogs. Styling uses theme tokens, and destructive actions retain confirmation.

## Validation Review

Frontend lint, build and unit tests pass. Playwright and two-theme browser evidence are tracked in the QA record.

## Assumptions

The owner allowed either moving the summary above rows or making it sticky. The implementation places it below column headers. The shared Checkbox styling applies in every area using the primitive.

## Review Decision

Approved for QA.

## Owner Follow-Up

- The index stays visible during horizontal scrolling and is excluded from the configured count of pinned data columns. The boundary uses the border token and remains visible above scrolling cells.
- The summary operation and value share one line with a separate accessible output. The full result is available in the title.
- Invalid inline input keeps focus for pointer and keyboard attempts to leave. The editor still allows correction, popup controls, retry and Escape. Form-wide row operations continue to use their existing explicit Save controls.

## Pagination and Access Follow-Up

- Separate table borders stay attached to sticky cells while adjacent cells scroll underneath. The scroll viewport reserves space for the pagination bar and short grids keep their footer directly after the content.
- Toolbar state uses the shared primary tokens for expanded, pressed, or configured controls. Summary keeps a separate live output even though the visible result is inside the select.
- Access forms share two equal input tracks and one action track at desktop widths. Narrow layouts stack the fields. Permission inputs keep their previous authorization and save behavior.
- Clipboard commands still support keyboard shortcuts directly in the grid. Column rule violations currently use the generic inline save-error treatment and were raised for discussion.
