# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0247
- Task ID: TASK-0264
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Primary then fallback, at most two calls, failover only on unreachable/5xx/404 — pass, executed in Python and Deno (`test_*_fallback_rules`, 7 cases each: ok, 503, 404 with LLM_FALLBACK_PROVIDER, connection error, 401, 400, double 500).
- Offline mode never fails over — pass (`test_offline_mode_never_fails_over`).
- No credential ids in exported code — pass (asserted in both runners and `test_model_fallback.py`).

## Checks Performed

- Export pytest suites with Deno; full `factory verify run`; handbook strict build.

## Gaps Or Untested Areas

- Real provider SDK error objects were not exercised (no paid calls); the fake mirrors their `status_code`/`status` fields.

## QA Decision

Pass.
