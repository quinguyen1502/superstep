# Task

## Metadata

- Project: superstep
- Task ID: TASK-0107
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0063
- Design IDs: none
- Architecture IDs: none
- Pull request: [#126](https://github.com/quinguyen1502/superstep/pull/126) `fix/demo-locale-visitor`
- Merge commit: `74ab1f85774645e994fa3ec9b632fc13047d8fc4` (2026-10-24)

## Objective

Demo: locale-aware mock replies and per-visitor history.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- `engine/locale.py`: `pick()` returns `en` (default) or `vi` from an explicit value or an `Accept-Language` header.
- `Ports.locale` carries the run's language; `mock_llm(prompt, model, locale)` answers `Answer:` / `Trả lời:`; the example `lookup_order` tool opts in by declaring a `locale` parameter (same opt-in pattern as `idempotency_key` in `call_tool`).
- `/ws/run` sets the locale from the request's `locale` field, else `Accept-Language`. The studio sends `locale: uiLocale()` with editor runs and Chat panel messages and answers.
- Exported Python/TS code's mock now answers in English, matching the engine's default.
- Regenerated `handbook/docs/{en,vi}/images/overview.png` (README hero) plus the chat-tab, chat-visitor and chat-fullscreen shots. The English shots now show English replies.
- In demo mode, signing in with `demo@superstep.dev` now issues a session for a fresh anonymous visitor account (`demo-v-<random>`, viewer, no password) that gets the template account's sample shares. Run history, chats, waiting runs and notifications were already scoped per user, so they are now per visitor. Samples stay shared and read-only, and `refuses()` covers every visitor account.
- Cleanup: visitors older than `STUDIO_DEMO_VISITOR_TTL` (default 86400 s) are removed with their runs, chats, notifications and shares at every boot and every demo sign-in.
- No migration is needed because there is no new column. Without `STUDIO_DEMO_MODE`, login behaves as before (unit-tested).
- Backend: `tests/test_demo_visitors.py` (8 new tests). Full suite: 679 passed, 14 skipped, 1 failed. The failure is `test_code_subprocess.py::test_timeout_kills_the_whole_process_group`, which also fails on clean `develop` on the dev box: RLIMIT_NPROC versus the many threads already running there makes fork return EAGAIN.
- Frontend: vitest 98/98, `lint:ui` clean, tsc clean.

## Changed files

- 35 files: `CHANGELOG.md`, `backend/app/api/deps.py`, `backend/app/api/routes/runs_ws.py`, `backend/app/core/config.py`, `backend/app/engine/effects.py`, `backend/app/engine/llm.py`, `backend/app/engine/locale.py`, `backend/app/engine/nodes.py`, `backend/app/engine/ports.py`, `backend/app/engine/python_export.py`, `backend/app/engine/tools.py`, `backend/app/engine/typescript_export.py`, `backend/app/repositories/chat_sessions.py`, `backend/app/repositories/users.py`, `backend/app/services/auth_service.py`, `backend/app/services/demo_service.py`, `backend/tests/test_demo_visitors.py`, `docs/deploy/demo.md`, `docs/deploy/demo.vi.md`, `docs/deploy/env-vars.md`, `docs/deploy/env-vars.vi.md`, `frontend/e2e/mock-locale.spec.ts`, `frontend/src/components/chat/use-chat-run.ts`, `frontend/src/components/editor/use-studio.ts`, `frontend/src/lib/i18n.ts` and more.

## Activity Log

- 2026-10-24: merged into develop (74ab1f8).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0099, QA QA-0099 (retroactive records).
