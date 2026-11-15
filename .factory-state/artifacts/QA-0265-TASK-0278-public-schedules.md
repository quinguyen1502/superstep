# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0265
- Task ID: TASK-0278
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: pass

## Validation Scope

TASK-0278 public schedule routes, the committed public OpenAPI spec 1.2.0, and the Python and TypeScript client methods. Review is REV-0265. The product tree reviewed is commit `b2d5f0ca` on `factory/task-0278-public-schedules` against `origin/develop` `f525620f`. Finish-pr adds this record, the review, and the done move. It does not change the API source.

## Acceptance Criteria Coverage

- Criterion: A workflow token can list, create, update, delete, and preview schedules of its workflow.
  - Result: pass
  - Evidence: `backend/tests/test_public_schedules.py` creates a weekday schedule, reads it back through the Studio JWT list, turns it off, previews `@daily`, and deletes it. `tests/test_public_openapi.py` checks the 201 body and the preview body against the documented models.
- Criterion: A token for another workflow, a missing token, and a bad cron expression fail with the existing catalog codes.
  - Result: pass
  - Evidence: `tests/test_public_schedules.py` expects `401 TRIGGER_TOKEN_INVALID` for a missing token and for another workflow's token, `400 SCHEDULE_CRON_INVALID` for `61 * * * *`, and `404 SCHEDULE_NOT_FOUND` for an unknown id.
- Criterion: `docs/api/openapi.public.json` matches the app, and the new operations are the only added public workflow routes.
  - Result: pass
  - Evidence: `tests/test_public_openapi.py::test_committed_public_spec_matches_the_app` and `test_public_spec_has_only_the_public_routes`. `PUBLIC_OPS` is the two run routes plus `listSchedules`, `createSchedule`, `previewSchedule`, `updateSchedule`, and `deleteSchedule`.
- Criterion: The Python and TypeScript clients call the new paths and map `SCHEDULE_NOT_FOUND`, `SCHEDULE_CRON_INVALID`, and `SCHEDULE_LIMIT`.
  - Result: pass
  - Evidence: `sdk/python/tests/test_client.py`, `sdk/python/tests/test_async.py`, and `sdk/typescript/test/client.test.ts`. `sdk/python/tests/test_spec_sync.py` and `sdk/typescript/test/package.test.ts` require every documented error example code to be in `BY_CODE`.

## UX And Accessibility Coverage

- Criterion: Studio schedule dialog.
  - Result: pass by inspection
  - Evidence: `frontend/src/components/schedules-dialog.tsx` is unchanged and still calls `POST /api/schedules/preview`. No new screen, colour, or confirmation dialog.

## Checks Performed

- `backend`: `pytest tests/test_public_openapi.py tests/test_schedules.py tests/test_public_schedules.py tests/test_layers.py`. 26 passed. The main-checkout virtualenv was used with `PYTHONPATH` set to this worktree.
- `sdk/python`: `pytest`. 234 passed, 8 skipped. The same `PYTHONPATH` pattern was used.
- `sdk/typescript`: `npm test` (106 passed), `npm run gen:check`, `npm run typecheck`, and `npm run build`. Exit 0 on arm64 Node 22.12.0.

## Defects

- None.

## Gaps Or Untested Areas

- Full backend pytest, frontend lint, frontend test, and frontend build were not re-run. This change does not edit the frontend.
- The public HTTP test does not create 21 schedules. The shared limit test in `tests/test_schedules.py` does.
- `factory verify` was not run through the x86_64 virtualenv.

## Residual Risk

- A schedule created with a workflow token runs as that token's owner when a worker is running. With `STUDIO_WORKER=0` on every process, stored schedules do not fire. That worker rule already existed.

## Assumptions

- Opening the public API is not a release or publish approval. Package versions stay unchanged.

## Required Follow-Up

- None for this task. Simulator screenshots for TASK-0227 stay pending on their own branch.

## QA Decision

Passed to done.
