# Task

## Metadata

- Project: superstep
- Task ID: TASK-0092
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: none (test reliability)
- Design IDs: none
- Architecture IDs: DEC-0018 (effectively-once side effects)

## Objective

Make `backend/tests/test_effectively_once.py::test_ui_run_paused_in_parallel_branch_does_not_rerun_sibling`
deterministic. Recorded only; no fix in this task yet.

## Evidence

- Fails about 1 run in 4 on the box, on develop and on branches that do not touch the engine (seen on the
  docs-only branch `factory/task-0089-superstep-vs-langsmith` and on `feat/agent-server-api`): 4 isolated runs gave
  3 passed, 1 failed with `KeyError: 'a'` at `CALLS["a"] == [1]` (line 272).
- Passes on rerun; CI has not failed on it so far.

## Hypothesis (not confirmed)

- The test starts `a` (Tool) and `h` (Human) in the same superstep. When the Human interrupt is raised before the
  sibling Tool node has run (LangGraph runs parallel nodes in threads, order not guaranteed), the first segment
  ends with `CALLS` lacking `"a"`, so the assertion raises `KeyError` instead of failing on the value. The engine
  behaviour under test (the sibling is not re-run on resume) may still be correct; the test assumes the sibling
  always finishes before the pause.

## Scope

### In Scope

- Confirm the cause (loop the test, log the order of node starts).
- Either make the engine's guarantee explicit (siblings of a Human node finish before the run pauses) and test it,
  or make the test independent of the order (`CALLS.get("a", [])`, and assert "at most once across both segments").

### Out Of Scope

- Other flaky tests (`test_code_subprocess.py::test_timeout_kills_the_whole_process_group` is a known box-only flake).

## Acceptance Criteria

- 50 consecutive isolated runs pass on the box; CI green.
- If the engine changes, a DEC records the ordering guarantee.
