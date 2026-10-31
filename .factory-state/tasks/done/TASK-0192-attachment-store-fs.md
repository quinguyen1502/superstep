# Task

## Metadata

- Project: superstep
- Task ID: TASK-0192
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

The `fs` backend. A folder backend for single-host installs and shared volumes.

## Scope

### In Scope

- `fs` backend under `STUDIO_ATTACHMENT_FS_PATH` (default `/data/attachments`); random keys `<workflow>/<session>/<attachment id>`, never the file name; path traversal refused.
- Atomic writes (temp file then rename); streaming reads.
- Health detail and a write/read/delete probe for `/api/health`.
- Docker: the all-in-one image uses the data volume; the full stack mounts one named volume on `api` and `worker`.

### Out Of Scope

- CLI prompts and handbook (TASK-0195).

## Inputs

- REQ-0080 and DEC-0074 (Accepted 2026-10-31, owner decisions recorded there).
- `backend/app/services/chat_attachment_service.py`, `backend/app/repositories`, the CLI under `sdk/python/src/superstep/cli/`, `scripts/install.sh`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0080-attachment-storage.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0074-attachment-storage.md`
- Decisions: `DEC-0072` (chat attachments), `DEC-0009`, `DEC-0010`, `DEC-0068` and `DEC-0071` (CLI), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested; handbook and CHANGELOG where the behaviour is user-visible.

## Implementation Notes

- Keep the backends small; no general storage library (DEC-0074, alternatives).

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code in `core/errors.py` CATALOG, `docs/api-errors.md`, and both locales. `tests/test_api_envelope.py` passes.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No secret is logged or printed; S3 keys only in `.env` (mode 600).

## Dependencies

- TASK-0191

## Acceptance Criteria

- The `fs` backend passes the contract suite on a temp folder.
- With `STUDIO_ATTACHMENT_STORAGE=fs`, new uploads land in the folder and old `db` rows still download.
- A key cannot escape the root folder.
- The health probe reports a missing or read-only folder clearly; the worker's probe detects a non-shared volume.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run lint && npm test && npm run build` when the UI changes
- `factory verify run --profile full`, `factory validate`

## Assumptions

- The designer step is skipped; REQ-0080 and DEC-0074 describe the behaviour.

## Open Questions

- None. DEC-0074 is accepted.

## Activity Log

- 2026-10-31: planned from REQ-0080 (DEC-0074, accepted by the owner). Status todo. Not started.

- 2026-10-30: implemented on `factory/task-0192-attachment-store-fs` from `develop`. Adds the `fs` backend (`app/storage/fs.py`): atomic writes, key confinement, streamed reads, a worker heartbeat and health fields; compose, `.env.example` and handbook en/vi updated. `factory verify run --profile full` passed. The owner authorized merging the REQ-0080 task PRs when CI is green. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0192-attachment-store-fs` from `develop`.
- Review: `.factory-state/artifacts/REV-0181-task-0192.md`. QA: `.factory-state/artifacts/QA-0181-task-0192.md`.
