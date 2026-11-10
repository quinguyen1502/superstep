# Review

## Metadata

- Project: superstep
- Review ID: REV-0279
- Task ID: TASK-0294
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`backend/app/core/logging.py` (context variables, `ContextFilter`, `JsonFormatter`, `configure`), `backend/app/api/request_context.py`, `backend/app/main.py`, `backend/app/worker.py`, `backend/app/core/config.py` (`log_format`, `log_level`), the run context in `RunService.execute` and the engine thread, `docker-compose.yml`, `.env.example`, configuration reference (en and vi), `backend/tests/test_log_correlation.py`.

## Findings

### Blocking

- None.

### Non-Blocking

- With the default `text` format nothing new is attached: `studio.*` warnings still reach Python's last-resort handler. Setting `STUDIO_LOG_LEVEL` in text mode adds one plain `LEVEL logger: message` handler on `studio`.
- The engine thread is now started through `contextvars.copy_context()`, so it sees the run and request context; the full backend suite stays green with that change.
- WebSocket connections get a request id in the log context but there is no response header to echo it in.

## Review Decision

Approved for QA.
