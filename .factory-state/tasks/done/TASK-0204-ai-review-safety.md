# Task

## Metadata

- Project: superstep
- Task ID: TASK-0204
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0075, DEC-0009

## Objective

Fix the AI review findings 2, 8, 10 and 11 of the external review of v0.10.0 and v0.10.1: the judge saw only the first 12,000 characters of a request, a review lost to a restart left the step with nobody told, update_waiting could drop an event appended meanwhile on SQLite, and parallel reviews could pass the daily cap together.

## Scope

### In Scope

- a request longer than the judge sees goes to people (cause too_long)
- a review lost to a restart goes to people from the maintenance sweep (cause restart)
- update_waiting compares the events text when it appends one
- the daily cap is reserved atomically per workflow per UTC day
- docs en/vi

### Out Of Scope

- The other findings of the v0.10.0/v0.10.1 review; each group has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- A request longer than 12,000 characters is never judged and goes to people
- A lost review is sent to people once, the owner is told and the channel is asked
- An event appended between the read and the write of update_waiting is kept
- Parallel reviews cannot pass the daily cap; an escalated review gives its slot back

## Validation

- A regression test for each finding that fails before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the external review of v0.10.0 and v0.10.1.
- 2026-10-31: implemented on `factory/task-0204-ai-review-safety` from `develop`. A request longer than the judge's 12,000 characters goes to people (cause too_long); a step remembers its pending review (approval_waits.review, migration 0049) and the maintenance sweep sends a review lost to a restart to people (cause restart); update_waiting compares the events text when it appends; the daily cap is reserved atomically in approval_auto_quota and released when the review escalates. `factory verify run --profile full` passed. The owner asked to fix the confirmed review findings and merge each task when CI is green. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0193-task-0204.md`. QA: `.factory-state/artifacts/QA-0193-task-0204.md`.
