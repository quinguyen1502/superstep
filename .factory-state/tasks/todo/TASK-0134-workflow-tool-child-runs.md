# Task

## Metadata

- Project: superstep
- Task ID: TASK-0134
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073
- Design IDs: none
- Architecture IDs: DEC-0066, DEC-0063, DEC-0018, DEC-0023

## Objective

Run a workflow tool call as a linked child run that the parent's tool step waits for, once, across pauses, restarts
and retried jobs, and give its result back to the model (DEC-0066 decisions 3 to 5 and 7).

## Scope

### In Scope

- Migration: `runs.parent_run_id` (indexed) and `runs.parent_step`, unique together; `Run` model and
  `RunRepository` (`child_of(parent, key)`, `children(parent)`).
- Engine: `AwaitChild(step, run_id)` in `engine/errors.py`; `runtime.run_stream` hands back a checkpoint for it;
  `ports.start_child(key, workflow, version, input)`; `A/__tool` starts or finds the child, waits, and on resume turns
  `{child_run_id, status, output | error, usage}` into the tool result, adding usage and cost to the Agent node.
- `RunService`: record the parent `waiting` with `wait = {kind: "child", run_id}` and no approval or notification;
  `start_child` enqueues a `tool` source job with the parent's owner and resource owner, `test` and `mock_models`
  inherited; `settled()` of a run with a parent queues the parent's resume with `enqueue_resume`; a resume for a
  parent no longer waiting for that child is dropped.
- Cancel cascade to running and waiting children; the run-time depth check (`WORKFLOW_TOOL_TOO_DEEP` in
  `core/errors.py`, `docs/api-errors.md`, en and vi).
- `backend/tests/test_workflow_tool_runs.py`: a call with the mock and with a respx-mocked provider; a failed child;
  the same tool twice in one run; inside a For each loop; cancel; restart tests as in TASK-0115 and TASK-0127 (the
  parent recovered before and after recording `waiting`, the child cut off mid-way); time travel after a call keeps
  the recorded result.

### Out Of Scope

- Approval requests naming both workflows and the runs pages (TASK-0135), the trace UI (TASK-0136).

## Inputs

- DEC-0066, TASK-0133's settings and snapshot.
- `engine/agents.py`, `engine/runtime.py`, `engine/errors.py`, `engine/ports.py`, `services/run_service.py`,
  `services/run_worker.py`, `services/job_queue.py`, `models/run.py`, `repositories/`, `migrations/versions/`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`, `REQ-0071-durable-resume-after-restart.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: `DEC-0018-effectively-once.md`, `DEC-0023-rbac-sharing.md`, `DEC-0044-workflow-test-runs.md`,
  `DEC-0063-agent-node-expansion.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- A supervisor workflow run through `/ws/run`, the API trigger and a test run calls a specialist workflow and answers
  with its result; the child is its own run with a parent.

## Implementation Notes

- The resume of a parent from a child goes through the same queue and lease as a Human-node resume, so it works with
  the in-memory and the Redis queue.
- A studio (`/ws/run`) parent waits like a Human node: the socket gets the waiting event and the resumed segment runs
  on the worker.

## Constraints

- One Alembic migration, SQLite and Postgres; layers (DEC-0009); no new dependency.
- A finished child call is never repeated; a child is started at most once per call key.

## Dependencies

- TASK-0133.

## Acceptance Criteria

- pytest: the model gets the child's output fields as the tool result; a failed child gives an error result and the
  parent goes on; usage and cost add up on the Agent node.
- Restart: a parent recovered before it recorded `waiting` finds the existing child; a child cut off mid-way recovers
  and then resumes the parent; a duplicate settle resumes the parent once.
- Cancelling the parent cancels a running and a waiting child; seven nested calls fail with `WORKFLOW_TOOL_TOO_DEEP`.
- Full backend suite on SQLite and Postgres; `test_layers.py` and `test_api_envelope.py` pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`; `factory verify run --profile full`; the CI Postgres job.

## Assumptions

- The child's timeout is the normal run timeout; a parent waiting for a child is not running (DEC-0066 decision 7).

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).

## Handoff Notes

-
