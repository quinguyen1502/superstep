# Task

## Metadata

- Project: superstep
- Task ID: TASK-0104
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0061
- Design IDs: none
- Architecture IDs: none
- Pull request: [#122](https://github.com/quinguyen1502/superstep/pull/122) `feat/demo-mode`
- Merge commit: `ebc5426f071341df1dca9375373968707418ecc5` (2026-10-24)

## Objective

Public demo mode and live demo on Render.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Visitor:** one shared account `demo@superstep.dev` (global role viewer, public password), offered as **Try the demo** on the sign-in page. Existing RBAC keeps it away from credentials, KBs, tokens, MCP, admin. A demo guard (api/demo.py, policy in services/demo_service.py) refuses all its writes except sign in/out, cancel run, answer Human, mark notifications read → `403 DEMO_READ_ONLY`. Sign-up and password reset are closed for everyone.
- **Edit locally + run:** the editor is editable for the visitor but Save is off; run_service accepts unsaved edits in demo mode.
- **No outbound calls:** Code nodes off server-side (`DEMO_CODE_DISABLED`, UI explains in en/vi), HTTP Tool and Send email refused (`DEMO_NODE_DISABLED`), LLM/Decision always on the offline mock.
- **Rate limit:** `STUDIO_DEMO_RUN_RATE_LIMIT` runs per client IP/min (default 20).
- **Samples seeded every boot:** example, Chatbot (chat-style), Router, Approval flow, shared read-only with the visitor.
- **Banner** on every page (dismissible per session): demo, data resets, first load ~30 s.
- Live demo link in README / README.vi (inside the Deploy section from #119, not touching #117's areas) and handbook start page (en + vi).

## Changed files

- 38 files: `README.md`, `README.vi.md`, `backend/app/api/demo.py`, `backend/app/api/deps.py`, `backend/app/api/error_handlers.py`, `backend/app/api/routes/runs_ws.py`, `backend/app/core/config.py`, `backend/app/core/errors.py`, `backend/app/engine/code_runtime.py`, `backend/app/engine/nodes.py`, `backend/app/engine/validator.py`, `backend/app/main.py`, `backend/app/services/auth_service.py`, `backend/app/services/code_service.py`, `backend/app/services/demo_service.py`, `backend/app/services/run_service.py`, `backend/app/services/seed.py`, `backend/app/services/workflow_service.py`, `backend/tests/test_demo_mode.py`, `docs/api-errors.md`, `docs/deploy/demo.md`, `docs/deploy/demo.vi.md`, `docs/deploy/env-vars.md`, `docs/deploy/env-vars.vi.md`, `frontend/src/App.tsx` and more.

## Activity Log

- 2026-10-24: merged into develop (ebc5426).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0096, QA QA-0096 (retroactive records).
