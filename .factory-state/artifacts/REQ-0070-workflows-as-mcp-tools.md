# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0070
- Status: Done (TASK-0114, PR #142)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Source: owner request in chat, 2026-10-25 (feature 1: expose workflows as an MCP server).

## Summary

- Opted-in workflows become MCP tools that other clients (Claude Desktop, Cursor, agents) call over the official MCP
  Python SDK's Streamable HTTP transport, mounted in the FastAPI app at `/mcp`.

## Acceptance Criteria

- Auth reuses the public API workflow token (`X-Workflow-Token` or `Authorization: Bearer`); runs go through the
  existing trigger/run services (history source `api`, rate limit, input checks).
- The tool's input schema derives from the workflow's state fields; a call runs the workflow and returns its output.
  A run paused at a Human node returns `run_id` + `status: waiting` + prompt; `get_run` and `resume_run` tools exist.
- Opt-in per workflow (off by default), set in the editor's API dialog, which also copies a client config snippet
  (en, vi). Demo mode restrictions hold.
- Handbook page en+vi, public API docs updated; backend tests and an integration test with the MCP client; Playwright
  e2e; CHANGELOG Unreleased.

## Out Of Scope

- One endpoint exposing several workflows to one client (tokens are per workflow); SSE streaming of node progress.
