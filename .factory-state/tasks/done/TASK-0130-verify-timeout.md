# Task

## Metadata

- Project: superstep
- Task ID: TASK-0130
- Status: done
- 2026-10-26: PR #170 merged into develop (13c832b) with the owner's approval after CI passed (14 passed, 1 skipped); moved to done.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0066 (clean `factory verify`)
- Design IDs: none
- Architecture IDs: DEC-0064 (verification commands in the tool policy)

## Objective

Give the backend suite room under `factory verify` (owner request in chat on 2026-10-26: "Sửa luôn đi"). TASK-0129
found that the backend suite takes 205 to 265 s in CI and 346 s locally, against a fixed 300 s per-command timeout.

## Changes

- Upstream sw-ai-factory 6e66d20 (pushed to its `main`):
  - an optional `timeout` (seconds) on each tool-policy command, and `factory verify run --timeout`;
  - the default stays 300 s, and a timed-out check names the setting to raise;
  - discovered checks get unique policy names: two checks of one kind in one directory used to collide, and the
    first `verify run` failed.
- `.factory` vendored at 6e66d20.
- `tool-policy.yaml`: `backend-test` has `timeout: 900`. `tooling/generated.yaml` is refreshed by `factory tools apply`
  (the policy hash).
- `tests/fixtures/mcp_demo_server.py` reads the request body before it answers 401. Before, it closed the connection
  with the body unread, the socket reset, and the client sometimes saw `connection failed (ReadError)` instead of
  `HTTP 401`. That made `test_mcp.py::test_http_client_json_and_sse` fail at random: 4 of 20 runs before the fix, 0 of
  20 after.

## Findings

- With the timeout raised, the first local `verify run` got through the whole backend suite (348 s) and then failed on
  the MCP test above. It had passed in the run an hour earlier. Run alone, it failed 1 time in 3.

## Acceptance Criteria

- `factory verify plan --profile full` shows `timeout: 900s` for `backend-test`.
- `factory verify run --profile full` passes locally with the plain CLI, with no API workaround.
- CI's Factory verification passes.

## Validation

- Upstream: `python -m unittest discover -s tests`, 140 tests OK. The new tests cover the policy round trip, invalid
  values, the CLI flag, the timeout message and the name collision. The collision and timeout tests fail without the
  change.
- Superstep: `factory validate`, `verify validate`, `tools validate`, `skills validate` (70): passed.

## Validation Results

- `factory verify plan --profile full`: `backend-test` shows `timeout: 900s`.
- `factory verify run --profile full` with the plain CLI: all 8 checks passed (backend-test 348.06 s, over the old 300 s
  limit).
- `test_http_client_json_and_sse` 20 times in a row: 20 passed with the fixture fix, 16 passed and 4 failed without it.

## Review And QA

- Review: the owner reviewed PR #170 and approved the merge. No separate REV artifact.
- QA: the validation above, and CI on #170: Factory verification ran the 8 policy commands, all passed (backend 260 s
  under the 900 s limit).
