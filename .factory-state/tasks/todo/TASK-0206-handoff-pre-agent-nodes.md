# Task

## Metadata

- Project: superstep
- Task ID: TASK-0206
- Status: todo
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
