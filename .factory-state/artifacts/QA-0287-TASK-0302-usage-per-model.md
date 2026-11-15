# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0287
- Task ID: TASK-0302
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Two models return two rows with correct sums; 403 without `users.manage`: pass (`test_models_users_and_teams_blocks`, `test_usage_api_needs_users_manage`).
- Playwright: Models table renders and sorts; empty state on a fresh database: pass (`e2e/usage.spec.ts`, run locally).
- en/vi locale parity: pass (`locales.test.ts`); shadcn components and UI class check.

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_run_usage.py tests/test_usage_api.py`; `npx vitest run src/lib/__tests__/usage.test.ts src/lib/__tests__/locales.test.ts`; `npx playwright test e2e/usage.spec.ts` (passed locally; the dev server was started with `vite` directly because the local `predev` SDK build fails with the workspace TypeScript 6).
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
