# Task

## Metadata

- Project: superstep
- Task ID: TASK-0328
- Title: Open granted Dataset reads and writes on public entries
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Runtime

## Objective

Let a saved workflow use its Dataset grant from chat and the API trigger, while delete and demo mode stay denied.

## Scope

### In Scope

- Public classification remains demo mode, or a run source other than Studio Run (`ui`), schedule, or workflow test. Child workflow-tool runs use the top run's source.
- Find, Get, Insert, and Upsert, including Agent writes, succeed on Studio chat, public chat, and the API trigger when the saved workflow grant allows the operation.
- `delete_row` on those entries returns `DATASET_GRANT_DENIED` even when `allow_delete` is true.
- Demo mode rejects every Dataset operation. Unsaved workflows stay denied.
- Resume and recovery honor a grant removed while the run waits.

### Out Of Scope

- New public channels, Agent delete, and changes to snapshot or CSV behavior.
- Export runtimes and the handbook.

## Inputs

- `RunService._bind_dataset` and `DatasetAccessService.workflow_dataset`.
- `delete_row` from TASK-0325 and Agent writes from TASK-0327.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Discovery:
- Clarifications:

## Expected Outputs

- The public operation matrix and tests for chat, the API trigger, schedules, Studio Run, demo mode, nested tools, and resume.

## Implementation Notes

- Replace the blanket public denial. Do not treat a public run as unauthenticated access to a dataset the workflow cannot use.
- A workflow without the matching grant still receives `DATASET_GRANT_DENIED`. A person who cannot see the dataset still receives not found from Studio.

## Constraints

- Backend layers in `docs/backend-architecture.md`. Reuse `DATASET_GRANT_DENIED`.
- Studio chat stays in the public group, as REQ-0099 assumes.

## Dependencies

- [TASK-0325](TASK-0325-dataset-delete-runtime.md)
- [TASK-0327](TASK-0327-dataset-agent-write.md)

## Acceptance Criteria

- Studio chat, public chat, and an API trigger can find and upsert when granted, and cannot delete.
- Studio Run and a schedule can delete when delete is enabled.
- Demo mode cannot use Dataset operations. A nested tool follows its top run.
- A grant removed during a wait is denied when the run resumes.
- An Agent write follows the same entry rule as the Dataset node.

## Validation Plan

- Run Dataset access, runtime, Agent, and public-chat tests on SQLite and PostgreSQL.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- No new design artifact. The visible result is that previously denied chat and API runs now perform granted lookups and writes.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.

## Handoff Notes

- Start from `develop` after TASK-0325 and TASK-0327 merge, on `factory/task-0328-dataset-public-entry`.
