# Task

## Metadata

- Project: superstep
- Task ID: TASK-0269
- Title: Export MCP adapter
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Architecture IDs: DEC-0088
- Plan: PLAN-0009

## Objective

Replace the MCP stub (node and Agent MCP tool) in Python and TypeScript exports with a real Streamable HTTP MCP call configured by `MCP_SERVER_<n>_URL` / `_HEADERS`, per DEC-0088. Split from TASK-0266.

## Acceptance Criteria

- Configured: real initialize + tools/call + session close against a local MCP server, headers sent, JSON and event-stream replies, tool errors stop the run (Python and Deno).
- Unconfigured: offline announced mock; live run refused naming the variable.
- No server id, URL or secret in the generated file.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0251-TASK-0269-export-mcp-adapter.md`
- QA: `.factory-state/artifacts/QA-0251-TASK-0269-export-mcp-adapter.md`

## Activity Log

- 2026-11-07: Created (split from TASK-0266) and implemented.
