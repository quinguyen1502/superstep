# Task

## Metadata

- Project: superstep
- Task ID: TASK-0171
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

`superstep mcp` is a local stdio MCP server. An MCP client lists and calls the named workflows through the studio's `/mcp`, using the personal access token instead of a workflow token.

## Scope

### In Scope

- DEC-0071 decision 7.
- PAT plus `X-Superstep-Workflow` on `/mcp`, in the API adapter and `WorkflowMcpService`, without an MCP import in the service.
- The stdio bridge in the CLI, standard library only.
- The integration test that imports the MCP SDK client, skipped unless `mcp` imports, and failed when `SUPERSTEP_MCP_TEST=1` and `mcp` is missing.
- `.github/workflows/cli.yml` installs `mcp>=1.12,<2` and sets `SUPERSTEP_MCP_TEST=1`.

### Out Of Scope

- Creating or storing a workflow token.
- Putting `mcp` in `pyproject.toml` dependencies or in the `cli` extra.
- Resources, prompts, sampling or elicitation.
- Enabling `mcp_enabled` from the CLI. A workflow that is off is an error.

## Inputs

- REQ-0079 group C (`mcp`) and REQ-0070.
- DEC-0071 decision 7 and DEC-0061.
- `backend/app/api/mcp_server.py`, `backend/app/services/workflow_mcp_service.py`, `backend/app/services/trigger_service.py` (`queue`, `check_rate`).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`, `.factory-state/artifacts/REQ-0070-workflows-as-mcp-tools.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`, `.factory-state/decisions/DEC-0061-workflows-as-mcp-tools.md`
- Decisions: `DEC-0068-superstep-cli.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- A process whose stdout is MCP JSON-RPC and whose stderr is human text.
- An MCP SDK client session that lists `run_<slug>`, `get_run` and `resume_run` for one opted-in workflow and completes a `tools/call` against the test server.

## Implementation Notes

- Authenticate the PAT in the API layer, then call the service with the user id and the workflow id. Do not build a fake `WorkflowToken` row.
- Rate-limit key `pat:{id}:{workflow id}` uses the existing limiter and window. A workflow token's key stays `token:{id}`.
- The bridge reads and writes Content-Length or newline-delimited JSON the MCP SDK's stdio client already speaks. Match the SDK 1.x stdio framing the test client uses (`mcp>=1.12,<2`). A unit test can feed one frame without installing `mcp`.
- Colliding tool names get `_<6 hex chars of the workflow id>`. The description still names the workflow.
- `MCP_DISABLED` is a CLI code, used when any named workflow has `mcp_enabled` false or the user cannot open it. The process exits before reading stdin.

## Constraints

- `tests/test_layers.py`: the service does not import `mcp` or FastAPI.
- The Python 3.9 SDK job must stay green without `mcp` installed.
- stdout is reserved for the protocol while the server runs. `--json` on `mcp` is rejected as usage, or ignored, so it cannot corrupt the stream. Reject it.
- No new server error code unless the existing `TRIGGER_TOKEN_INVALID` and `MCP_SERVER_DISABLED` cannot express the refusal. Prefer those two.

## Dependencies

- TASK-0167 merged into `develop`. The PAT check in `AuthService.current` is how `/mcp` recognises the bearer.
- May proceed in parallel with TASK-0168, TASK-0169 and TASK-0170. Register `mcp` from its own module.

## Acceptance Criteria

- A workflow token still sees only its own workflow. A PAT without the header is `TRIGGER_TOKEN_INVALID`. A PAT with the header for a workflow MCP has not been turned on for is `MCP_SERVER_DISABLED`. A PAT for a workflow the user cannot open is `TRIGGER_TOKEN_INVALID`.
- A PAT with the header for an enabled workflow lists the same three tools as that workflow's token, and `tools/call` on the run tool starts a run owned by the user.
- Two workflows in one `superstep mcp` process produce both run tools. If the slugs match, the second name ends with the id suffix.
- The integration test, with `SUPERSTEP_MCP_TEST=1` and `mcp` installed, starts the CLI, initializes a client session, lists the tool and calls it. Without the package and without the variable, that test skips. With the variable and without the package, it fails.
- `mcp --help` has an example and says the process speaks MCP on stdio. `mcp --json` exits 2.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py` plus the MCP auth tests.
- `cd sdk/python && python -m pytest -q` on 3.12 with `mcp>=1.12,<2` installed and `SUPERSTEP_MCP_TEST=1`.
- The same pytest on 3.9 without `mcp`, and the skipped test is reported skipped, not failed.

## Assumptions

- The designer step is skipped. Claude Desktop's config is a handbook snippet in TASK-0172, not a new UI.
- The test server is the backend TestClient or an in-process ASGI app the bridge can be pointed at with `--url`. The bridge accepts `--url` only as an override of the stored URL; it still requires a token.
- Framing follows the MCP Python SDK 1.x stdio client, not SDK 2.x.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071). Not started.
- 2026-10-30: implementation started. PAT plus `X-Superstep-Workflow` on `/mcp`, and the stdio bridge.

- 2026-10-30: owner asked to finish the phase 2 chain in one pass. Review REV-0147. QA QA-0147. Task moved to done. Not merged.

## Handoff Notes

- Review REV-0147. QA QA-0147. Not merged. `mcp` stays out of the package.
