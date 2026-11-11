# Task

## Metadata

- Project: superstep
- Task ID: TASK-0294
- Title: Structured JSON logs with request, run and trace ids
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-11
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Let operators correlate a log line with the HTTP request, the run and the trace that produced it.

## Owner-Facing Outcome

With `STUDIO_LOG_FORMAT=json`, API and worker logs (including uvicorn access lines) are one JSON object per line with `request_id`, `run_id` and `trace_id` when known, so a log search for a run id or trace id finds every related line. The default text format is unchanged.

## Scope

### In Scope

- `STUDIO_LOG_FORMAT` (`text` default, `json`) and `STUDIO_LOG_LEVEL` if not already present; one formatter in `core/logging.py` used by the API, the worker and uvicorn loggers.
- Request context: an ASGI middleware takes `X-Request-ID` when it is a safe short token, otherwise generates one, stores it in a context variable and echoes it in the response header.
- Run context: the worker and engine set `run_id` (and `workflow_id`) in a context variable for the duration of a job, including engine worker threads.
- `trace_id` and `span_id` from the current OTel span when tracing is on; empty otherwise.
- Existing redaction (`RedactTokens`) keeps working in both formats; no prompts, inputs, outputs or secrets are added to log records.
- `.env.example` and the configuration reference page (en and vi) list the new variables.

### Out Of Scope

- Log shipping (Loki, ELK) and a Compose log stack; the handbook may show an example query only.
- New HTTP, SQL or Redis spans (TASK-0295).

## Dependencies

- None (MVP observability merged). Independent of every other phase 2 task.

## Acceptance Criteria

- With JSON format, a request that starts a run produces lines carrying the same `request_id`; worker lines for that run carry its `run_id`; with tracing on, `trace_id` matches the run's `runs.trace_id`.
- With the default text format, log output is byte-compatible with today apart from optional ids.
- `X-Request-ID` is echoed; an oversized or unsafe incoming value is replaced, never logged raw.
- A test proves WebSocket `token=` values stay redacted in JSON output.
- `tests/test_layers.py` passes (no FastAPI imports in services).

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.
- 2026-11-10: Started on branch factory/task-0294-json-logs (stacked on the planning branch so the acceptance and the tasks land together).
- 2026-11-10: `STUDIO_LOG_FORMAT` (`text` default, `json`) and `STUDIO_LOG_LEVEL` in `core/config.py`; `core/logging.configure` is called by the API (`create_app`) and the worker (`app.worker`). JSON: one handler on the root logger with `ContextFilter`, `RedactTokens` and `JsonFormatter` (`ts`, `level`, `logger`, `message`, `request_id`, `run_id`, `workflow_id`, `trace_id`, `span_id` when known, `exception`); uvicorn's loggers propagate to it, so access lines are JSON too.
- 2026-11-10: `api/request_context.RequestContext` (outermost middleware) keeps `X-Request-ID` when it matches `[A-Za-z0-9._:-]{1,64}`, otherwise makes a new id, and echoes it in the response. `RunService.execute` sets the run context; the trace id is bound once the root span is open; the engine thread starts with a copy of the context.
- 2026-11-10: Compose passes `STUDIO_LOG_FORMAT` and `STUDIO_LOG_LEVEL`; `deploy/observability/observability.env` sets `STUDIO_LOG_FORMAT=json`. `.env.example` and the configuration reference (en and vi) list both variables.
- 2026-11-10: Deviation: `STUDIO_LOG_LEVEL` did not exist and was added; in text mode it only adds a plain handler on `studio` when set, so default output stays byte-identical. `trace_id` falls back to the run's trace id when no OTel span is current (run spans are not made current unless TASK-0295 instrumentation is on).
- 2026-11-10: Review REV-0279 and QA-0279. Moved to review.
- 2026-11-11: Owner approved merging the Phase 2 stack. Moved to done on PR #355.

## Handoff Notes

- Use branch `factory/task-0294-json-logs` from `develop` when implementation begins.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0279-TASK-0294-json-logs.md`
- QA: `.factory-state/artifacts/QA-0279-TASK-0294-json-logs.md`
