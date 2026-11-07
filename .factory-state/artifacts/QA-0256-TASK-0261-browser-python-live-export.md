# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0256
- Renumbered: QA-0251 → QA-0256 on 2026-11-07 (TASK-0272). PR #331 merged first and keeps QA-0251 for TASK-0269.
- Task ID: TASK-0261
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass with follow-up

## Validation Scope

Python export live page for Playwright and Browserless on `factory/task-0261-browser-python-live-export`, pull request #329. The `memory` driver stays the TASK-0251 fixture. Live control flow is executed by a stub `playwright` package written beside `graph.py` and imported by the generated helper. Playwright is not installed (`find_spec` is None). Chromium was not launched. Review REV-0256 recorded no blocking findings.

## Acceptance Criteria Coverage

- Criterion: With `SUPERSTEP_BROWSER_DRIVER=playwright` or `browserless`, one alias uses one page until idle, lifetime expiry, or process exit.
  - Result: pass
  - Evidence: `test_live_page_reuses_one_browser_for_click_fill_and_evaluate` records one `launch` before the first `stop`, then a second `launch` only after idle closes the browser. The recovered navigate is `confirmed`. Process exit runs the registered `_shutdown_live` closer: the stub log gains one `stop` after the process ends. Python 3.12 does not shrink `atexit._ncallbacks` when `unregister` clears a slot, so the check does not use that counter. Browserless uses `connect_over_cdp` once in `test_live_profile_and_browserless_stealth` and does not call `launch`. Lifetime uses the same `_close_live` path as idle and is not a separate live case.

- Criterion: A click without an `href` and a fill change the live page. A later snapshot or extract sees the stored HTML from that page.
  - Result: pass
  - Evidence: The same test clicks `#go`, sees button text `Clicked`, fills `SO-1`, and the following snapshot and extract both report `SO-1` for element `order`. An `href` click then stores `https://example.com/next` without a second launch.

- Criterion: Live evaluate accepts a page expression other than `document.title` and `document.body.innerText`, rejects an expression over 4,000 characters, and still refuses evaluate when the connection disallows it.
  - Result: pass
  - Evidence: `document.querySelector("#status")` returns a `live:` value and one evaluate log entry of that length. A 4001-character expression returns `capability_refused` and does not add an evaluate log entry. The existing memory test still refuses `alert(1)` and accepts `document.title` when the live page is absent. The connection flag is still required before either path.

- Criterion: A redirect hop off the whitelist or to a private address does not become the current page.
  - Result: pass
  - Evidence: `test_live_redirect_does_not_replace_the_page` navigates to `https://example.com/`, then a hop to `https://evil.test/` returns `whitelist_denied` and a hop to `http://127.0.0.1/secret` returns `private_address`. The stored URL stays `https://example.com/`. A script request to `https://evil.test/app.js` aborts without failing the document. `about:blank` is continued.

- Criterion: Profile cookies and localStorage apply only to an origin that is both listed and whitelisted. The cookie value does not appear in the generated source. Invalid profile JSON does not open a page.
  - Result: pass
  - Evidence: `test_live_profile_and_browserless_stealth` asserts `synthetic-cookie`, `synthetic-storage`, and `other-cookie` are absent from the export. Env `{` returns `profile_invalid` with an empty Playwright log. A wider runtime seed applies only the `allowed.test` cookie and `https://allowed.test:8443` localStorage. The existing memory test still returns `profile_missing` when the profile env is empty.

- Criterion: `max_pages` refuses the next document navigation. `stealth` is not sent for a local Playwright provider.
  - Result: pass
  - Evidence: `test_live_max_pages_refuses_the_next_document` with `max_pages` 1 refuses the click navigation and the next navigate with `limit` and `max_pages`, keeps `https://example.com/`, records `go_back`, and shows one `goto`. Local launch keys are `["headless"]`. Browserless connect URL is `https://browserless.example/session?token=redacted&stealth=true` with no launch. `test_memory_driver_does_not_count_max_pages` navigates twice under `max_pages` 1 and both calls are `confirmed`.

- Criterion: Upload, download, and inline screenshot bytes stay refused.
  - Result: pass
  - Evidence: The live test uploads with `allow_upload` true and gets `capability_refused` plus `refused outside Studio` and `True`. Screenshot is `{captured: true, inline_bytes: false}`. Download remains the same pre-store refusal as upload.

- Criterion: Existing `memory` fixture tests still pass, including click-by-href, in-memory fill, the two evaluate expressions, and the private-origin fixture.
  - Result: pass
  - Evidence: `tests/test_browser_python_export.py` is 16 passed inside the full backend run. `test_profile_and_private_drivers_fail_closed` still prints `private_address` for Playwright against the loopback fixture and records no HTTP hits. The recipe fill result still omits the order id.

- Criterion: A run without Playwright skips the live cases and does not count them as passed.
  - Result: pass with follow-up
  - Evidence: The live cases do not `pytest.skip`. They execute against the stub and pass. That pass is control-flow evidence, not a Chromium pass. The activity log and this report state that Chromium was not launched.

## UX And Accessibility Coverage

- Criterion: No new UI.
  - Result: pass
  - Evidence: The diff does not change frontend components, theme tokens, or locale catalogs. Handbook prose is documentation only. Browser verification of the app was not required.

## Checks Performed

- `backend/.venv/bin/python -m pytest` — 1440 passed, 71 skipped, 541.90s, exit 0
- `sdk/python/.venv/bin/python -m pytest` — 229 passed, 8 skipped, 16.49s, exit 0
- Repo root, Node arch arm64: `npm run build`, `npm run lint` (36 frontend warnings and 1 `@superstep/react` warning, 0 errors), `npm run test` — exit 0. Frontend 177 passed. `@superstep/react` 22 passed. `@superstep/sdk` 102 passed.
- `sdk/typescript`: `npm run build`, `npm run test` (102 passed), `npm run typecheck` — exit 0
- `python3 scripts/check-browser-handbook.py` — passed
- `git diff --check` — passed
- `factory verify` was not launched through the x86_64 venv

## Defects

- None open.

## Gaps Or Untested Areas

- A real Chromium launch and a live Browserless endpoint were not executed. The stub is the control-flow proof.
- `factory validate` still fails on clean develop because TASK-0253's done file lacks the capital Review/REV- strings. That failure is pre-existing and was not changed. CI `factory verify` does not run `factory validate`.

## Residual Risk

- The memory driver will fetch a private origin when that origin is on the connection whitelist. Playwright and Browserless will not.
- Export cookie matching allows a subdomain of the cookie domain. Studio profile storage still requires an exact host.
- Parallel Agent tool batches can still raise `interrupt()` off the graph thread. Same-connection commands remain serialized. This task did not change that path.

## Assumptions

- Synthetic fixtures (`synthetic-cookie`, `synthetic-storage`, `other-cookie`, `fixture-browserless-token`, `runtime-token`) are test data and are absent from generated code.
- The owner wants this pull request Ready and does not want it merged in this step.

## Required Follow-Up

- Do not mark REQ-0086 done until TASK-0262 is merged. AC11 stays open.
- When a machine has Playwright and Chromium, run one live navigation and record it. Do not treat this QA as that launch.
- TASK-0262 stays in todo until the owner says task-start.

## QA Decision

conditionally passed with documented risk
