# Task

## Metadata

- Project: superstep
- Task ID: TASK-0114
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0070
- Design IDs: DEC-0061
- Architecture IDs: none

## Objective

Expose opted-in workflows as MCP tools at `/mcp` (official MCP Python SDK, Streamable HTTP), authenticated with the
public API's workflow token.

## Scope

### In Scope

- Backend: `api/mcp_server.py` (SDK adapter, mounted in `main.py`), `services/workflow_mcp_service.py`,
  `TriggerService.resume` / `wait(since)`, `engine/state_schema.py` (shared with `/api/lg`), `workflows.mcp_enabled`
  (migration 0038), `GET/PUT /api/workflows/{wid}/mcp`, error `MCP_SERVER_DISABLED`, `mcp` dependency.
- Frontend: MCP tab in the API dialog (`mcp-server-tab.tsx`), en+vi strings, `/mcp` in the Vite proxy and nginx.
- Tests: `backend/tests/test_mcp_server.py` (MCP SDK client against uvicorn), `frontend/e2e/mcp-server.spec.ts`.
- Docs: handbook `run/mcp-server.md` (en, vi), run index, MCP guide, public API, API reference, comparison page API
  cell, `docs/api-errors.md`, CHANGELOG.
- Merged TASK-0113 (#141) moved to `done`.

### Out Of Scope

- Multi-workflow servers, progress streaming (DEC-0061).

## Dependencies

- None: based on develop at bb70e04.

## Activity Log

- 2026-10-25: implemented, tests and e2e pass, screenshots reviewed (en, vi); verified with `factory deps apply` and
  `factory verify run --profile full` (QA-0106).
- 2026-10-25: PR #142 merged into develop (a6aba88) with the owner's approval; moved to done.

## Handoff Notes

- Review REV-0106, QA-0106.
