# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0054
- Status: Done (TASK-0091, PR #129)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner request in chat, 2026-10-24 (item 2 of 5). Branch `feat/agent-server-api` (PR #129) predates the switch to the factory workflow; artifacts added afterwards on the same branch.

## Summary

- A subset of the LangGraph Agent Server API at `/api/lg` so the official `langgraph-sdk` clients and `RemoteGraph` can run Superstep workflows.

## Acceptance Criteria

- Assistants (one per workflow: search, get, graph, schemas), threads (create, get, search, delete, state, history), runs (create, wait, stream values/updates, get, list, join, cancel, also stateless).
- Human nodes surface as interrupts; `Command(resume=...)` continues the same run.
- Auth: workflow token or user JWT (`x-api-key`, `X-Workflow-Token`, `Authorization: Bearer`).
- Tables `agent_threads`, `agent_thread_runs` (migration 0036); error codes THREAD_NOT_FOUND, THREAD_EXISTS, THREAD_BUSY, THREAD_WORKFLOW_MISMATCH in catalog, docs and locales.
- Verified with langgraph-sdk in tests and a live smoke script; handbook en+vi; CHANGELOG.

## Out Of Scope

- Stream modes other than values/updates; crons, store, multiple concurrent runs per thread.
- LangSmith Studio and Agent Chat UI compatibility (needs CORS, more endpoints, a messages list).
