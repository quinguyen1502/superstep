# Task

## Metadata

- Project: superstep
- Task ID: TASK-0331
- Title: Accept Dataset writes and document the public boundary
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Acceptance

## Objective

Prove one support-ticket path across the new operations and document the boundary in both handbooks.

## Scope

### In Scope

- One automated path that grants write without delete, has an Agent upsert a ticket, finds it from a public entry, then deletes it from a Studio Run after delete is enabled.
- Denial checks for public delete, a token without delete capability, a read-only Agent tool, and demo mode.
- English and Vietnamese handbook pages stating the delete capability, Agent insert and upsert, and the entries that cannot delete.
- Both handbook builds.

### Out Of Scope

- New screenshots, formula columns, relations, triggers, saved views, calendar and map views, MCP, and embeddings.
- Changes to the export runtime beyond a failing acceptance test.

## Inputs

- Handbook pages `handbook/docs/en/guide/datasets.md` and `handbook/docs/vi/guide/datasets.md`.
- The merged behavior from TASK-0326, TASK-0328, TASK-0329, and TASK-0330.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Acceptance test, handbook updates, and both handbook builds.

## Implementation Notes

- Keep product documentation in English in `docs/`. Vietnamese belongs in the Vietnamese handbook and locale catalogs.
- Do not recapture the existing Dataset screenshots unless the documented screen changed.

## Constraints

- Handbook navigation must keep the Datasets entry in both languages.
- The acceptance test uses the public interfaces from the earlier tasks. It does not add a product feature.

## Dependencies

- [TASK-0326](TASK-0326-dataset-delete-editor.md)
- [TASK-0328](TASK-0328-dataset-public-entry.md)
- [TASK-0329](TASK-0329-dataset-export-python-delete.md)
- [TASK-0330](TASK-0330-dataset-export-typescript-delete.md)

## Acceptance Criteria

- The support-ticket path passes: Agent upsert, public find, denied public delete, Studio delete, and a repeated standalone setup that keeps the remaining rows.
- Python and TypeScript coverage from the export tasks still passes against this path's contract.
- Both handbook languages describe delete, Agent writes, and the entries that cannot delete. Both handbook builds succeed.

## Validation Plan

- Run the new acceptance test and the Dataset export tests on SQLite and PostgreSQL.
- Run both handbook builds from `handbook/README.md`.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- The earlier tasks already cover the detailed matrices. This task is the cross-entry proof and the operator documentation.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.

## Handoff Notes

- Start from `develop` after TASK-0326, TASK-0328, TASK-0329, and TASK-0330 merge, on `factory/task-0331-dataset-writes-acceptance`.
