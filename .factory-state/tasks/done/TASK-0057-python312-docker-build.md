# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0057
- Status: done
- Phase: release
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: none (a fix to the build, no behaviour change)
- Design IDs: none
- Architecture IDs: DEC-0009

## Objective

Make `develop` releasable again: the backend imports on Python 3.12 (the version of `backend/Dockerfile` and CI), and the
web Docker image builds.

## Scope

### In Scope

- `services/schedule_service.py`: `fire_due` is annotated `list[str]` inside a class that defines a `list` method. Python
  3.12 evaluates the annotation at class creation, finds the method, and raises `TypeError: 'function' object is not
  subscriptable`, so `app.main` cannot be imported. Use `typing.List[str]` there.
- `frontend/tsconfig.app.json`: exclude test files from the app type-check. `state-refs.test.ts` imports
  `backend/tests/fixtures/template_refs.json`, which is outside the web image's build context (`./frontend`), so
  `npm run build` failed in Docker. Vitest still runs the tests.

### Out Of Scope

- Any change in behaviour, API or UI.

## Inputs

- CI on `develop` since PR #63 and #64: Backend (pytest, Python 3.12), Backend (pytest on Postgres 17 + Redis 7) and
  docker compose build + smoke fail; Factory verification fails on the same pytest run.

## Related Artifacts

- Requirements: none
- Design: none
- Architecture: `docs/backend-architecture.md` (DEC-0009)
- Decisions: none
- Discovery: local runs used Python 3.14, which evaluates annotations lazily, so the error did not show.
- Clarifications: none

## Expected Outputs

- The two edits above, and green CI on the pull request.

## Implementation Notes

- A comment above `fire_due` says why it uses `typing.List`.

## Constraints

- No new dependencies; layers unchanged.

## Dependencies

- None.

## Acceptance Criteria

- `python -c "import app.main"` works on Python 3.12.
- `python -m pytest -q` passes on Python 3.12 (local: 480 passed, 10 skipped).
- `npm run build`, `npm test` and `npm run lint` pass in `frontend/`.
- `docker compose build web api` succeeds (checked locally); the CI smoke job passes.

## Validation

- Python 3.12 venv: import and the full pytest suite, as above.
- `docker compose build web api` with Docker 28.3.3: both images built.
- CI on PR #66: all six checks pass (both backend jobs, both frontend builds, compose build + smoke, factory verify). Merged in PR #66.

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review none recorded at the time; QA none recorded at the time; develop verified retroactively by QA-0085.
