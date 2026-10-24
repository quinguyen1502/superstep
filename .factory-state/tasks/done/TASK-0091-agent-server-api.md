# Task

## Metadata

- Project: superstep
- Task ID: TASK-0091
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0054
- Design IDs: none
- Architecture IDs: DEC-0059

## Objective

LangGraph Agent Server API subset at /api/lg.

## Scope

### In Scope

- backend/app/models/agent_thread.py, migration 0036, repositories/agent_threads.py, services/agent_server_service.py, services/trigger_service.py, routes/agent_server.py, schemas/agent_server.py, core/errors.py; tests/test_agent_server_api.py; scripts/agent_server_smoke.py; docs/agent-server-api.md, docs/backend-architecture.md, handbook run/agent-server-api.md (en+vi); CHANGELOG.

### Out Of Scope

- Stream modes other than values/updates; crons, store, multiple concurrent runs per thread.
- LangSmith Studio and Agent Chat UI compatibility (needs CORS, more endpoints, a messages list).

## Dependencies

- None: based on develop. TASK-0087 (#132) is stacked on this branch (migration 0037 follows 0036).

## Activity Log

- Branch `feat/agent-server-api` (PR #129) predates the owner's switch to the factory workflow on 2026-10-24; it keeps its name, and these artifacts were added as a normal commit on it.
- 2026-10-24: implemented, verified with `factory deps apply` and `factory verify run --profile full` plus e2e and handbook builds (QA-0084); PR into develop.
- 2026-10-24: PR #129 merged into develop (436aa59); moved to done by TASK-0110.

## Handoff Notes

- Review REV-0084, QA-0084.
