# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0244
- Task ID: TASK-0252
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Validation Scope

TypeScript and LangGraph.js project export of browser tools and recipes on
`factory/task-0252-browser-typescript-export`, stacked on
`factory/task-0251-browser-python-export` at `c39064ed` (PR #321). Evidence is
`backend/tests/test_browser_typescript_export.py` executed with Node
`--experimental-strip-types` and a local LangGraph stub. Deno is not installed
here, so a Deno run is not claimed. The emitted source still keeps `npm:`
specifiers. Review REV-0244 recorded no blocking findings.

## Acceptance Criteria Coverage

- Criterion: TypeScript standalone and project browser Agent and recipes execute the same supported local fixture scenarios outside Superstep.
  - Result: pass
  - Evidence: `test_recipe_runs_on_node_without_secrets_or_a_fixed_url` calls generated `open`, `fill`, and `read`. Shipment status is `In transit`. The fill result does not contain `SO-1`. No `Authorization` header is sent. The project zip README names `browserCall`, and `package.json` does not depend on Playwright. `test_agent_parallel_calls_keep_session_order` calls generated `browser_tool` with two pending navigations. `test_invalid_browser_settings_stay_a_placeholder` keeps a managed placeholder and does not emit `browserCall`.

- Criterion: No credentials, Superstep-only ids as runtime authority, silent MCP stub, or dropped policy appear in the output.
  - Result: pass
  - Evidence: Recipe and secrets tests assert fixture token, proxy password, and the server id are absent. The proxy URL may appear. `test_secrets_and_private_drivers_do_not_open_a_page` returns `token_missing`, then `proxy_credentials_missing`, with no HTTP hits. `test_profile_missing_and_playwright_refuses_loopback` asserts the synthetic cookie and storage text are absent, then `profile_missing` before a page. `.env.example` contains `SUPERSTEP_BROWSER_DRIVER=` with an empty value. Stored workflows do not contain `_browser_export` or `_managed_export`.

- Criterion: Same-session serialization, stale observation, and unknown effects match the Python contract despite parallel Agent tool calls.
  - Result: pass
  - Evidence: `test_same_session_commands_do_not_overlap` records sequences `[1, 2]`, session peak 1, and server peak 1 under `Promise.all`. The agent test keeps server peak 1 across at least two hits. `test_approval_stale_lost_unknown_and_whitelist` rejects `false` and `{text: "yes"}`, grants `{approved: true}`, reports `stale_observation` without changing the page URL, pops `SUPERSTEP_BROWSER_FAULT` for unknown and lost, and lets a later explicit navigate succeed. `test_idle_timeout_drops_the_page_and_does_not_replay` sets `touched` to 100000 seconds before `Date.now()/1000`, expects `session_lost`, an empty page URL, and one new explicit navigate.

- Criterion: Unsupported capabilities fail explicitly. Existing non-browser TypeScript exports stay compatible.
  - Result: pass
  - Evidence: Upload returns `capability_refused` and the message contains `refused outside Studio` even though `allow_upload` is on. Evaluate of `alert(1)` is `capability_refused`; `document.title` returns `Track`. Screenshot is `{captured: true, inline_bytes: false}`. Off-whitelist navigation is `whitelist_denied`. Playwright against the loopback fixture is `private_address` with no hits. `test_typescript_export.py` snapshot and project/handoff regressions are in the focused run (45 passed, 30 skipped). The skips are the pre-existing Deno-gated checks.

## UX And Accessibility Coverage

- Criterion: No new UI.
  - Result: pass
  - Evidence: The diff does not change frontend components, theme tokens, or locale catalogs. Handbook prose is documentation only. Browser verification of the app was not required.

## Checks Performed

- Focused backend pytest (`test_browser_typescript_export.py`, `test_browser_python_export.py`, `test_typescript_export.py`, `test_project_export.py`, `test_handoff_exports.py`) — 45 passed, 30 skipped, 50.67s, exit 0
- `backend/.venv/bin/python -m pytest` — 1435 passed, 71 skipped, 526.00s, exit 0
- repo root, Node arch arm64 v22.12.0: `npm run build`, `npm run lint` (36 frontend warnings, 0 errors, pre-existing), `npm run test` — exit 0. Frontend 169 passed. `@superstep/react` 22 passed.
- `sdk/python/.venv/bin/python -m pytest` — 229 passed, 8 skipped, 13.75s
- `sdk/typescript`: `npm run build`, `npm run test` (102 passed), `npm run typecheck` — exit 0
- `python3 scripts/check-browser-handbook.py` — passed
- `git diff --check` — passed

## Defects

- None open.

## Gaps Or Untested Areas

- Live Playwright Chromium and a live Browserless endpoint were not launched. Private-address, missing-token, and missing-Playwright paths are the proofs.
- Deno was not executed. Node strip-types is the local proof. CI may run Deno for the older TypeScript export tests; those tests skip locally when Deno is absent.
- `factory validate` still fails on clean develop because TASK-0253's done file lacks the capital Review/REV- strings. That failure is pre-existing and was not "fixed". CI `factory verify` does not run `factory validate`.

## Residual Risk

- The memory driver will fetch a private origin when that origin is on the connection whitelist. Playwright and Browserless will not.
- Parallel Agent tool batches can raise `interrupt()` off the graph thread. Same-connection commands remain serialized.
- `max_pages` is not enforced, matching the Python export.

## Assumptions

- Synthetic fixtures (`fixture-browserless-token`, `fixture-user`, `fixture-password`, `synthetic-cookie`, `synthetic-storage`) are test data and are absent from generated code.
- The owner wants this pull request Ready and does not want it merged yet. TASK-0251 (PR #321) merges first.

## Required Follow-Up

- Do not mark REQ-0086 done until both export pull requests are merged.
- Merge TASK-0251 before this branch.

## QA Decision

Passed to done. Advisory QA only; merge still needs the owner.
