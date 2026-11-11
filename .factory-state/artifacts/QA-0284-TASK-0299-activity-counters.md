# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0284
- Task ID: TASK-0299
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-11
- Outcome: pass

## Acceptance Criteria Coverage

- Each counter increments with mocked channel, MCP, browser and sandbox calls; failures carry the catalog code: pass (`test_mcp_calls_by_transport_with_codes`, `test_sandbox_executions_by_runtime_language_and_status`, `test_browser_sessions_and_actions`, `test_channel_messages_in_and_out`).
- No server name, URL, user id or run id in labels: pass (`test_enums_match_the_product_lists`, `test_no_metric_label_is_a_user_or_team_id`).
- Run behaviour unchanged; integration tests green: pass (full backend suite, 1663 passed and 32 skipped at this commit).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_activity_metrics.py tests/test_metrics.py tests/test_layers.py`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).
- The required Image check on PR #358 failed while building the standalone sandbox service because its Dockerfile omitted `app.engine.activity`. A local import using only the Dockerfile's application files reproduced the failure and passed after adding the module to the image.

## QA Decision

Pass.
