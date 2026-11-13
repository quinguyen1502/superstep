# Task

## Metadata

- Project: superstep
- Task ID: TASK-0313
- Title: Dataset CSV preview, import and export
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

Seed and extract operational tables as CSV from Studio.

## Scope

CSV schema suggestions, editable mapping, bounded preview, per-row errors, explicit import and permission-checked export.

## Inputs

Dataset type validation and Studio grid; standard upload size and error handling.

## Expected Outputs

CSV services, routes and Studio actions for new and existing datasets.

## Dependencies

[TASK-0311](../done/TASK-0311-dataset-rows.md), [TASK-0312](TASK-0312-dataset-studio-grid.md)

## Acceptance Criteria

- Quoted separators, embedded newlines, BOM, type mismatches and duplicate keys are handled with actionable messages.
- Preview changes no rows.
- Import is atomic within its documented bounds and rejects stale schema.
- CSV export respects authorization, handles spreadsheet formula injection and includes the authorized result beyond one UI page.

## Validation Plan

Run backend parser/permission tests and Playwright for preview, invalid mapping, corrected import and download.

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

Start from integrated develop on `factory/task-0313-dataset-csv` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
