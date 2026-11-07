# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0263
- Task ID: TASK-0277
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: pass with follow-up

## Validation Scope

TASK-0277 footer on the Studio pages listed in the task. Review is REV-0263. The health version is the server value returned by `GET /api/health`.

## Acceptance Criteria Coverage

- Criterion: Signed-out and signed-in Studio pages in scope show the copyright line in English and Vietnamese.
  - Result: pass
  - Evidence: Chrome on `http://127.0.0.1:5197`, desktop and a 390px viewport. Login showed `Superstep · Qui Nguyen · 2026`, then Vietnamese `Bản quyền Superstep · Qui Nguyen · 2026`. The workflow list, Settings, the approval inbox, and forgot-password showed the English line. Register uses `AuthPage`. Reset password uses the same `Frame` as forgot-password.
- Criterion: When `/api/health` returns a version, the line includes it. A failed call leaves the copyright and hides the version.
  - Result: pass
  - Evidence: With health data `version: 0.12.0`, the line included `Version 0.12.0` and `Phiên bản 0.12.0`. A page whose `/api/health` request was aborted showed `Superstep · Qui Nguyen · 2026` and no version.
- Criterion: The editor canvas and public chat do not gain a footer.
  - Result: pass
  - Evidence: `/workflows/abc` and `/c/demo` had `[data-testid=app-meta]` count 0. Those routes error without a full API, which still mounts the page tree that would contain the footer.
- Criterion: Locale strings differ between `en` and `vi`. No hard-coded colours.
  - Result: pass
  - Evidence: `meta.copyright` and `meta.version` differ. `npm run test` includes the locale test (177 frontend tests passed). Classes are `text-muted-foreground` and `text-xs`.

## UX And Accessibility Coverage

- Criterion: The footer does not cover the sign-in card or the workflow list, including a phone-width viewport.
  - Result: pass
  - Evidence: Screenshots of login and the workflow list at 390×844. The line sits under the card. The sign-in button text stayed `Sign in` / `Đăng nhập`.
- Criterion: The line is text in a `footer`, and the language switch updates it.
  - Result: pass
  - Evidence: `#lang-switch` then `[data-lang=vi]` changed the same footer.

## Checks Performed

- `sdk/python`: `.venv/bin/python -m pytest` with `PYTHONPATH` set to this worktree. 229 passed, 8 skipped. 15.37s.
- Root `npm run lint`. Exit 0. Warnings include a new `react(purity)` note on `new Date()` in `app-meta.tsx`.
- Root `npm run test`. Exit 0. Frontend 177 passed, React package 22 passed, TypeScript SDK 102 passed.
- Root `npm run build`. Exit 0.
- `sdk/typescript`: `npm run typecheck`, `npm run test` (102 passed), `npm run build`. All exit 0.
- Backend `.venv/bin/python -m pytest` with `PYTHONPATH` set to this worktree. 1492 passed, 112 skipped, in 608.33s. Exit 0.
- `git diff --check` at finish time.
- Commands used the worktree sources. Node was arm64 v22.12.0. `factory verify` was not launched through the x86_64 virtualenv.

## Defects

- None that fail an acceptance criterion.

## Gaps Or Untested Areas

- No Playwright spec was added. The browser check was a one-off Chrome script against a preview, not `npm run e2e`.
- `/workflows/abc` and `/c/demo` were checked for the absence of the footer while those pages were in their error state.

## Residual Risk

- A health failure stays cached until reload, so the version can stay hidden after the API recovers.
- The workflow notice can overlap the footer while it is on screen.

## Assumptions

- The preview health body used the same envelope as `EnvelopeResponse`. The displayed `0.12.0` matches `backend/pyproject.toml` on this branch.

## Required Follow-Up

- CI on the finished head. Merge only when the owner asks.

## QA Decision

conditionally passed with documented risk
