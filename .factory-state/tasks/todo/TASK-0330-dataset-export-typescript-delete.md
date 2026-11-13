# Task

## Metadata

- Project: superstep
- Task ID: TASK-0330
- Title: Add TypeScript standalone delete and Agent writes
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Export

## Objective

Make an exported TypeScript project delete rows and perform Agent writes with the same contract as the Python export.

## Scope

### In Scope

- Standalone SQLite and PostgreSQL `delete_row`, insert, and upsert for Agent writes, including receipts and the shared writer lock.
- The same binding manifest operations and connected token denial as the Python export.
- The TypeScript section of `docs/dataset-export.md`.
- A mixed graph that reads through the Superstep API and deletes through standalone storage.

### Out Of Scope

- The Python runtime and the Python section of `docs/dataset-export.md`.
- Snapshot seeding, customer-table mapping, automatic sync, and the handbook.

## Inputs

- `backend/app/engine/dataset_typescript_standalone.py` and the Python contract from TASK-0329's acceptance, or from TASK-0325 and TASK-0327 when this task starts first.
- Existing TypeScript standalone fixtures.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Discovery:
- Clarifications:

## Expected Outputs

- TypeScript standalone delete and Agent writes, export tests, and the TypeScript export doc.

## Implementation Notes

- Keep the current Node and Deno SQLite loading rules. Do not add `better-sqlite3`.
- Setup stays repeatable and must not remove existing rows.
- Cross-language hash equality is not required. Observable results and error codes must match.

## Constraints

- Match the Studio and Python field, type, unique-key, and error contract.
- Edit only the TypeScript portion of `docs/dataset-export.md`.

## Dependencies

- [TASK-0325](TASK-0325-dataset-delete-runtime.md)
- [TASK-0327](TASK-0327-dataset-agent-write.md)

## Acceptance Criteria

- Generated TypeScript projects pass lookup, Agent insert and upsert, delete, receipt replay, and changed-payload conflict on SQLite and PostgreSQL.
- A connected token without delete capability cannot delete.
- Setup run twice keeps the rows that remain. Schema mismatch fails without changing stored rows.

## Validation Plan

- Run the TypeScript standalone and project-export tests with the repo's Deno version on SQLite and PostgreSQL.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- This task may proceed beside TASK-0329. Neither task edits the other language section.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.

## Handoff Notes

- Start from `develop` after TASK-0325 and TASK-0327 merge, on `factory/task-0330-dataset-export-typescript-delete`.
