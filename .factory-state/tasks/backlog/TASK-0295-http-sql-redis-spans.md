# Task

## Metadata

- Project: superstep
- Task ID: TASK-0295
- Title: HTTP, SQL and Redis spans
- Status: backlog
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

Show where time goes inside a request or run: HTTP handling, SQL queries and Redis calls as spans next to the existing run and node traces.

## Owner-Facing Outcome

In Jaeger (Compose `tracing` or `observability` profile), a slow request or run shows its database and Redis calls as child spans, so the operator can tell a slow query from a slow model.

## Scope

### In Scope

- Opt-in instrumentation behind one flag (for example `STUDIO_OTEL_INSTRUMENT=1`, effective only when an OTLP traces endpoint is set): OpenTelemetry FastAPI (or ASGI), SQLAlchemy and Redis instrumentation packages, imported lazily like today's SDK.
- HTTP server spans named by route template; probe routes (`/api/health`, `/api/ready`) excluded.
- SQL spans without bound parameter values; Redis spans without values (command name and key prefix only).
- Spans started while a run executes in the worker become children of the run's current node span where the context is available; HTTP requests that start a run add a span link to the run trace.
- Dependency pins in the backend requirements with license notes; `.env.example` and the configuration reference (en and vi).

### Out Of Scope

- New metrics (HTTP metrics already exist from the MVP).
- Changing LangSmith export (LangSmith keeps receiving only run and node spans).

## Dependencies

- None. Coordinates with TASK-0294 only on the shared request context; either can merge first.

## Acceptance Criteria

- With the flag off, no instrumentation package is imported and run traces are unchanged (test).
- With the flag on against an in-memory exporter, an API request yields an HTTP span with SQL child spans, and a run yields SQL and Redis spans under its trace.
- No span attribute contains a SQL parameter value, a Redis value, a prompt or a secret (test).
- Probe routes create no spans; LangSmith export filters out the new span kinds.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- Should HTTP spans be sampled (for example 10 percent) by default when the flag is on? Recommended: parent-based, always on, documented as an operator choice.

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.

## Handoff Notes

- Use branch `factory/task-0295-http-sql-redis-spans` from `develop` when implementation begins.
