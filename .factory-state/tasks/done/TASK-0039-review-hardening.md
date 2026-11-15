# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0039
- Status: done
- Phase: review hardening
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Requirement IDs: REQ-0027
- Design IDs:
- Architecture IDs:

## Objective

Fix the defects and leftovers from the 2026-10-18 project review (REQ-0027).

## Scope

### In Scope

- `backend/app/core/net.py`: the address check and pinned request shared by webhooks, MCP, and the HTTP Tool node
- `backend/app/engine/nodes.py` HTTP Tool guard and `backend/app/engine/compiler.py` Condition matching
- Playwright specs under `frontend/e2e/`
- `project.md`, `roadmap.md`, REQ-0024 and REQ-0025 status
- Editor header badges at 1280px
- CORS config, access-log token redaction, `.gitignore` for the migration lock, `dev.sh`, `repositories/teams.py`, the `react(immutability)` warning, lazy routes

### Out Of Scope

- CI billing, the GitHub default branch, splitting `Editor.tsx`, and the 46 React hook oxlint warnings

## Inputs

- `.factory-state/artifacts/REQ-0027-review-hardening.md`

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0027-review-hardening.md`
- Architecture: `docs/backend-architecture.md`
- Errors: `docs/api-errors.md`
- QA of the review baseline: `.factory-state/artifacts/QA-0037-task-0038.md` (Playwright baseline on macOS)
- Review: `.factory-state/artifacts/REV-0038-task-0039.md`
- QA: `.factory-state/artifacts/QA-0038-task-0039.md`

## Expected Outputs

- Pytest for the HTTP Tool guard and Condition matching
- A green Playwright run on macOS apart from documented environment skips
- Updated README sections (nodes, configuration), `docs/api-errors.md`, locale files

## Constraints

- Engine imports only `core`. No new route, no schema change.
- Branch `factory/task-0039-review-hardening` from `develop` (`00d9a8e`). One PR into `develop`. Do not merge until the owner asks.
- Independent of TASK-0038 (PR #41); both edit `roadmap.md`.

## Dependencies

- None.

## Acceptance Criteria

- Same as REQ-0027.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && npx playwright test` (system Chrome via `PW_CHROME`, uvicorn via `E2E_UVICORN`)
- `git diff --check`

## Assumptions

- `factory ready` does not exit 0 here (the CLI needs `textual`). The owner asked for the work anyway.
- GitHub Actions does not run (billing, owner decision). Local checks are the evidence.

## Open Questions

- None

## Activity Log

- 2026-10-18: Owner asked to fix the review items after TASK-0038. REQ-0027 approved by that reply. Branch `factory/task-0039-review-hardening` from `develop` (`00d9a8e`). Task filed in `doing`.
- 2026-10-18: Implemented: `core/net.py` guard for HTTP Tool nodes, `pick_branch` for Conditions, configurable CORS, token redaction, editor header grid, lazy Editor/Settings routes, `ControlOrMeta` in Playwright, stale run-input selectors, records, `dev.sh`, `.gitignore`. The editor header at 1280px was a new finding from the Playwright run.
- 2026-10-18: Owner asked to resolve the remaining items. `backend/.venv` repaired. On Python 3.14 `test_cancel_queued_run_is_skipped` errored at teardown (nested TestClient); fixed. REV-0038 has no blocking findings. QA-0038 passed. Task set to done. PR into `develop`. Not merged.
- 2026-10-18: Owner asked to merge ("Merge it"). Rebased onto `develop` after PR #41; the editor header and roadmap conflicts were resolved (the header keeps #41's `EditorLayout` and this task's `minmax(min-content,1fr)` column). PR [#42](https://github.com/quinguyen1502/langgraph-studio/pull/42) merged into `develop`.

## Handoff Notes

- The Editor split is a separate follow-up.
