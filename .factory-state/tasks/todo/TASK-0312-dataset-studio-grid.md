# Task

## Metadata

- Project: superstep
- Task ID: TASK-0312
- Title: Dataset catalog, schema editor and grid
- Status: todo
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

[TASK-0310](../done/TASK-0310-dataset-schema.md), [TASK-0311](TASK-0311-dataset-rows.md)

## Acceptance Criteria

- A user can create a team dataset, set a unique key, add or edit a row, filter and sort pages, and cancel or retry an edit.
- Enter and Escape work as designed, stale conflicts keep the draft, and deletions use shared typed confirmation.
- Both themes and both locales render correctly.

## Validation Plan

Run npm test, lint and build, plus Playwright for create/edit/filter/delete on desktop and a narrow viewport.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-12: Created during owner-approved requirements planning.

## Handoff Notes

Start from integrated develop on `factory/task-0312-dataset-studio-grid` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
