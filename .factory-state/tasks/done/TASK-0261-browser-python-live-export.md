# Task

## Metadata

- Project: superstep
- Task ID: TASK-0261
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002
- Plan: PLAN-0006
- Size: M

## Objective

Keep one Playwright or Browserless page per browser alias in the Python project export, and run click, fill, and evaluate on that page. The fixture driver `memory` stays the TASK-0251 contract.

## Scope

### In Scope

- Change the Python helper in `backend/app/engine/browser_export.py` so `playwright` and `browserless` keep one browser and one page per alias until idle, lifetime expiry, or process exit.
- Navigate, and a click that has an `href`, pass the origin whitelist before `page.goto`. A click without an `href` acts on the live element. Fill types into the live element. After each change, store the page HTML for snapshot and extract.
- Live evaluate runs in the page, at most 4,000 characters, only when the connection allows it. The result is untrusted. The expression cannot use a shell or the filesystem.
- Every live redirect hop stays on the whitelist and off private addresses, or it does not become the current page.
- Apply profile JSON from `SUPERSTEP_BROWSER_PROFILE_*` only to an origin that is both listed and whitelisted, and only before the first navigation. The generated file contains the variable name. Invalid JSON does not open a page.
- `max_pages` counts document navigations and refuses the next one. `stealth` is passed only when the provider is Browserless.
- Extend `backend/tests/test_browser_python_export.py`. Update the English and Vietnamese browser handbook export note and the project README sentence that describes a live session.
- Preserve the existing `memory` fixture tests.

### Out Of Scope

- TypeScript parity (TASK-0262).
- Upload, download, and screenshot image bytes. Those stay refused. A screenshot result stays `{captured: true, inline_bytes: false}`.
- Changing the `memory` driver into a live browser. Private origins stay reachable only on `memory` when whitelisted.
- Opening loopback or other private addresses with Playwright or Browserless.
- A Studio conversation lease, interactive profile capture, other managed adapters, MCP stdio/HTTP, and the retriever.
- TASK-0227 and TASK-0228.
- Schema changes and Alembic migrations.

