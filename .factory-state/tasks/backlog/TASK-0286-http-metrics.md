# Task

## Metadata

- Project: superstep
- Task ID: TASK-0286
- Title: HTTP request metrics by route template
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: S

## Objective

Count HTTP requests and record latency and 5xx by route template, method and status class, from a lightweight ASGI middleware on the existing meter.

## Scope

### In Scope

- Middleware in the FastAPI app: `studio.http.server.requests` counter and `studio.http.server.duration` histogram (ms), labels `route` (matched route template, `unmatched` otherwise), `method`, `status_class` (2xx..5xx).
- WebSocket connections open as an up-down counter `studio.ws.connections`.
- Exclude `/api/health` and `/api/ready` from latency buckets or label them so probes do not skew dashboards.
- Follow OTel HTTP semantic conventions where they fit; a dependency on `opentelemetry-instrumentation-fastapi` only if the owner prefers it over the middleware (record in the task log).

### Out Of Scope

- HTTP spans on run traces (phase 2); request IDs and JSON logs (phase 2).

## Dependencies

- TASK-0285 merged.

## Acceptance Criteria

- A test client request produces one counter increment and one histogram record with the route template, never the raw path or query.
- A 500 response counts under `5xx`; streaming and WebSocket routes do not break.
- No measurable overhead when metrics are off (middleware short-circuits).

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
