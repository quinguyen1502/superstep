# Task

## Metadata

- Project: superstep
- Task ID: TASK-0206
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073, DEC-0009

## Objective

Fix review finding 5 of the external review of v0.10.0 and v0.10.1: after a hand-off, the next chat message jumped from Start to the agent that answered last and skipped any node between Start and the first agent.

## Scope

### In Scope

- start router only when Start leads straight to Agent nodes (engine, chat session, Python, LangGraph and TypeScript exports)
- DEC-0073 amendment
- docs en/vi

### Out Of Scope

- The other findings of the v0.10.0/v0.10.1 review; each group has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Nodes between Start and the first agent run on every message
- A chat whose Start leads straight to the entry agent still continues with the agent that answered last
- The exports mirror the engine

## Validation

- A regression test for each finding that fails before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the external review of v0.10.0 and v0.10.1.
- 2026-10-31: implemented on `factory/task-0206-handoff-pre-agent-nodes` from `develop`. The start router that lets a chat continue with the agent that answered last exists only when every edge from Start goes straight into an Agent node (handoffs.continues, ExportWriter.start_receivers); otherwise every message runs from Start, so nodes before the first agent always run. DEC-0073 decision 4 amended. `factory verify run --profile full` passed. The owner asked to fix the confirmed review findings and merge each task when CI is green. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0194-task-0206.md`. QA: `.factory-state/artifacts/QA-0194-task-0206.md`.
