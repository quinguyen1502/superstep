# Task

## Metadata

- Project: superstep
- Task ID: TASK-0366
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Expose the Formula preview in the Dataset Schema and make stored results usable in the read-only Rows experience.

## Dependencies

- [Formula persistence](../done/TASK-0365-dataset-formula-persistence.md). Integration follows persistence in PR #424 and the evaluator in PR #423.
- [Design addendum](../../artifacts/DES-0008-dataset-formulas-and-relations.md), [architecture](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md), [plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md).

## Scope

- Add an authorized, non-mutating Formula preview for an existing row or sample values.
- Add the approved schema editor, result kind, field insertion and error placement. Keep configuration behind the existing opt-in setting.
- Show computed scalar results and localized diagnostics in Rows. Reuse the existing filters, sorts, summaries and displays. Computed cells are excluded from every Studio and workflow write mapping.

## Acceptance Criteria

- A manager can add and update a Formula expression and preview its value. Sample inputs are available for an empty dataset. Invalid expressions and per-row null or error states are distinguishable. Preview makes no stored changes.
- Formula label and field picker are keyboard accessible and compatible with mobile, light and dark theme and EN/VI.
- Viewer can browse Formula results. Row editors, copy/paste, fill, row duplication, CSV mappings, Dataset node and Agent write settings treat computed columns as read-only.
- The server still refuses unauthorized previews and malformed definitions. Project export stays gated until parity.

## Validation Plan

- Run SQLite/PostgreSQL Formula integration tests, frontend build and lint, locale tests, and Playwright with real Formula-backed rows in Studio.

## Activity Log

- 2026-11-21: Continued the owner-approved Dataset plan after the persistence slice passed local QA.
- 2026-11-21: Implemented the Formula schema editor, live and sample preview, read-only results and diagnostics. Validated the Studio and database contracts and moved to review.

- 2026-11-21: The owner approved merging PR #425 into develop. Review and QA passed. Final-head CI gates integration.

## Review And QA

- [Review](../../artifacts/REV-0355-TASK-0366-dataset-formula-studio.md)
- [QA](../../artifacts/QA-0355-TASK-0366-dataset-formula-studio.md)
