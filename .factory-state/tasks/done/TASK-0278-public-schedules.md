# Task

## Metadata

- Project: superstep
- Task ID: TASK-0278
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-08
- Updated: 2026-11-08
- Requirement IDs: owner request 2026-11-08
- Design IDs: none
- Architecture IDs: DEC-0036
- Phase: public API
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Expose workflow schedule management on the public OpenAPI, authenticated by the same workflow token that starts runs.

## Scope

### In Scope

- List, create, update, delete and preview schedules at `/api/hooks/workflows/{wid}/schedules`.
- Reuse `ScheduleService`. The token's owner is the schedule owner. `authenticate` already requires that owner to still have the share right.
- Public OpenAPI spec, English and Vietnamese handbook notes, and thin Python and TypeScript client methods.

### Out Of Scope

- A new cron syntax, a new error code, or a change to the Studio JWT routes.
- Publishing an SDK or bumping `@superstep/sdk` / `superstep` package versions.
- REQ-0082, the React Native package, and the pending simulator screenshots.

## Inputs

- DEC-0036, the existing Studio routes in `triggers.py`, and the public hook routes in `hooks.py`.

## Related Artifacts

- Decisions: `.factory-state/decisions/DEC-0036-scheduled-runs.md`
- Architecture: `docs/backend-architecture.md`
- Review: `.factory-state/artifacts/REV-0265-TASK-0278-public-schedules.md`
- QA: `.factory-state/artifacts/QA-0265-TASK-0278-public-schedules.md`

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Routers call services. No new error code. The public spec stays the source for the SDKs.
- A workflow token manages only its own workflow.

## Acceptance Criteria

- A workflow token can list, create, update, delete and preview schedules of its workflow.
- A token for another workflow, a missing token, and a bad cron expression fail with the existing catalog codes.
- `docs/api/openapi.public.json` matches the app, and the new operations are the only added public workflow routes.
- The Python and TypeScript clients call the new paths and map `SCHEDULE_NOT_FOUND`, `SCHEDULE_CRON_INVALID` and `SCHEDULE_LIMIT`.

## Validation Plan

- `backend/.venv/bin/python -m pytest tests/test_public_openapi.py tests/test_schedules.py tests/test_public_schedules.py`
- `sdk/python` pytest for the client, and `sdk/typescript` `npm test` plus `npm run gen:check`.

## Assumptions

- The owner asked to open this on the public API because callers may need it. That is not a release or publish approval.
- The schedule still runs as the token owner, through the existing worker.

## Open Questions

- None.

## Activity Log

- 2026-11-08: Owner asked to open schedule management on the public OpenAPI. Allocated TASK-0278 after `git fetch --all --prune`. Branch `factory/task-0278-public-schedules` from `origin/develop` at `f525620f`.
- 2026-11-08: Public routes on `hooks.py` reuse `ScheduleService`. Spec `1.2.0` regenerated. Python and TypeScript clients call the new paths and map `SCHEDULE_NOT_FOUND`, `SCHEDULE_CRON_INVALID`, and `SCHEDULE_LIMIT`. Handbook en/vi, Unreleased changelog, and a dated DEC-0036 follow-up. Backend pytest 25 passed (`test_public_openapi.py`, `test_public_schedules.py`, `test_schedules.py`) plus `test_layers.py`. Python SDK 27 passed. TypeScript SDK 106 passed, `gen:check` and `typecheck` passed.
- 2026-11-08: Owner asked to commit this branch. The task stayed in doing. No push and no pull request on that step.
- 2026-11-08: Owner asked to push, then to open the pull request. Draft PR #341 targets `develop`.
- 2026-11-08: Owner asked to finish the pull request. Review REV-0265 found no blocking issues. QA-0265 passed. Moved to done. REQ-0082 stays incomplete. No publish. Do not merge until the owner asks.

## Handoff Notes

- Branch `factory/task-0278-public-schedules`. Draft PR #341. Package versions stay unchanged.
- REQ-0082 stays incomplete. Simulator screenshots for TASK-0227 stay pending on their own branch.
- Do not merge until the owner asks.
