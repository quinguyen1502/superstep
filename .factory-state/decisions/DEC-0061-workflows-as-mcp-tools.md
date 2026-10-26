# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0061
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Related Requirements: REQ-0070
- Related Architecture: none
- Related Tasks: TASK-0114

## Decision

1. **One endpoint, scoped by the token.** The server is a single `/mcp`; the workflow token (already scoped to one
   workflow) decides which workflow the client sees. No new credential type, no per-workflow URL, and revoking the
   token cuts the client off, as for the REST API.
2. **Explicit opt-in.** A boolean `workflows.mcp_enabled` (migration 0038, default off), changed by people with the
   `share` action (who manage tokens). A token alone does not expose a workflow to agents; a disabled workflow
   answers `403 MCP_SERVER_DISABLED` before the MCP layer, as an invalid token answers `401 TRIGGER_TOKEN_INVALID`.
3. **Three tools.** `run_<slug of workflow name>` (input schema = state fields, shared with `/api/lg` via
   `engine/state_schema.py`), `get_run`, `resume_run`. A call waits up to `STUDIO_SYNC_WAIT_MAX` like a `sync` REST
   call; Human-node pauses return `status: waiting` with `run_id` and prompt instead of holding the call open, so the
   client (or its user) decides the answer. `resume_run` enqueues the existing `resume` job and waits for the run to
   settle after the paused segment (`TriggerService.resume` / `wait(since=...)`, shared logic).
4. **Official SDK, low-level server, stateless JSON.** `mcp.server.lowlevel.Server` with
   `StreamableHTTPSessionManager(stateless=True, json_response=True)`: any replica answers any request (runs live in the
   database) and no session state is kept. The SDK is used here (unlike the hand-written MCP client of TASK-0013)
   because serving has no sandboxing concerns. Tool failures are tool results with `isError` and the common error
   object, so clients see our English error codes.
5. The service (`workflow_mcp_service.py`) has no MCP import; `api/mcp_server.py` is the adapter (routes -> services ->
   repositories).

## Consequences

- A client that needs several workflows adds several servers (one token each).
- No progress streaming; long runs are polled with `get_run`.
- nginx (split images) and the Vite dev proxy forward `/mcp`.
