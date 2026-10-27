# Task

## Metadata

- Project: superstep
- Task ID: TASK-0158
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0076
- Design IDs: none
- Architecture IDs: DEC-0069, DEC-0066, DEC-0063, DEC-0018

## Objective

A wave that pauses for an approval or a child run lets the other calls finish, and the parent resumes once, after every wait in the wave is resolved. A restart does not repeat a finished call.

## Scope

### In Scope

- Checkpoint `waits`: one entry per open approval slot and per child run of the wave. A wave with exactly one child and no approval may keep today's `checkpoint.wait`.
- `RunService.resume_parent`: enqueue one resume only when every child of the wave has settled and no approval of the wave is open. Store child results until that moment. A duplicate settle does not enqueue twice. A child that settles before the parent has recorded the wait is picked up when the parent records it, as today.
- `ApprovalRepository.add_wait`: do not close an open wait of a different node on the same run. Closing the same node on a new pause still supersedes that node's own wait.
- Answering one approval, in the studio or by its deadline (`on_timeout`), resolves only that slot. If other waits remain, the run stays waiting and the answer is kept for the one resume.
- Cancel of the parent cancels every running or waiting child of the wave. A late child does not resume a parent that is no longer waiting.
- Tests in `backend/tests/`: one approval in a round of two calls, the other call finishes, answering completes the round; two workflow tools start two children together and the parent resumes once; one child cancelled, the round continues; the run cancelled, both children cancelled; a deadline fires on one approval while the other call is still running; a restart in the middle of the wave repeats no finished call (ledger). Existing single-approval agent tests still pass.

### Out Of Scope

- The editor and the trace bars (TASK-0159).
- Exports (TASK-0160).
- A new approval that lists every call of the round. CLAR-0007 chose one approval per call.
- Changing `STUDIO_WAIT_TTL` for the whole run.

## Inputs

- TASK-0157's slots, join and ledger keys.
- DEC-0069 decision 7. DEC-0066 decisions 3 to 5 and 7.
- `backend/app/services/run_service.py` (`resume_parent`, `cancel_children`, `plan_resume`), `backend/app/services/approval_service.py` (`on_waiting`, `_timeout`), `backend/app/repositories/approvals.py` (`add_wait`).
- `backend/tests/test_agent_approval.py`, `backend/tests/test_workflow_tool_runs.py`, and the restart tests of TASK-0115 and TASK-0127.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`, `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`
- Decisions: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`, `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0018-effectively-once.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`

## Expected Outputs

- Two workflow-tool calls in one round start two child runs together. The parent resumes once, after both have settled, and the model receives both results in order.
- An approval pauses only its call. The other call of the round has already finished.

## Implementation Notes

- `AwaitChild` is an `Interrupt`. The wave's `checkpoint.nodes` must be every slot, so a resume re-enters the slots that the ledger already finished.
- `add_wait` today closes every open wait of the run. That must become per node, or the second approval of a wave deletes the first.
- `_timeout` today always enqueues a resume. Enqueue only when `waits` is empty after this answer. The deadline response is the tool result for that slot, not for the round.
- No migration. `approval_waits` already allows several rows per run. Child identity stays `parent_run_id` + `parent_step`.
- A finished slot on resume comes from the ledger. Assert `reused` on that `node_finished`, and assert the tool body did not run again.

## Constraints

- DEC-0009: routers stay out of this change. Services call repositories. No raw SQL.
- No new error code is expected. A new code, if one is forced, goes through `core/errors.py`, `docs/api-errors.md` and both locale files.
- One resume job per wave, not one per child.

## Dependencies

- TASK-0157 merged to `develop`.

## Acceptance Criteria

- pytest: an approval in a two-call round pauses only that call. The other call's result is recorded before the answer. Answering `approved` completes the round, and the model sees both results in order.
- Two workflow-tool calls start two child runs before either has settled. The parent resumes once, after both settle. A duplicate settle of one child does not start a second resume.
- One child ends `cancelled`. Its call is an error result, and the other call's result still reaches the model.
- Cancelling the parent cancels a running child and a waiting child of the same wave.
- The deadline of one approval answers only that call while the other call is still running. The round completes when the rest finish. The other call is not cancelled.
- A worker restart after one call of the wave has finished does not run that call again. The ledger test shows the reused result.
- A run that waits on a single approval, as in `test_agent_approval.py`, still asks once and completes on one answer.
- Full backend suite on SQLite. `tests/test_layers.py` passes.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`

## Assumptions

- The approval deadline is the node's `on_timeout`, not `STUDIO_WAIT_TTL`.
- A wave with one child and no approval keeps the existing `checkpoint.wait` shape, so current readers of a single child keep working.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0076 (DEC-0069). Medium-task workflow.

## Handoff Notes

- Do not start a branch until the owner confirms this set and TASK-0157 has merged. The next skill is `task-start`.
- TASK-0161's e2e waits on this task for two desks in one round.
