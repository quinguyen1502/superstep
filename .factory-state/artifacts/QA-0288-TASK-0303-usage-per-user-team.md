# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0288
- Task ID: TASK-0303
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Two users in two teams with one shared member return correct sums and the shared-member count: pass (`test_models_users_and_teams_blocks`).
- No telemetry call receives a user or team id: pass (`test_no_metric_label_is_a_user_or_team_id`, AST scan of every `labels(` call).
- Playwright: tables render for an admin and are absent for a member: pass (`e2e/usage.spec.ts`, run locally).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_run_usage.py tests/test_usage_api.py`; `npx playwright test e2e/usage.spec.ts`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
