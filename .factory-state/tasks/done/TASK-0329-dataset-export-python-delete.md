# Task

## Metadata

- Project: superstep
- Task ID: TASK-0329
- Title: Add Python standalone delete and Agent writes
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Export

## Objective

Make an exported Python project delete rows and perform Agent writes with the same contract as Studio.

## Scope

### In Scope

- Standalone SQLite and PostgreSQL `delete_row`, insert, and upsert for Agent writes, including receipts and the shared writer lock.
- Binding manifest entries for the operations the graph uses.
- Connected export calls for those operations, including a token without `allow_delete` being rejected.
- The Python section of `docs/dataset-export.md`.
- A mixed graph that reads through the Superstep API and deletes through standalone storage.

### Out Of Scope

- The TypeScript runtime and the TypeScript section of `docs/dataset-export.md`.
- Snapshot seeding, customer-table mapping, and automatic sync.
- Handbook pages.

## Inputs

- `backend/app/engine/dataset_python_standalone.py`, `docs/dataset-export.md`, and the operations from TASK-0325 and TASK-0327.
- Existing Python standalone fixtures.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Review: [REV-0313](../../artifacts/REV-0313-TASK-0329-dataset-export-python-delete.md)
- QA: [QA-0313](../../artifacts/QA-0313-TASK-0329-dataset-export-python-delete.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Python standalone delete and Agent writes, export tests, and the Python export doc.

## Implementation Notes

- Setup stays repeatable and must not remove existing rows.
- A missing delete leaves no receipt. A replay after the row is gone returns the stored result.
- Default archives still contain no rows and no secrets.

## Constraints

- Match the Studio field, type, unique-key, and error contract. Destination ids, paths, and credentials stay in deployment settings.
- Edit only the Python portion of `docs/dataset-export.md`.

## Dependencies

- [TASK-0325](../done/TASK-0325-dataset-delete-runtime.md)
- [TASK-0327](../done/TASK-0327-dataset-agent-write.md)

## Acceptance Criteria

- Generated Python projects pass lookup, Agent insert and upsert, delete, receipt replay, and changed-payload conflict on SQLite and PostgreSQL.
- A connected token without delete capability cannot delete. A token with it can.
- Setup run twice keeps the rows that remain. Schema mismatch fails without changing stored rows.

## Validation Plan

- Run the Python standalone, connected export, and project-export tests on SQLite and PostgreSQL.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- TASK-0330 owns the TypeScript section of the export doc. The tasks may run in parallel only if each stays in its section.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.
- 2026-11-13: Branched `factory/task-0329-dataset-export-python-delete` on TASK-0328. Added standalone Delete row, Agent insert and upsert in the exported Python runtime, manifest operations for Agent writes, and the Python export doc. Review REV-0313. QA QA-0313. Moved to done.

## Handoff Notes

- `dataset_standalone` supports `delete_row` under the writer lock with a receipt; a missed delete stores none.
- `dataset_agent` takes the tool's operations, write fields, and key. The generated tool node derives one operation ID per model call from the step's checkpoint namespace and the call id.
- The exported offline mock model fills enums and Dataset write values like the Studio mock.
- TASK-0330 mirrors this in the TypeScript runtime.
