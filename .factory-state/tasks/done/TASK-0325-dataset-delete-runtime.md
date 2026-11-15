# Task

## Metadata

- Project: superstep
- Task ID: TASK-0325
- Title: Execute workflow Dataset row deletion
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Runtime

## Objective

Remove one dataset row from a saved workflow or a connected token when delete is granted.

## Scope

### In Scope

- `delete_row` by `row_id` or by one unique `key` and `value`, as DEC-0098 defines.
- Receipt, writer lock shared with insert and upsert, and audit of identifiers only.
- Connected execution that requires the token's `allow_delete`.
- Engine validation for the operation. Tests may supply the binding without the Studio editor.
- Dry-run and workflow-test behavior that leaves stored rows unchanged.

### Out Of Scope

- The Dataset node editor, Agent tools, and the public-entry policy change. Public runs stay denied for every Dataset operation until TASK-0328.
- Standalone Python and TypeScript execution.
- Studio grid deletion.

## Inputs

- Dataset runtime, row service, connected service, and the grant flag from TASK-0324.
- Existing receipt and unique-key behavior.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Review: [REV-0309](../../artifacts/REV-0309-TASK-0325-dataset-delete-runtime.md)
- QA: [QA-0309](../../artifacts/QA-0309-TASK-0325-dataset-delete-runtime.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Workflow and connected `delete_row`, with denial, replay, and conflict tests.

## Implementation Notes

- Check `allow_delete`. Do not treat `write` or `read_write` as permission to delete.
- A missing row raises `DATASET_ROW_NOT_FOUND` and does not store a receipt.
- Reuse `DATASET_GRANT_DENIED`, `DATASET_RECEIPT_CONFLICT`, `DATASET_NODE_ARGUMENTS_INVALID`, `AUTH_TOKEN_INVALID`, and the existing schema errors.

## Constraints

- Backend layers in `docs/backend-architecture.md`. The Studio row-delete route stays a plain DELETE.
- Preserve row, byte, and query limits.

## Dependencies

- [TASK-0324](../done/TASK-0324-dataset-delete-capability.md)

## Acceptance Criteria

- A workflow with delete enabled removes one row by id and one row by unique key. A workflow or token without delete enabled cannot.
- Replaying a completed delete returns the first result after the row is gone. A different payload for that identity conflicts.
- A test or dry-run deletes nothing. Concurrent delete and upsert leave one committed result.
- A key that is no longer unique, or a field the schema no longer has, fails and leaves rows in place.
- Audit records the dataset, row id, workflow or credential, and run, and does not record cell values.

## Validation Plan

- Run Dataset runtime, receipt, connected, layer, and API-envelope tests on SQLite and PostgreSQL, including concurrent delete and upsert.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- The Studio editor lands in TASK-0326. This task proves the operation through the engine and connected API.
- Public denial stays as it is on `develop` until TASK-0328.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.
- 2026-11-13: Owner asked for task-start. Branched `factory/task-0325-dataset-delete-runtime` from `origin/develop` at `a83ef088` and moved to doing. No source edits.
- 2026-11-13: Owner asked to implement through finish. Added workflow and connected `delete_row`. Review REV-0309. QA QA-0309. Moved to done.

## Handoff Notes

- Branch `factory/task-0325-dataset-delete-runtime` from `origin/develop` at `a83ef088`. One commit, Ready PR into `develop`. Do not merge until the owner asks and required CI is green.
- Leave the untracked stale TASK-0310–TASK-0322 copies and the two HTML previews uncommitted.
