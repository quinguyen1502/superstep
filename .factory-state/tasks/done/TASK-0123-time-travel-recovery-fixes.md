# Task

## Metadata

- Project: superstep
- Task ID: TASK-0123
- Status: done
- 2026-10-26: PR #153 merged into develop (405b54f) with the owner's approval after CI passed (15 passed, 2 skipped); moved to done.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0051 (time travel, TASK-0088), REQ-0071 (runs across restarts, TASK-0115)
- Design IDs: none
- Architecture IDs: DEC-0057 (time travel), DEC-0062 (start-up recovery)

## Objective

Fix two defects found when reviewing the work merged since v0.5.0 (owner request in chat, 2026-10-26).

## Findings

1. **Time travel groups sequential nodes into one checkpoint.**
   - Cause: `services/time_travel.checkpoints` treated nodes that started, one after another, from the same state as
     one parallel superstep. A Condition leaves the state unchanged, so the node after it joined its checkpoint.
   - Reproduced on Start → Condition → (Yes | No) → End:
     - the checkpoints were `[route, yes]` and the final state;
     - forking checkpoint 0 with `message: "nope"` ran `route, yes, e, no, e`: both branches, and End twice.
2. **Start-up recovery counts resumes as interruptions.**
   - Cause: `RunWorker.recover_unfinished` compared `runs.lease_gen` with `STUDIO_RECOVER_MAX_ATTEMPTS`, but
     `lease_gen` goes up on every claim: the start, each recovery, and each resume after a Human node or an Agent
     tool approval.
   - Effect: a run resumed twice and then cut off by its first restart ended as `RUN_INTERRUPTED` ("3 times").

## Changes

- Time travel:
  - `engine/runtime.run_stream` numbers the supersteps of a segment, and each `node_finished` event carries its
    `superstep`;
  - `time_travel.checkpoints` groups nodes by that number, and a checkpoint's state is the state at the start of its
    superstep;
  - events without `superstep` (runs recorded before this change) keep the old grouping by equal state.
- Restart recovery:
  - `RunService.interruptions(run)` = `lease_gen` minus the run's `run_resumed` events;
  - recovery gives up when that number reaches the limit, and `RUN_INTERRUPTED` reports it.
- Handbook (deploy, configuration; en, vi), `core/config.py` comment, CHANGELOG (Fixed).

## Acceptance Criteria

- Forking before a Condition with an edited state runs the Condition alone, then only the branch it picks.
- Parallel nodes still form one checkpoint.
- A resumed run that is cut off by a restart continues, as long as restarts alone stay under the limit.
- A run cut off by restarts still ends as `RUN_INTERRUPTED` at the limit.

## Validation

- New tests:
  - `tests/test_time_travel.py::test_checkpoints_follow_the_superstep_numbers`;
  - `tests/test_time_travel.py::test_fork_before_a_condition_takes_one_branch`;
  - `tests/test_durable_restart.py::test_resumes_do_not_count_as_interruptions` (a real server killed after a
    Human-node resume, with `STUDIO_RECOVER_MAX_ATTEMPTS=2`).
- All three fail without the fix and pass with it.
- Backend `pytest`: 717 passed, 54 skipped.
- e2e `time-travel`, `agent-node`, `agent-tests`, `trace`: 6 passed.

## Review And QA

- Review of the merged work: this task's Findings. Not changed, noted as low-risk:
  - an answer sent with MCP `resume_run` is lost if the server restarts before the worker takes the job; the run
    stays waiting;
  - a recovered run's mock replies use the default language;
  - `/api/lg` reveals that a `thread_id` exists even when it belongs to someone else.
- QA: the validation above. No separate REV or QA artifact (owner asked for the fix directly).
