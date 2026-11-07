# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0242
- Task ID: TASK-0251
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Validation Scope

Python and LangGraph project export of browser tools and recipes on
`factory/task-0251-browser-python-export` at base `e26e39e9`. Evidence is
`backend/tests/test_browser_python_export.py` executed with `python -I`, plus
the declared tool-policy commands. TypeScript parity is TASK-0252 and is not
claimed here. Review REV-0242 recorded no blocking findings.

## Acceptance Criteria Coverage

- Criterion: Exported Agent and recipe fixtures run outside Superstep with no MCP placeholder, no Superstep import, and no fixed URL substituted for dynamic input.
  - Result: pass
  - Evidence: `test_recipe_runs_outside_superstep_without_secrets_or_a_fixed_url` invokes the recipe and reads shipment status `In transit`. The fill result does not contain the order id. `test_child_recipe_export_calls_the_helper` covers a nested recipe. `test_fixed_binding_is_used_and_model_binding_is_not_replaced` keeps a fixed binding and leaves a model binding as `missing_url`. `test_agent_parallel_calls_keep_session_order` invokes an Agent graph as `__main__`. AST import scan has no `app` or `playwright`. `managed_placeholders` is false for a valid browser connection.

- Criterion: Supported proxy, profile, and policy settings are retained. Credentials, cookies, and provider tokens are absent from generated code and example environment values.
  - Result: pass
  - Evidence: `test_public_policy_omits_secrets_and_rejects_invalid_settings` keeps the proxy server and omits password and token. `test_secrets_stay_in_the_environment_and_failures_do_not_open_a_page` asserts the fixture token and proxy password are absent, then fails closed with `token_missing` and `proxy_credentials_missing` before any HTTP hit. `test_profile_and_private_drivers_fail_closed` asserts the synthetic cookie and storage text are absent, `profile_missing` when the profile env is unset, and `private_address` for the Playwright driver against loopback. The project zip `.env.example` lists `SUPERSTEP_BROWSER_*` names with empty values. `requirements` stays langgraph-only for the memory driver.

- Criterion: Concurrent tool calls keep same-session command order. Approval, rejection, lost session, and unknown effects keep the required behavior.
  - Result: pass
  - Evidence: `test_same_session_commands_do_not_overlap` records sequences 1 then 2 and server peak 1. `test_agent_parallel_calls_keep_session_order` keeps server peak 1 across two parallel navigations. `test_approval_stale_lost_unknown_and_whitelist` rejects `False` and a model-shaped `{"text":"yes"}`, accepts only `{"approved": true}`, reports `stale_observation` without applying the click, pops `SUPERSTEP_BROWSER_FAULT` for unknown and lost, and does not replay. `test_idle_timeout_drops_the_page_and_does_not_replay` clears the page on idle and requires a new explicit navigate.

- Criterion: Unsupported behavior is refused with an explicit capability explanation. Plain code, the project manifest, and setup guidance agree.
  - Result: pass
  - Evidence: Upload and download raise `capability_refused` and the message names the refusal outside Studio. Evaluate refuses JavaScript other than the two allowlisted expressions. Invalid settings stay a managed placeholder (`test_invalid_browser_settings_stay_a_placeholder`). The TypeScript file throws `TS_BROWSER_REFUSAL` and does not call `callMcpTool` or `managedOperation`. README browser bullets appear only when `browser_call` is present. English and Vietnamese handbook section 5 matches that contract. `scripts/check-browser-handbook.py` passed.

## UX And Accessibility Coverage

- Criterion: No new UI.
  - Result: pass
  - Evidence: The diff does not change frontend components, theme tokens, or locale catalogs. Handbook prose is documentation only. Browser verification of the app was not required.

## Checks Performed

- `backend/.venv/bin/python -m pytest` — 1427 passed, 71 skipped, 522.03s, exit 0
- repo root, Node arch arm64: `npm run build`, `npm run lint` (warnings only), `npm run test` — exit 0
- `sdk/python/.venv/bin/python -m pytest` — 229 passed, 8 skipped, 13.77s
- `sdk/typescript`: `npm run build`, `npm run test` (102 passed), `npm run typecheck` — exit 0
- `scripts/check-browser-handbook.py` — passed
- Focused export files were included in the backend run: `test_browser_python_export.py`, `test_managed_tools.py`, `test_project_export.py`, `test_python_export.py`, `test_typescript_export.py`, `test_handoff_exports.py`

## Defects

- None open.

## Gaps Or Untested Areas

- Live Playwright Chromium and a live Browserless endpoint were not launched. Private-address, missing-token, and missing-Playwright paths are the proofs.
- TypeScript execution of browser tools is not in this task. The export throws instead of stubbing.
- `factory validate` still fails on clean develop because TASK-0253's done file lacks the capital Review/REV- strings. That failure is pre-existing and was not "fixed". CI `factory verify` does not run `factory validate`.

## Residual Risk

- The memory driver will fetch a private origin when that origin is on the connection whitelist. Playwright and Browserless will not.
- Parallel Agent tool batches can raise `interrupt()` off the graph thread. Same-connection commands remain serialized.

## Assumptions

- Synthetic fixtures (`fixture-browserless-token`, `fixture-user`, `fixture-password`, `synthetic-cookie`) are test data and are absent from generated code.
- The owner wants this pull request Ready and does not want it merged yet.

## Required Follow-Up

- TASK-0252 implements the TypeScript helper and extends the handbook note.
- Do not mark REQ-0086 done until TASK-0252 is merged as well.

## QA Decision

Passed to done. Advisory QA only; merge still needs the owner.
