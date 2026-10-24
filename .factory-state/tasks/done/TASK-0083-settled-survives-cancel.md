# Task

## Metadata

- Project: superstep
- Task ID: TASK-0083
- Status: done (PR #113)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0044
- Design IDs: none
- Architecture IDs: DEC-0046

## Objective

Fix the intermittent `test_chat_trigger_runs.py::test_waiting_then_finished_and_errors` timeout ("finished: approved"
reply never sent) in the SQLite backend CI job, at its root cause.

## Root Cause

`RunService.execute()` sends `run_summary`, then calls `settled()`, which awaited `asyncio.to_thread(chat.on_settled)`.
The studio socket closes as soon as it gets `run_summary` (the test client cancels the handler task at once). When every
default-executor thread was busy, the queued `to_thread` work item had not started yet, so the cancellation removed it
from the executor (`concurrent.futures.Future.cancel()`): the chat reply was silently never sent. The same applied to
the callback_url delivery and to test-suite recording after a cancelled handler. More likely on a slow or loaded
runner, which is why it showed up on the SQLite job and not locally. Reproduced locally under CPU load: 10 of 100 loops
failed.

## Scope

### In Scope

- `services/run_service.py`: `settled()` submits one `_settle` job through the existing `_write_in_thread` (submitted at
  once, shielded, never cancelled; the pattern the run-history write already uses).
- Regression test `test_settled_survives_a_cancelled_handler` (one busy executor thread, the settling task cancelled).

### Out Of Scope

- Raising test timeouts.

## Validation Plan

- The test looped 100 times under 8 busy CPU loops, before and after; the full backend suite; CI with the SQLite job
  re-run 3 times.

## Activity Log

- 2026-10-23: diagnosed from CI runs 39930090057 and 39943245803 (both fail at line 191, the post-resume reply) and a
  local instrumented loop (`settled()` entered, then CancelledError before `on_settled` ran); fixed; draft PR into develop.
- 2026-10-23: CI green, SQLite backend job re-run 3 times (4/4 green); owner approved the merge; merged into develop (PR #113).

## Handoff Notes

- None.
- Backfilled 2026-10-24 (TASK-0093): Review REV-0076; QA QA-0076; develop verified retroactively by QA-0085.
