# Task

## Metadata

- Project: superstep
- Task ID: TASK-0127
- Status: doing
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0071 (runs across restarts), REQ-0072 (Agent node approvals)
- Design IDs: none
- Architecture IDs: DEC-0062 (start-up recovery), DEC-0043 (first answer wins)

## Objective

Fix a risk TASK-0123's review recorded: an answer to a waiting run is lost if the server restarts before the worker
takes its resume job (owner request in chat on 2026-10-26: "Làm thêm phần rủi ro kia đi").

## Findings

- Every answer path only enqueues a `resume` job. That covers the Approvals inbox, the chat channels, deadlines,
  MCP `resume_run`, `/api/lg` and workflow tests. With the in-memory queue the job is lost on a restart, and
  start-up recovery skips waiting runs.
- **Effect:**
  - the run stays `waiting`;
  - inbox and channel answers had already closed the waiting step, so a second answer is refused
    (`APPROVAL_ALREADY_DECIDED`); the run can only expire.
- **A second window:** a worker claims the run (`running`) and the server stops before the resumed segment saves
  anything. Recovery then sees a `running` run whose checkpoint is not a progress checkpoint, and restarts it from
  the beginning without the answer.

## Changes

- `runs.resume_job` (Text, JSON), migration `0039_resume_job`.
- `job_queue.enqueue_resume(runs, enqueue, job)` keeps the job on the run (only while it waits), then queues it.
  All five call sites use it: `approval_service` (3), `trigger_service.resume` (MCP), `agent_server_service`
  (`/api/lg`) and `workflow_test_service`.
- The kept job is cleared by the next progress checkpoint (`RunRepository.save_progress`) or result
  (`RunService.record`).
- `RunWorker.recover_unfinished` (in-memory queue) queues the kept jobs again:
  - a run still `waiting` is resumed;
  - a `running` run with a kept job (claimed, nothing recorded since) goes back to `waiting` first, or ends as
    `RUN_INTERRUPTED` at the limit;
  - such runs are left out of the usual recovery.
- Handbook `operate/deploy.md` (en, vi), CHANGELOG (Unreleased, Fixed).

## Acceptance Criteria

- An inbox answer whose resume job is lost before a restart resumes the run after the restart.
- A run claimed by a resume and cut off before it recorded anything resumes with the answer, not from the start.
- The recovery limit still applies; a finished run keeps no answer.

## Validation Results

- New `tests/test_resume_recovery.py` (4 tests). New `tests/test_durable_restart.py::test_answer_queued_before_a_restart_is_not_lost`
  (a real server with `STUDIO_WORKER=0`, then restarted with the worker on).
- Without the recovery change: 3 of the new unit tests fail and the real-server test ends `waiting`; with it,
  all pass.
- Full backend `pytest`: 722 passed, 56 skipped.
