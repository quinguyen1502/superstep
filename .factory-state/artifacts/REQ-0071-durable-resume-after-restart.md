# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0071
- Status: In review (TASK-0115)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Source: owner request in chat, 2026-10-25 (feature 2: durable resume after restart).

## Summary

- Verify that runs paused at a Human node, and runs in flight, survive a server restart and can be resumed from
  their checkpoint; prove it with tests that restart the process, fix what does not, and document the behaviour.

## Acceptance Criteria

- Tests restart a real server process between pause and resume (Human node), and in the middle of a running run.
- Gaps fixed: unfinished runs are resumed after a restart, or end with a clear error code.
- Handbook en+vi documents what survives a restart per run kind and queue; the comparison pages' durable-runs cells
  for Superstep are accurate. CHANGELOG Unreleased.

## Out Of Scope

- A persistent LangGraph checkpointer for the engine (Superstep stores its own checkpoints, DEC-0062); webhook
  deliveries and delayed jobs held only in the in-memory queue.