## Inputs

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md` (2026-11-07 export-driver clarification).
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision: `.factory-state/decisions/DEC-0085-browser-tools.md` decision 10.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Fixture helper already on `develop` from TASK-0251: `backend/app/engine/browser_export.py`.
- Contract bounds: `docs/browser-contract.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0086-browser-tools.md`
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`
- Decisions: `.factory-state/decisions/DEC-0085-browser-tools.md`
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`
- Clarifications: REQ-0086 section "Owner clarification (2026-11-07) — export drivers"

## Expected Outputs

- Python export helper with a live Playwright/Browserless page and unchanged `memory` behavior.
- Tests that execute the live path when Playwright and Chromium are installed, and that do not report that path as passed when they skip.
- Handbook notes in `handbook/docs/en/guide/browser.md` and `handbook/docs/vi/guide/browser.md`.
- Review and QA artifacts before the task moves to done.

## Implementation Notes

- Generated code imports nothing from `app`. Tokens, proxy passwords, and profile JSON are read from the environment at run time.
- Close the browser on idle, lifetime expiry, and process exit.
- Reuse the current HTML parser for snapshot and extract after storing `page.content()`.
- Playwright remains an optional install. Do not add it as a required dependency of the exported project.
- Medium-task workflow. No new screen, so design review is the existing handbook wording. Technical direction is DEC-0085 decision 10.

## Constraints

- One task branch from `develop`, one pull request. Do not stack on an unmerged branch unless the owner says so.
- Do not modify the merged TASK-0251 behavior of the `memory` driver except to share helpers that keep those tests passing.
- No secrets, cookies, or image bytes in the generated source.
- Backend layers stay as in `docs/backend-architecture.md`. No FastAPI in the engine. No raw SQL.

## Dependencies

- TASK-0251 is merged. The fixture helper is on `develop`.
- TASK-0252 (PR #323) is the TypeScript fixture export and is not required to start this Python task.
- Task-start waits for a separate owner instruction. This file does not authorise implementation.

## Acceptance Criteria

- With `SUPERSTEP_BROWSER_DRIVER=playwright` or `browserless`, one alias uses one page until idle, lifetime expiry, or process exit.
- A click without an `href` and a fill change the live page. A later snapshot or extract sees the stored HTML from that page.
- Live evaluate accepts a page expression other than `document.title` and `document.body.innerText`, rejects an expression over 4,000 characters, and still refuses evaluate when the connection disallows it.
- A redirect hop off the whitelist or to a private address does not become the current page.
- Profile cookies and localStorage apply only to an origin that is both listed and whitelisted. The cookie value does not appear in the generated source. Invalid profile JSON does not open a page.
- `max_pages` refuses the next document navigation. `stealth` is not sent for a local Playwright provider.
- Upload, download, and inline screenshot bytes stay refused.
- Existing `memory` fixture tests still pass, including click-by-href, in-memory fill, the two evaluate expressions, and the private-origin fixture.
- A run without Playwright skips the live cases and does not count them as passed.

## Validation Plan

- `backend/.venv/bin/python -m pytest tests/test_browser_python_export.py`
- Full backend pytest from `backend/`: `.venv/bin/python -m pytest`
- `python3 scripts/check-browser-handbook.py`
- `git diff --check`
- Declared repo checks that the README or handbook change can affect: repo-root `npm run build`, `npm run lint`, and `npm run test` when the handbook or export README changes.
- Live Playwright cases must be executed once on a machine that has Playwright and Chromium. Record that run in the task activity log. A skip is not that evidence.
- At completion: review artifact, QA artifact, one commit, Ready pull request. Do not merge without the owner.

## Assumptions

- The owner approved the 2026-11-07 driver wording and asked for this task split. Implementation starts only after task-start.
- Designer and architect roles are skipped. The handbook copy is operator documentation. DEC-0085 decision 10 is the technical direction.
- Backend CI may not have Chromium. The live proof is recorded wherever Chromium is actually launched.

## Open Questions

- None. Task-start is a separate owner instruction.

## Activity Log

- 2026-11-07: Created by plan-tasks after `git fetch --all --prune` and `factory ids next TASK --all-refs` returned TASK-0261. Pair is TASK-0262. No product code, dependency install, or implementation branch.
- 2026-11-07: Owner said task-start. Branch `factory/task-0261-browser-python-live-export` from `develop` `78b289c3`. Status doing. No source edits.
- 2026-11-07: Owner said làm đi. Python live page is implemented in `backend/app/engine/browser_export.py`. Memory fixture behavior is unchanged. `backend/tests/test_browser_python_export.py` runs the live control flow through a stub `playwright` package beside `graph.py`. Playwright is not installed in the local venv (`find_spec` is None), and the live driver refuses loopback, so Chromium was not launched. A skip was not counted as a pass. Focused pytest: 16 passed. `python3 scripts/check-browser-handbook.py` passed. `git diff --check` passed.
- 2026-11-07: Tool-policy validation on this branch. Backend pytest 1440 passed, 71 skipped, 541.90s. SDK Python pytest 229 passed, 8 skipped, 16.49s. Repo-root npm build, lint (warnings only, 0 errors), and test passed on arm64 Node (frontend 177, react 22, sdk typescript 102). SDK TypeScript build, test (102), and typecheck passed. Handbook check and `git diff --check` passed. `factory verify` was not run through the x86_64 venv.
- 2026-11-07: Review REV-0251, no blocking findings, approved for QA. QA QA-0251, pass with follow-up. Chromium was not launched. Owner asked to finish the pull request without merging. Status done. PR #329.
- 2026-11-07: CI on PR #329 failed `test_live_page_reuses_one_browser_for_click_fill_and_evaluate` on Python 3.12. `atexit.unregister` clears the slot there without shrinking `_ncallbacks`, so the in-process probe returned false. The test now reads `playwright-log.json` after the process exits and expects one more `stop` from `_shutdown_live`. Product code is unchanged.

## Handoff Notes

- Branch: `factory/task-0261-browser-python-live-export`. Draft PR #329 becomes Ready in this step. Do not merge until the owner asks.
- Review: `.factory-state/artifacts/REV-0251-TASK-0261-browser-python-live-export.md`. QA: `.factory-state/artifacts/QA-0251-TASK-0261-browser-python-live-export.md`.
- TASK-0262 stays in todo. Do not start it until this pull request is on develop and the owner says task-start.
- Live control flow is proven with the stub. A real Playwright and Chromium launch is still a follow-up. REQ-0086 AC11 stays open.
- PR #323 is merged. It is not a blocker for this Python task.
