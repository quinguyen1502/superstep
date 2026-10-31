# Task

## Metadata

- Project: superstep
- Task ID: TASK-0205
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0076, DEC-0071, DEC-0009

## Objective

Fix the CLI sign-in findings 4, 6 and 12 of the external review of v0.10.0 and v0.10.1: the CLI sent its saved token to any --url, the browser sign-in could be phished with a link holding the code (and its start was unlimited and never cleaned), and PatService.user_for_token was dead code while last_used was written on every request.

## Scope

### In Scope

- saved token sent only to the issuing server
- sign-in link without the code; the page asks for the typed code with a warning
- rate limit on POST /api/auth/cli/devices and removal of old sign-ins
- remove PatService.user_for_token; throttle last_used
- DEC-0076; docs en/vi

### Out Of Scope

- The other findings of the v0.10.0/v0.10.1 review; each group has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- The saved token is not sent to another server
- A code in the link is not used; the person types it
- Sign-in starts are limited per client IP and old ones are removed
- last_used is written at most every 5 minutes and the dead code is gone

## Validation

- A regression test for each finding that fails before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the external review of v0.10.0 and v0.10.1.
- 2026-10-31: implemented on `factory/task-0205-cli-auth-safety` from `develop`. The CLI sends its saved token only to the server that issued it; the sign-in link no longer carries the code and /cli/authorize asks for the typed code with a warning; POST /api/auth/cli/devices is limited to 10 per client IP per 10 minutes and old sign-ins are removed; PatService.user_for_token is removed and last_used is written at most every 5 minutes. `factory verify run --profile full` passed. The owner asked to fix the confirmed review findings and merge each task when CI is green. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0192-task-0205.md`. QA: `.factory-state/artifacts/QA-0192-task-0205.md`.
