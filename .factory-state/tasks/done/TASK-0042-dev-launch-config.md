# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0042
- Status: done
- Phase: editor maintenance
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Requirement IDs:
- Design IDs:
- Architecture IDs:

## Objective

Track `.claude/launch.json`, the dev server configuration the Claude desktop app uses to start and preview the app.

## Scope

### In Scope

- `.claude/launch.json`: `backend` (uvicorn on :8000 with reload, the same command as `dev.sh`) and `frontend` (Vite on :5173)
- `roadmap.md`: TASK-0041 merged (PR #44)

### Out Of Scope

- Changes to `dev.sh`, ports, or application code

## Inputs

- Owner request on 2026-10-18: “commit file launch.json”

## Related Artifacts

- `dev.sh`

## Constraints

- One PR into `develop`. Do not merge until the owner asks.

## Dependencies

- None

## Acceptance Criteria

- Both configurations start their server from a fresh checkout that has `backend/.venv` and `frontend/node_modules` (the same prerequisites as `dev.sh`).

## Validation Plan

- Started both servers from this file in the Claude app on 2026-10-18; `/docs` on :8000 and `/api/health` through :5173 returned 200.
- `git diff --check`

## Assumptions

- Configuration only; no review or QA artifact.

## Open Questions

- None

## Activity Log

- 2026-10-18: The file was written in TASK-0041 to serve the app for the owner's testing. Owner asked to commit it. Branch `factory/task-0042-dev-launch-config` from `develop` (`4ee1ccd`). Not merged.

## Handoff Notes

- None.
- Backfilled 2026-10-24 (TASK-0093): Review none recorded at the time; QA none recorded at the time; develop verified retroactively by QA-0085.
