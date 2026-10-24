# Task

## Metadata

- Project: superstep
- Task ID: TASK-0109
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0065
- Design IDs: none
- Architecture IDs: DEC-0018 (effectively-once side effects)

## Objective

Fix the flaky tests: TASK-0092 (parallel Human sibling), the box-only subprocess process-group test, the credentials
e2e delete-confirm timeout, plus two CI timing flakes found while merging the v0.6.0 PRs.

## Root Causes And Fixes

- `test_ui_run_paused_in_parallel_branch_does_not_rerun_sibling` (TASK-0092): the Human node pauses by raising
  `Interrupt`; LangGraph's runner cancels sibling tasks that have not started when a task raises
  (`langgraph/pregel/_runner.py`, "if any task failed, cancel all other tasks"). So the Tool sibling `a` runs before
  the pause or not at all; both are correct (it then runs once on resume). The test assumed it always ran first.
  Fix (test only): accept both orders and assert the invariant: `a` runs exactly once across both segments, the
  ledger holds its result only if it ran, and the resume reports `reused` exactly then. Engine unchanged.
- `test_timeout_kills_the_whole_process_group`: the subprocess runner sets `RLIMIT_NPROC`, which counts every process
  of the user; on the shared box the limit is already reached, so `subprocess.Popen` in the sandboxed code fails with
  `BlockingIOError` (CODE_FAILED) before the timeout. Fix: skip with that reason when this exact failure occurs.
- `credentials.spec.ts` delete confirm: the trash button was clicked as soon as it existed, while the dialog list was
  still rendering, so the click could land on a replaced button and the confirm dialog never opened. Fix: wait for
  the row, and retry the click until `#confirm-delete` is visible.
- `test_code_node.py::test_time_limit_and_cancel_stop_the_call` (failed once on CI after #132, 7.4 s against a 5 s
  bound): the code loops forever, so any bound proves the kill; raised to 15 s.
- `scripts/compose_smoke.py` (All-in-one image job failed once on #133, empty run history): the script stopped at
  `run_finished`, which is sent before the run is written to history. It now stops at `run_summary`, sent after the write.

## Scope

### In Scope

- backend/tests/test_effectively_once.py, test_code_subprocess.py, test_code_node.py; frontend/e2e/credentials.spec.ts;
  scripts/compose_smoke.py.

### Out Of Scope

- Engine changes (none needed); factory validate cleanup (TASK-0110).

## Activity Log

- 2026-10-24: reproduced (1 in 20 isolated runs failed with KeyError 'a'), fixed, proved with repeated runs, verified (QA-0101); PR into develop. Closes TASK-0092.

- 2026-10-24: PR #136 merged into develop (1a77fde); moved to done by TASK-0110.

## Handoff Notes

- Review REV-0101, QA-0101.
