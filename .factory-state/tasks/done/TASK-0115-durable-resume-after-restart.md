# Task

## Metadata

- Project: superstep
- Task ID: TASK-0115
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0071
- Design IDs: DEC-0062
- Architecture IDs: none

## Objective

Prove that runs survive a server restart and fix the in-memory queue case, where in-flight runs were stuck.

## Scope

### In Scope

- `RunWorker.recover_unfinished` (called from the app lifespan), `RunService.recovery_job` / `interrupted`,
  `WorkflowTestService.test_job`, `RunRepository.list_unfinished`, config `STUDIO_RECOVER_ON_START`,
  `STUDIO_RECOVER_MAX_ATTEMPTS`, error `RUN_INTERRUPTED` (catalog, en/vi, docs/api-errors.md).
- `backend/tests/test_durable_restart.py`: real process restarts (Human-node pause then resume; running run continues
  without repeating the finished node; repeated interruption ends with `RUN_INTERRUPTED`).
- Handbook (en, vi): deploy "Runs across restarts", configuration, comparison pages' durable-runs cells. CHANGELOG.

### Out Of Scope

- Persistent LangGraph checkpointer; in-memory delayed jobs and webhook deliveries (DEC-0062).

## Dependencies

- None: based on develop at bb70e04 (independent of TASK-0114; both add CHANGELOG lines at the top of Unreleased).

## Activity Log

- 2026-10-25: findings recorded in DEC-0062 (Human-node pauses already durable; in-memory queue runs stuck after a
  restart, confirmed by the new test with recovery turned off); fix, tests, docs; verified (QA-0107).
- 2026-10-25: PR #143 merged into develop (e348e58, with #146) with the owner's approval; moved to done by TASK-0120.

## Handoff Notes

- Review REV-0107, QA-0107.
