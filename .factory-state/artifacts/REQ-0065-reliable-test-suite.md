# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0065
- Status: Done (TASK-0109, PR #136)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner decision in chat, 2026-10-24 (step 3a of the v0.6.0 plan).

## Summary

- The test suites give the same result on every run: known flaky tests are fixed at their root cause, or skip with a clear reason when the host cannot run them.

## Acceptance Criteria

- `test_effectively_once.py::test_ui_run_paused_in_parallel_branch_does_not_rerun_sibling` passes 50 consecutive isolated runs (TASK-0092).
- `test_code_subprocess.py::test_timeout_kills_the_whole_process_group` passes, or skips with a stated reason when the process limit prevents the fork.
- The credentials e2e delete-confirm step passes repeated runs.
- `factory verify run --profile full` passes on the box; CI green.
