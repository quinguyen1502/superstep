# Task

## Metadata

- Project: superstep
- Task ID: TASK-0299
- Title: Channel, MCP, browser and sandbox activity counters
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Make the integrations that most often fail visible in Grafana.

## Owner-Facing Outcome

Grafana shows channel messages in and out with failures by platform, MCP tool calls and errors, browser sessions and actions, and sandbox (Code node) executions with duration and failures, each with an error-rate alert.

## Scope

### In Scope

- `studio.channel.messages` (labels `kind` = channel platform, `direction` in/out, `status`): approval requests sent, callbacks received, chat trigger messages; from `services/approval_channels`, `channel_service`, `chat_trigger_service`.
- `studio.mcp.calls` and `studio.mcp.duration` (labels `transport`, `status`, `code`); never the MCP server name or URL.
- `studio.browser.sessions` (opened, closed, failed) and `studio.browser.actions` (`status`, `code`); `studio.browser.active` gauge where the gateway knows it.
- `studio.sandbox.executions` and `studio.sandbox.duration` (labels `runtime` docker/subprocess/deno, `language`, `status`).
- New label names (`kind`, `transport`, `runtime`, `language`) added to `LABELS` as fixed enums; Metric labels stay in the bounded `LABELS` set in `services/telemetry.py`; any new label is a fixed enum added there with a test. Never `user_id`, `run_id`, a raw URL, a server or connection name, a prompt or a secret.
- New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Per-connection or per-server breakdowns (cardinality).
- Channel refusal codes on the Usage page (TASK-0304).

## Dependencies

- None (TASK-0285 merged).

## Acceptance Criteria

- Each counter increments in a targeted test with mocked channel, MCP, browser and sandbox calls; failures carry the catalog error code.
- Label set test proves no server name, URL, user id or run id leaks.
- No measurable change to run behaviour; existing integration tests stay green.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.

## Handoff Notes

- Use branch `factory/task-0299-activity-counters` from `develop` when implementation begins.
