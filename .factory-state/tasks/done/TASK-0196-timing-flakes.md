# Task

## Metadata

- Project: superstep
- Task ID: TASK-0196
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0065 (reliable test suite)
- Design IDs: none
- Architecture IDs: DEC-0069

## Objective

Fix two timing-sensitive tests at their root cause, the way TASK-0109 (#136) did. The owner approved the follow-up after
the 0.10.0 release ("Làm đi"):
- `backend/tests/test_parallel_agent_tools.py::test_three_calls_overlap_and_keep_the_model_order` (TASK-0157);
- `frontend/e2e/studio.spec.ts` "register → logout → login → list → open example → run → done".

## Findings

- Parallel tool calls: the test proved concurrency with wall-clock overlap (`max(starts) < min(ends)`) while call `b`
  sleeps only 50 ms. In the full suite it failed twice in about seven `factory verify` runs during 0.10.0 work; in
  the failures `a` started about 0.36 s before `b` and `c`, and `b` and `c` started only after `a` ended, so the
  process stalled before the second and third worker threads ran. Isolated loops did not reproduce it (0 of 235 runs,
  including CPU load and pinning). The engine is correct: LangGraph submits all Send tasks of the wave to one thread
  pool. The assumption that three threads start within 50 ms is wrong under load. The test now uses a
  `threading.Barrier(3)`: every call waits until all three are inside, so a serial or capped wave fails
  deterministically (checked with the cap set to 2), and timing no longer matters. The 30 s barrier timeout only
  bounds the failure case.
- Studio e2e: after going back to the list, the test expected `getByText('ok', exact).first()` to be visible. Every
  row renders the last-run badge twice: a phone line (`sm:hidden`) in the name cell, then the Last run column. The
  first match is the hidden copy, so the test passed only when another visible `ok` happened to come first. Not a
  product bug. The test now checks the opened workflow's row (by id) for exactly one visible `ok`.

## Acceptance Criteria

- Each failure reproduced or explained with a measured rate, and fixed at the cause without raising timeouts.
- At least 50 isolated backend runs and 20 e2e runs pass after the fix, some under parallel load.
- `factory verify run --profile full` and `factory validate` pass.

## Validation

- Backend: before 0/235 isolated (2 of ~7 full-suite runs failed); after 60/60 isolated and 60/60 in 4 parallel loops
  with 8 CPU burners.
- E2E (the spec runs in vi only): before 10 of 20 failed (sequential) and 12 of 12 with 3 workers; after 25/25
  sequential, 12/12 with 3 workers, 15/15 with 3 workers and 6 CPU burners.

## Review And QA

- Review: `.factory-state/artifacts/REV-0175-task-0196.md`. QA: `.factory-state/artifacts/QA-0175-task-0196.md`.

## Activity Log

- 2026-10-31: implemented on `factory/task-0196-timing-flakes` from `develop` (numbered 0196 because REQ-0080 took
  TASK-0191 to TASK-0195).
