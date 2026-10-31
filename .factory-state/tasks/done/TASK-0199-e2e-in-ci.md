# Task

## Metadata

- Project: superstep
- Task ID: TASK-0199
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0001
- Design IDs: none
- Architecture IDs: DEC-0033, DEC-0008

## Objective

Run the Playwright e2e suite in CI. Every PR to develop runs the full e2e suite (en and vi) in CI, sharded, with cached browsers and failure artifacts, and no retries. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- ci.yml e2e job with 3 shards
- browser cache
- trace and screenshot upload on failure
- 30 min timeout
- subprocess Code runtime
- handbook en/vi development page
- CHANGELOG

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- The e2e job runs on every PR to develop and passes
- Failures upload traces and screenshots
- No retries
- flaky tests fixed at the cause

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: implemented on `factory/task-0199-e2e-in-ci` from `develop`. CI e2e job: 3 shards, cached Chromium, subprocess Code runtime, traces/screenshots on failure, 30 min timeout, no retries. Not made a required check: develop has no branch protection; the merge rule (all CI green) already gates it. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0187-task-0199.md`. QA: `.factory-state/artifacts/QA-0187-task-0199.md`.
