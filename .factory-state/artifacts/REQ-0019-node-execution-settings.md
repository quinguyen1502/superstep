# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0019
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request 2026-10-18 ("do those 3 items"), after a gap check against the LangGraph Graph API

## Summary

Each working node can set retry, a wait between tries, a timeout, and a cache TTL. Blank means off.

## Problem Or Opportunity

LangGraph `add_node` already has retry and cache policies, and a run can cap one node attempt. The canvas config panel only stored the node's own business fields (prompt, tool, and so on).

## Scope

### In Scope

- An Execution section on LLM, Retriever, Tool, MCP, and Human nodes
- Retry attempts (1–10) and wait between tries (seconds, up to 120). Wait defaults to 0.5 when attempts are set and wait is blank
- Timeout in seconds (up to 3600) that stops that attempt
- Cache TTL in seconds (1–86400) for a repeated call with the same input inside one run
- en and vi labels
- Validation errors when a value is present but out of range
- A Human pause is not counted as a failed attempt

### Out Of Scope

- Start, End, Condition, Join, Subgraph, and imported code nodes
- `error_handler`, `defer`, per-node `input_schema`, `Command`, and `Send`
- Cache that survives across runs
- Cancelling the underlying blocking call. The attempt stops; an HTTP or LLM call already in flight may still finish in the background

## Stakeholders Or Users

- Workflow authors using the editor

## Current Context

- Compiler: `backend/app/engine/compiler.py` calls `add_node` with the node function only
- Config panel: `frontend/src/pages/Editor.tsx`
- Installed LangGraph is 1.2.16. `timeout=` on `add_node` is rejected for sync nodes. Studio node bodies are sync

## Desired Behavior

- Empty Execution fields leave the node as it is today
- A set retry becomes a `RetryPolicy` on `add_node`. The wait is the value entered, without extra jitter or a growing backoff
- A set cache TTL becomes a `CachePolicy`. The cache lives only for that compiled run
- A set timeout stops the attempt after that many seconds and raises `NodeTimeoutError`, so a retry policy can run the attempt again

## Business Rules

- Attempts must be an integer from 1 to 10
- Wait, when set, must be greater than 0 and at most 120 seconds
- Timeout, when set, must be greater than 0 and at most 3600 seconds
- Cache TTL, when set, must be an integer from 1 to 86400

## Constraints

- shadcn/ui and theme tokens, strings in `en.json` and `vi.json`
- Engine stays free of FastAPI. The compiler and validator own the rules
- Do not change run-level `STUDIO_RUN_TIMEOUT`

## Acceptance Criteria

- The Execution section is on LLM, Retriever, Tool, MCP, and Human, and absent on Start
- Values survive selecting another node and coming back, and are stored on the node
- A node that fails with a connection error runs again up to the configured attempts and can then succeed
- The same node input inside one compiled run is not executed twice when a cache TTL is set
- A node that sleeps longer than its timeout fails the attempt in about the timeout, and a retry starts another attempt
- A Human node with retry still pauses immediately

## Edge Cases

- `true` is not a number. A bool in any of these fields is invalid
- Retry with attempts and no wait uses 0.5 seconds
- Timeout plus retry: each attempt gets its own cap

## Assumptions

- The owner accepted this scope by asking for these three settings on 2026-10-18
- UX direction is the existing config panel. No separate design artifact
- One task is enough (small-task workflow)

## Open Questions

- None

## Related Artifacts

- `.factory-state/artifacts/ARCH-0001-current-architecture.md`
- `.factory-state/tasks/done/TASK-0031-node-execution-settings.md`
- `.factory-state/artifacts/REV-0030-task-0031.md`
- `.factory-state/artifacts/QA-0030-task-0031.md`
