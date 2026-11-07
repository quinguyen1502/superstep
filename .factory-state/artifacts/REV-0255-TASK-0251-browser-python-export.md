# Review

## Metadata

- Project: superstep
- Review ID: REV-0255
- Renumbered: REV-0242 → REV-0255 on 2026-11-07 (TASK-0272). PR #320 merged first and keeps REV-0242 for TASK-0259.
- Task ID: TASK-0251
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

Uncommitted branch `factory/task-0251-browser-python-export` against `origin/develop`
at `e26e39e9`. No product commit existed at review time. The reviewed tree is the
working tree that the following one-commit squash will contain.

Files:

- `backend/app/engine/browser_export.py` (new standalone helper and public policy)
- `backend/tests/test_browser_python_export.py` (new executable export tests)
- `backend/app/engine/export_common.py`
- `backend/app/engine/python_export.py`
- `backend/app/engine/typescript_export.py`
- `backend/app/engine/project_export.py`
- `backend/app/services/mcp_service.py`
- `handbook/docs/en/guide/browser.md`
- `handbook/docs/vi/guide/browser.md`
- `roadmap.md`
- `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- `.factory-state/tasks/doing/TASK-0251-browser-python-export.md` (moves to done with this delivery)
- `.factory-state/tasks/done/TASK-0250-browser-agent-recipe-trace-ui.md` (lifecycle only; PR #315 already merged)

No schema migration, UI component, locale catalog, or secret value was added.

## Reference Artifacts

- TASK-0251 acceptance criteria
- REQ-0086 AC8 (Python half; TypeScript remains TASK-0252)
- DES-0004, ARCH-0002, DEC-0085, PLAN-0006
- `docs/backend-architecture.md` (service may call engine; engine does not import FastAPI)
- Prior studio delivery on develop, including TASK-0250 REV-0240 / QA-0240

## Findings

### Blocking

- None.

### Non-Blocking

- The memory driver fetches a whitelisted origin with the stdlib, including a loopback origin, so a local fixture can run. Playwright and Browserless refuse non-global addresses before launch. That is wider than the studio always-on private-IP block, and it is the fixture path the tests use.
- A real Chromium launch and a live Browserless session are not executed. Missing Playwright, a missing token, and a private address fail closed before launch.
- TypeScript still refuses browser steps with an explicit error. That is the TASK-0251 boundary. TASK-0252 replaces the refusal. The existing TypeScript snapshot stays stable because the throw is gated on `_browser_export`.
- When an Agent export runs more than one tool call at once, `interrupt()` can be raised on a worker thread. Same-connection browser commands still take the session lock. A single-call approval pause stays on the calling thread.

## Standards And Architecture Alignment

- `check_export` lives on the MCP service and calls `public_policy` in the engine. The embedded runtime imports nothing from `app`.
- Annotations `_browser_export` and `_managed_export` are stripped before save. Tests read the stored workflow and assert both keys are absent.
- Invalid browser settings stay a managed placeholder. Other managed adapters are unchanged.
- Secret fields are not part of `BrowserSettings`. `.env.example` lists names with empty values. Fixture token, proxy password, and profile cookie text are asserted absent from generated source.
- No new API error code, envelope, or Alembic migration.
- Upload and download raise an explicit capability refusal outside Studio. Evaluate allows only `document.title` and `document.body.innerText`, and only when the connection allows it.

## Design Alignment

No new screen. The handbook adds a short Python export section in English and Vietnamese. It names the memory, Playwright, and Browserless drivers, empty environment values, the six default tools, the upload/download refusal, interrupt, and the TypeScript refusal. `scripts/check-browser-handbook.py` passed.

## Validation Review

Declared tool-policy commands were run from `/tmp/superstep-wt-0251` with arm64 Node (`process.arch` arm64), not through the x86_64 backend virtualenv:

- `backend`: `.venv/bin/python -m pytest` — 1427 passed, 71 skipped, 522.03s, exit 0
- repo root `npm run build`, `npm run lint`, `npm run test` — exit 0 (lint warnings only, pre-existing)
- `sdk/python`: `.venv/bin/python -m pytest` — 229 passed, 8 skipped, 13.77s
- `sdk/typescript`: `npm run build`, `npm run test` (102 passed), `npm run typecheck` — exit 0
- `scripts/check-browser-handbook.py` — passed
- `git diff --check` on the tracked product diff — passed

`factory validate` was not used as a gate. On clean develop it already fails because TASK-0253 lacks the capital strings the done-task check wants. CI runs `factory verify`, which does not call `factory validate`.

## Assumptions

- The owner authorised implementation through a Ready pull request and did not authorise merge.
- TASK-0250's move to done belongs on this branch because PR #315 is already merged. No separate pull request is opened for that move.
- TASK-0252 is an owner-authorised stack and is outside this review.

## Required Follow-Up

- TASK-0252 replaces the TypeScript refusal with an executable helper and the same fixture contract.
- Merge waits for the owner. REQ-0086 stays open until both exports merge.

## Review Decision

Approved for QA. No blocking findings.
