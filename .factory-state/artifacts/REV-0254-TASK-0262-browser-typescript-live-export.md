# Review

## Metadata

- Project: superstep
- Review ID: REV-0254
- Task ID: TASK-0262
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

Branch `factory/task-0262-browser-typescript-live-export` against `develop` `10300e20` (merge of PR #329). Draft pull request #334. The reviewed product diff is the TypeScript live page on top of the merged TASK-0252 helper, matching the merged TASK-0261 contract.

Files:

- `backend/app/engine/browser_export_ts.py`
- `backend/tests/test_browser_typescript_export.py`
- `backend/app/engine/project_export.py`
- `handbook/docs/en/guide/browser.md`
- `handbook/docs/vi/guide/browser.md`

No schema migration, UI component, locale catalog, or secret value was added. The Python helper was not changed. The `memory` driver contract is unchanged.

## Reference Artifacts

- TASK-0262 acceptance criteria
- REQ-0086 AC11
- DES-0004, ARCH-0002, DEC-0085 decision 10, PLAN-0006
- TASK-0261 and REV-0256 for the Python contract this task copies
- `docs/backend-architecture.md` (the embedded runtime imports nothing from `app`)

## Findings

### Blocking

- None.

### Non-Blocking

- Playwright is not installed, and the live driver refuses loopback, so Chromium and Browserless were not launched. The live control flow runs through a stub `playwright` package under `node_modules` and Node strip-types. Those tests pass as control-flow evidence. They are not a Chromium pass. The task sentence that says a run without Playwright skips the live cases is not implemented as `pytest.skip`; the stub executes instead of being counted as a browser launch.
- Process exit uses Node `beforeExit` and closes the browser asynchronously. The test sees one extra `close` in the stub log after the process ends. Deno was not run.
- Cookie domain matching treats a listed origin host as a match when it equals the cookie domain or is a subdomain of it. That matches the Python export and is slightly wider than Studio's exact-host profile validator. The export still drops origins that are not listed, not whitelisted, or private.
- The TypeScript allow-flag text is `true` because that is how JavaScript stringifies a boolean. The Python helper prints `True`. The refusal still names the flag and says the runtime has no attachment store.
- A click without `href` that changes the URL is refused and restored when `max_pages` is already reached. The under-limit success path for that click is implemented and not separately asserted. An `href` click is covered and reuses the same browser.
- The `memory` driver still fetches a whitelisted private origin. That is the TASK-0252 contract. Playwright and Browserless call `requirePublic` before importing Playwright.

## Standards And Architecture Alignment

- The helper is emitted into the export. Generated code imports nothing from `app`. Playwright is loaded with `import("playwright")` and then `import("npm:" + "playwright")`, so the exporter's `npm:` dependency regex does not add Playwright to `package.json`.
- Tokens, proxy passwords, and profile JSON stay in the environment. Invalid profile JSON raises `profile_invalid` before launch. Error strings for launch and fetch do not include the token.
- No FastAPI, raw SQL, or Alembic change. No new API catalog code. `profile_invalid` exists only inside the generated helper.
- Upload, download, and inline screenshot bytes stay refused. `stealth=true` is appended only to the Browserless URL. Local `chromium.launch` receives `headless` and, when set, `proxy`.

## Design Alignment

- No new screen. Handbook prose in English and Vietnamese now says the TypeScript export keeps one page until idle, lifetime, or process exit, matching DEC-0085 decision 10. The shared README states the same rule for both exports.
- UI conventions and browser verification do not apply. No component or theme token changed.

## Validation Review

- Tool-policy commands were run from the worktree with arm64 Node. Backend pytest: 1481 passed, 106 skipped, 588.76s. SDK Python pytest: 229 passed, 8 skipped, 14.01s. Repo-root `npm run build`, `npm run lint` (36 frontend warnings, 1 react warning, 0 errors), and `npm run test` (frontend 177, react 22, sdk typescript 102). SDK TypeScript build, test (102), and typecheck passed. `scripts/check-browser-handbook.py` and `git diff --check` passed.
- Focused export pytest (`test_browser_typescript_export.py`, `test_browser_python_export.py`, `test_typescript_export.py`, `test_project_export.py`): 48 passed, 29 skipped.
- `factory verify` was not run through the x86_64 venv. `factory validate` is still expected to fail on clean develop because TASK-0253 lacks the capital Review/REV- strings. That was not changed.

## Assumptions

- The owner asked to carry the remaining live-export task through a Ready pull request without merging.
- A stub of the Playwright async API is acceptable control-flow evidence on a machine that cannot launch Chromium. A later real launch remains a follow-up, not a blocker for this review.

## Required Follow-Up

- Do not mark REQ-0086 done. AC11 stays open until this pull request merges.
- Record one real Playwright and Chromium launch when a machine has both. Do not treat the stub run as that launch. Do not record a Deno pass.

## Review Decision

approved for QA
