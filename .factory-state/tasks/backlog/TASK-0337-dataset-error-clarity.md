# Task

## Metadata

- Project: superstep
- Task ID: TASK-0337
- Title: Return Dataset errors that name the real cause
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P1
- Size: S

## Objective

Team membership, workflow sharing, filter mapping, and token scope failures each return a specific code and message.

## Scope

### In Scope

- `DATASET_TEAM_FORBIDDEN` (403) for creating a dataset in a team the caller is not a member of.
- `DATASET_WORKFLOW_NOT_SHARED` when granting a team dataset to a workflow that is not shared with that team, naming the team.
- Dataset node filter errors name the node, the filter position, and the field (`DATASET_FILTER_INVALID` with details); an empty mapped value says which state key was empty.
- `DATASET_TOKEN_SCOPE` (403) for a token valid for this dataset that lacks the operation; wrong, revoked, or other-dataset tokens keep `401 AUTH_TOKEN_INVALID`.
- `core/errors.py` `CATALOG`, `docs/api-errors.md`, en/vi `errors.<CODE>`.

### Out Of Scope

- Standalone export error mapping (TASK-0343).

## Inputs

- `dataset_service.py` `prepare_create`; `dataset_access.py` `_in_scope`, `token_dataset`; `dataset_rows.py` filter parsing; engine Dataset node.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- Branch from `develop`. If TASK-0329/TASK-0330 are still open, coordinate: their connected-client tests assert `AUTH_TOKEN_INVALID` for an insufficient token; TASK-0343 updates the exported clients.

## Acceptance Criteria

- Each scenario from the review returns its new code and an en/vi message.
- A failed run trace names the Dataset node and filter.
- A wrong token cannot distinguish an existing dataset from a missing one.

## Tests

- API envelope tests for every new code; access tests; engine test for the filter message.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- Confirm that the insufficient-token case may move from 401 to 403 (supersedes one REQ-0099 rule).

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0337-dataset-error-clarity` from `develop` when implementation begins.
