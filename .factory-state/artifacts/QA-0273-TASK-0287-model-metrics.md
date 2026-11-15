# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0273
- Task ID: TASK-0287
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- A mocked 429 raises `PROVIDER_RATE_LIMITED`, triggers fallback like `PROVIDER_BAD_RESPONSE`, and is counted separately from 5xx: pass (`test_http_429_is_rate_limited_and_502_to_clients`, `test_sdk_429_maps_to_rate_limited`, `test_failure_policy_is_bounded_and_auth_is_not_hidden[PROVIDER_RATE_LIMITED-2]`, `test_llm_errors_and_fallbacks`).
- Unknown-model usage increments `studio.llm.unpriced` and not `studio.llm.cost`: pass (`test_model_usage_cost_and_unpriced`).
- No metric carries `user_id` or `run_id`: pass (`assert_bounded`).
- Existing run, export and provider tests and en/vi locale parity stay green: see the PR checks.

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_metrics.py tests/test_model_fallback.py tests/test_telemetry.py tests/test_deferred.py tests/test_readiness.py tests/test_layers.py tests/test_api_envelope.py`.
- Full backend suite and frontend locale tests (see the PR), `factory validate --only hygiene`.

## QA Decision

Pass.
