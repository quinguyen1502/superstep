# Task

## Metadata

- Project: superstep
- Task ID: TASK-0168
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

A builder can keep a folder of workflow JSON in Git: `pull` writes it, `push` updates the studio, and a studio edit made after the pull is not overwritten unless `--force` is set.

## Scope

### In Scope

- DEC-0071 decision 4.
- `version` on `GET /api/workflows` and on `GET /api/workflows/{id}`. `updated` on the single-workflow GET. Both are response fields, not stored in the graph.
- CLI commands `workflows list`, `workflows export`, `workflows import`, `pull` and `push`, using the token from TASK-0167.
- CLI error codes `WORKFLOW_CHANGED`, `WRONG_SERVER`, `AMBIGUOUS`, `NOT_A_WORKFLOW` and `SERVER_TOO_OLD` in the CLI catalogs only.

### Out Of Scope

- Deleting a remote workflow that is missing locally, or a local file that is missing on the server.
- Importing Python, TypeScript or a LangGraph zip.
- `run`, `test` and `mcp`.
- A new server route for export or import. Use the routes that already exist.

## Inputs

- REQ-0079 group C (list, export, import, pull, push).
- DEC-0071 decision 4.
- `backend/app/services/workflow_service.py` (`get`, `list`, `save`, `READ_ONLY`), `backend/app/engine/exporters.py`, `sdk/python/src/superstep/cli/`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: `DEC-0068-superstep-cli.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`
- Exports: `.factory-state/artifacts/REQ-0043-python-export.md`, `.factory-state/artifacts/REQ-0047-typescript-export.md`, `.factory-state/artifacts/REQ-0053-langgraph-project-export.md`

## Expected Outputs

- A directory of `<id>.json` files plus `.superstep/lock.json` format 1.
- `push` that changes nothing when the server version moved, and a `--force` push that updates the studio and the lock.

## Implementation Notes

- Strip `access`, `mine`, `owner_email`, `version` and `updated` before writing a workflow file and before `POST`.
- Compare every file with the server before the first `POST`. The first conflict aborts the whole push.
- Resolve a name with `GET /api/workflows`. Exact name match. Zero matches is the server's not-found code. Two matches is `AMBIGUOUS`.
- `SERVER_TOO_OLD` when the workflow route the command needs answers 404. Print `data.version` from `/api/health` in that message.
- Tests use httpx mocks or the backend TestClient. They do not need Docker.

## Constraints

- No new dependency. Python >= 3.9. argparse.
- The version field is additive. Existing clients that ignore unknown JSON fields keep working.
- CLI catalogs stay key-identical across en and vi.

## Dependencies

- TASK-0167 merged into `develop`. The shared token file and the HTTP helper land there. Do not stack.

## Acceptance Criteria

- `pull` writes one JSON file per visible workflow and a lock whose `version` matches the server. A second pull updates a file whose version changed and leaves a local-only file in place.
- `push` of an unchanged folder exits 0 and does not create a new version. After the server version moves, `push` exits non-zero, writes no workflow, and `--force` then saves and refreshes the lock.
- A lock whose `url` is a different origin is `WRONG_SERVER` unless `--force`.
- `export --format json` matches the pull file. `python` and `typescript` match the export routes. `langgraph` is a zip. `import` of JSON creates a workflow. `import` of a `.py` file is `NOT_A_WORKFLOW` and does not call the server.
- Two workflows named `Support` make `export Support` exit `AMBIGUOUS`.
- `--help` on each command includes an example. `--json` is one object on stdout.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q` for the workflow GET fields, with the envelope tests if the payload changed.
- `cd sdk/python && python -m pytest -q` for pull, push, export and import.

## Assumptions

- The designer step is skipped. These commands have no new screen.
- "Changed in the studio" means the latest version number, not the `updated` clock.
- Push of a brand-new file is not a conflict.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071). Not started.
- 2026-10-30: implementation started.

- 2026-10-30: owner asked to finish the phase 2 chain in one pass. Review REV-0144. QA QA-0144. Task moved to done. Not merged.

## Handoff Notes

- TASK-0167 is merged. Review REV-0144. QA QA-0144. Not merged. TASK-0169, TASK-0170 and TASK-0171 are separate branches.
