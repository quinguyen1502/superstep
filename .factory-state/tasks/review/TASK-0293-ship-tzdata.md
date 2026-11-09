# Task

## Metadata

- Project: superstep
- Task ID: TASK-0293
- Title: Ship Python tzdata so schedule time zones resolve
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: XS

## Objective

Make every IANA zone a browser can report (for example `Asia/Saigon`) resolve on the server, so the schedule dialog does not reject it on images without system zone data.

## Scope

### In Scope

- Add `tzdata` to the backend dependencies (`backend/pyproject.toml` and `backend/requirements.txt`) so `zoneinfo` falls back to it.
- Test: `services/cron.zone("Asia/Saigon")` resolves with system zone data hidden (for example `PYTHONTZPATH` pointed at an empty directory).

### Out Of Scope

- Changing how the frontend picks the default zone; migrating existing schedules.

## Dependencies

- None; independent of the other tasks.

## Acceptance Criteria

- `Asia/Saigon` and `Asia/Ho_Chi_Minh` resolve in the backend image and in the slim test environment.
- Schedule creation with `Asia/Saigon` succeeds end to end.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
- 2026-11-09: Shipped with TASK-0284 on `factory/task-0284-readiness-tzdata`. `tzdata` added to `backend/pyproject.toml` and `backend/requirements.txt`; the Dockerfiles install the backend package, so the image gets it. Test: `cron.zone` resolves `Asia/Saigon` and `Asia/Ho_Chi_Minh` in a subprocess with `PYTHONTZPATH` pointed at an empty directory.
- 2026-11-09: Review REV-0270 and QA-0270. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0270-TASK-0293-ship-tzdata.md`
- QA: `.factory-state/artifacts/QA-0270-TASK-0293-ship-tzdata.md`
