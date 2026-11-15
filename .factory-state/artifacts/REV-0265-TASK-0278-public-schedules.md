# Review

## Metadata

- Project: superstep
- Review ID: REV-0265
- Task ID: TASK-0278
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: approved for QA

## Review Scope

`factory/task-0278-public-schedules` against `origin/develop` at `f525620f`. The product diff is commit `b2d5f0ca`. It adds public schedule routes on the workflow-token API, regenerates the public OpenAPI spec at 1.2.0, and adds thin Python and TypeScript client methods. Studio JWT routes, the cron parser, and `ScheduleService.fire_due` are unchanged. Package versions are unchanged.

## Reference Artifacts

- TASK-0278
- DEC-0036
- `docs/backend-architecture.md`
- `docs/api-errors.md`

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- A workflow token can create schedules that run later as the token's owner. The owner asked for this. The handbook, the public spec, and the 2026-11-08 follow-up on DEC-0036 say so. `authenticate` still requires that owner to keep the share right.
- The public HTTP test covers a bad cron, a missing token, another workflow's token, and an unknown schedule. It does not create 21 schedules. `tests/test_schedules.py` covers the shared limit of 20, and both clients map `SCHEDULE_LIMIT` from a mocked response.
- Full backend pytest, frontend lint, frontend test, and frontend build were not re-run. This change does not edit the frontend. `factory verify` was not run through the x86_64 virtualenv.

## Standards And Architecture Alignment

- Routers call `ScheduleService`. No new error code. `SCHEDULE_NOT_FOUND`, `SCHEDULE_CRON_INVALID`, and `SCHEDULE_LIMIT` stay in the catalog.
- The public spec is generated from the `public` routes. Responses are envelope `$ref`s. Create returns 201 through `EnvelopeResponse`.
- Preview stays `POST` with `{cron, timezone}`, matching the Studio route from TASK-0046. The owner confirmed that shape. `cron` is the expression to evaluate. A saved schedule already returns `next_runs`.
- REQ-0082 is not marked done. The React Native package and the pending simulator screenshots are untouched.

## Design Alignment

- No new Studio screen. The existing schedules dialog still calls `POST /api/schedules/preview`.
- English and Vietnamese handbook pages list the five public schedule operations and the three schedule error codes.

## Validation Review

- Declared checks passed on this worktree before this review record. Evidence is in QA-0265.
- `factory verify` was not run through the x86_64 virtualenv.

## Assumptions

- The owner asked to finish this pull request, including review, QA, and Ready. That is not a merge approval and not a publish approval.

## Required Follow-Up

- None for this task. Simulator screenshots for TASK-0227 stay pending on their own branch.

## Review Decision

Approved for QA. No blocking findings.
