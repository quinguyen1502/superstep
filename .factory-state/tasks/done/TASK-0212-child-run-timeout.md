# Task

## Metadata

- Project: superstep
- Task ID: TASK-0212
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0065 (reliable test suite), REQ-0073 (workflow tools)
- Design IDs: none
- Architecture IDs: DEC-0066, DEC-0017

## Objective

Fix at the cause, without retries, skips or a longer limit, the failure of `e2e/workflow-tools.spec.ts:31` (vi) in E2E
shard 3/3 on PR #268 (run 41190882491): the child run of a workflow tool ended with `timeout` (the 5 s
`STUDIO_RUN_TIMEOUT` of the E2E stack), so the child's step list under the tool call was empty.

## Findings

Evidence from the job log and the Playwright trace (`gh run download`, artifact `e2e-shard-3`):

- The test was not the first in the shard: it was test 38 of 45 (after `workflow-tests.spec.ts`), so it was not a cold
  start of the server or of Vite.
- The parent run (UI) went waiting at 10:03:37.856 UTC; the child `3f5f5332cc` (source `tool`) emitted `run_started` at
  10:03:37.855, so it did not wait for a worker or the queue, and its timer did not start at enqueue. Its next and only
  other event is the `RUN_TIMEOUT` error at 10:03:50.489, **12.63 s** later, with no node started. The parent's limit is
  not inherited: the parent's own segment took 30 ms, and the child's deadline is its own `t0 + STUDIO_RUN_TIMEOUT`.
- A 5 s `asyncio.wait` cannot fire after 12.6 s while the loop is free, and it was: the trace shows the page's
  `GET /api/workflows/…/runs` answered in 8 ms every 2 s through the whole gap. So the child reached its wait loop only
  after the deadline had already passed, and timed out on the first `wait(timeout=0)`. Between `t0` and that loop
  `RunService._execute` awaits only the `run_started` emit (in-memory bus) and `_save_progress`, the first progress
  checkpoint of a queue job (one `UPDATE` on the run row, SQLite with a 15 s busy timeout). That write took ~12.6 s.
- **Product bug**: the run's deadline was computed from `t0`, before that setup, so time spent waiting for the database
  before the engine started counted against `STUDIO_RUN_TIMEOUT`, and a run could time out without running a node. It
  affects every queued run (API, schedules, tests, child runs), not only the E2E stack.
- Why the write waited 12.6 s on the CI runner (SQLite write lock or the default thread pool) is not visible in the
  artifacts (the E2E server logs no timings), and it did not happen locally: two full `--shard=3/3` runs (one with 4
  CPUs and `PYTHON_CPU_COUNT=4`) with a probe on that write passed 39/39 and never saw it take over 0.3 s.

## Fix

`RunService._execute` starts the deadline right before the engine thread starts, after the first progress write. The
limit's length and its message are unchanged (`runtime.spec` still sees `(5s)`); no spec or E2E setting was changed.
Earlier flaky fixes (TASK-0196, TASK-0200, TASK-0201, TASK-0209) fixed test races or other product paths; none of them
touched the run timer, and nothing here raises a timeout or adds a retry.

## Acceptance Criteria

- The failure explained from the CI trace and reproduced deterministically before the fix.
- The reproduction passes after the fix; the time limit still stops a child whose nodes run past it.
- `factory verify run --profile full` and `factory validate` pass; CI green, all three E2E shards included.

## Validation

- Reproduction (throwaway hook, not committed): the child's first progress write sleeps 6 s
  (`E2E_SLOW_FIRST_PROGRESS=6`), `workflow-tools.spec.ts -g "set up in the editor" --repeat-each 3`.
  Before (develop e92f6761): 0/6, every repeat with the CI error (`child-step` not found, the child `timeout`).
  After: 9/10 over two runs; the one failure (first test on a fresh server, `#trace-summary` still `running` after
  30 s) happened the same way before the fix and never without the hook.
- Backend: `test_a_slow_first_progress_write_does_not_count_against_the_child_run_time` fails before the fix (child
  `timeout`) and passes after; `test_the_time_limit_still_stops_a_slow_child` and `test_core_hardening.py::test_timeout`
  pass before and after.
- Without the hook: before the fix `workflow-tests.spec.ts` + `workflow-tools.spec.ts` 11/11 and `--shard=3/3` 39/39
  twice (the failure needs the CI timing); after the fix `--shard=3/3` 39/39 (`runtime.spec` timeout `(5s)` included).

## Review And QA

- Review: `.factory-state/artifacts/REV-0200-task-0212.md`. QA: `.factory-state/artifacts/QA-0200-task-0212.md`.

## Activity Log

- 2026-10-31: created from the owner's request to fix the workflow-tools E2E failure on #268 at the cause; implemented
  on `factory/task-0212-child-run-timeout` from `develop` (e92f6761). Moved to done on this PR before the merge.
  REV/QA 0200 because #268 uses 0199.
