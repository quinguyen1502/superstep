# Review

## Metadata

- Project: superstep
- Review ID: REV-0329
- Task ID: TASK-0340
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for the Dataset Studio viewer, empty, and not-found states, the row delete confirmation, and the CSV issue list against REQ-0100, PLAN-0018, DES-0007, ARCH-0003, `docs/ui-conventions.md`, and the TASK-0340 acceptance criteria. Grid layout (TASK-0341) was checked to stay unchanged. TASK-0335 merged first, and its per-dataset manage check was combined with these states.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md

## Findings

### Blocking

- None.

### Non-Blocking

- Two reasons exist: the view-only reason (no `resources.manage`) and TASK-0335's manager reason (a team member who is not the dataset manager). Dataset-level controls show whichever applies, in the dataset menu and the Schema dialog; row controls follow `resources.manage` only.
- The view-only note appears only after the current user loads, so it does not flash for managers.
- The issue list says it shows the first issues found once the server limit of 100 is reached; issues found later can belong to earlier lines.

## Standards And Architecture Alignment

- Show-and-explain: Create, Add row, Edit dataset, Access, Import CSV, Delete dataset, Delete row, Add column, Edit column, and Remove column stay visible and disabled for users who may not change the dataset. The reason is an inline note linked with `aria-describedby`, repeated in the dataset menu and the Schema dialog. Export CSV and View schema stay enabled.
- `DATASET_NOT_FOUND` shows a neutral empty state with a link back to the catalog and no Retry. Other load errors keep the destructive alert with Retry.
- The empty catalog uses the shadcn `Empty` block with Create, Import CSV, and a handbook link. "Select a dataset" no longer shows while the catalog is empty.
- The CSV preview service adds the rejected value, cut to 200 characters, to each issue and sorts issues by line. The dialog cuts the value to 60 characters, replaces field keys with column labels, and counts issues per error code. The alert icon is top-aligned with its title.
- No factory IDs or state paths in product code.

## Design Alignment

- The row delete confirmation names the row by its first unique field with a value, else by its row ID (DES-0007).
- The CSV preview table shows the target field, or Skipped, under each source header.
- English and Vietnamese catalogs and the handbook changed together.

## Validation Review

- `e2e/dataset-studio-states.spec.ts` covers the empty catalog, not found, the viewer, row delete naming, and the CSV issue list, each in en and vi, light and dark, with screenshots attached.
- Unit tests cover the issue sort, the counts, and value shortening. Backend tests cover the issue order and value truncation. `e2e/datasets.spec.ts` now expects the named delete text.

## Assumptions

- The viewer reason names the `resources.manage` permission as the Users settings label shows it.

## Required Follow-Up

- None.

## Review Decision

Approved for QA. No blocking findings.
