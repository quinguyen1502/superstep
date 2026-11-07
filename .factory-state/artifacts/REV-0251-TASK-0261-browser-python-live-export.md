# Review

## Metadata

- Project: superstep
- Review ID: REV-0251
- Task ID: TASK-0261
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

Branch `factory/task-0261-browser-python-live-export` against `develop` `78b289c3`, pull request #329. The reviewed product diff is the Python live page on top of the merged TASK-0251 helper.

Files:

- `backend/app/engine/browser_export.py`
- `backend/tests/test_browser_python_export.py`
- `backend/app/engine/project_export.py`
- `handbook/docs/en/guide/browser.md`
- `handbook/docs/vi/guide/browser.md`
- `roadmap.md`
- `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- `.factory-state/artifacts/REQ-0086-browser-tools.md`
- `.factory-state/decisions/DEC-0085-browser-tools.md`
- `.factory-state/tasks/doing/TASK-0261-browser-python-live-export.md`

No schema migration, UI component, locale catalog, or secret value was added. The `memory` driver contract is unchanged. TASK-0262 is not implemented.

## Reference Artifacts

- TASK-0261 acceptance criteria
- REQ-0086 AC11 (Python half; TypeScript is TASK-0262)
- DES-0004, ARCH-0002, DEC-0085 decision 10, PLAN-0006
- `docs/backend-architecture.md` (the embedded runtime imports nothing from `app`)

## Findings

### Blocking

- None.

### Non-Blocking

- Playwright is not installed in the local venv, and the live driver refuses loopback, so Chromium and Browserless were not launched. The live control flow runs through a stub `playwright` package beside `graph.py`. Those tests pass as control-flow evidence. They are not a Chromium pass. The task sentence that says a run without Playwright skips the live cases is not implemented as `pytest.skip`; the stub executes instead of being counted as a browser launch.
- Cookie domain matching treats a listed origin host as a match when it equals the cookie domain or is a subdomain of it. The studio profile validator requires an exact host. The export still drops origins that are not listed, not whitelisted, or private.
- The shared project README states the live-page rule as Python behavior. The TypeScript export includes that sentence until TASK-0262. The handbook Python section does not claim the TypeScript driver already keeps one page.
- A click without `href` that changes the URL is refused and restored when `max_pages` is already reached. The under-limit success path for that click is implemented and not separately asserted. An `href` click is covered and reuses the same browser.
- The `memory` driver still fetches a whitelisted private origin. That is the TASK-0251 contract. Playwright and Browserless call `_require_public` before importing Playwright.

## Standards And Architecture Alignment

- The helper is emitted into the export. Generated code imports nothing from `app`. Playwright is loaded with `importlib.import_module("playwright.sync_api")`, so it is not a top-level import and is not added to `requirements.txt`.
- Tokens, proxy passwords, and profile JSON stay in the environment. Invalid profile JSON raises `profile_invalid` before launch. Error strings for launch and fetch do not include the token.
- No FastAPI, raw SQL, or Alembic change. No new API catalog code. `profile_invalid` exists only inside the generated helper.
- Upload, download, and inline screenshot bytes stay refused. `stealth=true` is appended only to the Browserless URL. Local `chromium.launch` receives `headless` and, when set, `proxy`.

## Design Alignment

- No new screen. Handbook prose in English and Vietnamese matches DEC-0085 decision 10: one page until idle, lifetime, or process exit; redirects stay on the whitelist; `memory` does not follow redirects.
- UI conventions and browser verification do not apply. No component or theme token changed.

## Validation Review

- Tool-policy commands were run from the worktree with arm64 Node. Backend pytest: 1440 passed, 71 skipped, 541.90s. SDK Python pytest: 229 passed, 8 skipped, 16.49s. Repo-root `npm run build`, `npm run lint` (36 frontend warnings, 1 react warning, 0 errors), and `npm run test` (frontend 177, react 22, sdk typescript 102). SDK TypeScript build, test (102), and typecheck passed. `scripts/check-browser-handbook.py` and `git diff --check` passed.
- `factory verify` was not run through the x86_64 venv. `factory validate` is still expected to fail on clean develop because TASK-0253 lacks the capital Review/REV- strings. That was not changed.

## Assumptions

- The owner asked to carry this branch through finish-pr without merging.
- A stub of the Playwright sync API is acceptable control-flow evidence on a machine that cannot launch Chromium. A later real launch remains a follow-up, not a blocker for this review.

## Required Follow-Up

- Do not mark REQ-0086 done. AC11 stays open until TASK-0262 merges.
- Do not start TASK-0262 until the owner says task-start after this pull request is on develop.
- Record one real Playwright and Chromium launch when a machine has both. Do not treat the stub run as that launch.

## Review Decision

approved for QA
