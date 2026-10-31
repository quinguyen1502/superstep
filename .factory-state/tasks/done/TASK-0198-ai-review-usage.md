# Task

## Metadata

- Project: superstep
- Task ID: TASK-0198
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0009, DEC-0010, DEC-0033

## Objective

Count AI auto-approval judge calls in usage. Every AI review judge call adds its tokens and cost to the run usage and telemetry, visible in the run trace. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- approval_review run event with usage
- run token/cost totals
- telemetry summarize
- trace tooltip en/vi
- handbook en/vi
- tests

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Auto-approved, escalated and invalid reviews count their usage
- A failed call counts nothing
- Usage shows in run totals, telemetry and the trace

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: implemented on `factory/task-0198-ai-review-usage` from `develop`. AI review judge usage is recorded as an approval_review event and added to the run tokens/cost; telemetry and the trace show it. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0186-task-0198.md`. QA: `.factory-state/artifacts/QA-0186-task-0198.md`.
