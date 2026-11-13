# Task

## Metadata

- Project: superstep
- Task ID: TASK-0324
- Title: Add a separate Dataset delete capability
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Access

## Objective

Let a manager grant row deletion separately from read and write, without deleting any row yet.

## Scope

### In Scope

- Additive migration after `0066_dataset_receipts` adding `allow_delete`, default false, on workflow grants and Dataset API tokens.
- API reads and writes of that flag for grants and tokens. Existing permission values stay `read`, `write`, and `read_write`.
- Access dialog control, off until enabled, in English and Vietnamese.
- Revoking a grant or token still uses typed confirmation. The API stays a plain delete.

### Out Of Scope

- The `delete_row` operation, Agent writes, public-entry changes, and export runtimes.
- Changing Studio grid row deletion.

## Inputs

- `dataset_workflow_grants` and `dataset_api_tokens` in `backend/app/models/dataset_access.py`.
- Access service, routes, and `frontend/src/components/datasets/dataset-access-dialog.tsx`.
- DEC-0098.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Review: [REV-0308](../../artifacts/REV-0308-TASK-0324-dataset-delete-capability.md)
- QA: [QA-0308](../../artifacts/QA-0308-TASK-0324-dataset-delete-capability.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Migration, grant and token contract, Access control, and tests showing existing records stay non-deleting.

## Implementation Notes

- Do not add `delete` to the permission check constraint.
- A `write` or `read_write` grant does not turn `allow_delete` on.

## Constraints

- Backend layers in `docs/backend-architecture.md`. Locale keys match in English and Vietnamese. shadcn/ui components and theme tokens only.
- No new error code unless the current catalog cannot express an invalid flag.

## Dependencies

- None. Branch from `develop`.

## Acceptance Criteria

- A manager can enable and disable delete on a workflow grant and on a new token. Existing grants and tokens remain false.
- Read, write, and read-and-write behavior is unchanged.
- The control is keyboard reachable in both languages. Revoke still requires the typed name and sends no confirm field.

## Validation Plan

- Run the Dataset access, migration, layer, and API-envelope tests on SQLite and PostgreSQL.
- Run the locale parity test and the Dataset access Playwright spec.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- REQ-0099 and DEC-0098 are the UX and storage direction. No new design or architecture artifact.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.
- 2026-11-13: Owner asked for task-start. Branched `factory/task-0324-dataset-delete-capability` from `develop` at `6a2e43a6` and moved to doing. No source edits.
- 2026-11-13: Owner asked to implement through finish-pr. Added `allow_delete` on grants and tokens. Review REV-0308. QA QA-0308. Moved to done.

## Handoff Notes

- Branch `factory/task-0324-dataset-delete-capability` from `develop` at `6a2e43a6`. One commit, Ready PR into `develop`. Do not merge until the owner asks and required CI is green.
- Leave the untracked stale TASK-0310–TASK-0322 copies and the two HTML previews uncommitted.
