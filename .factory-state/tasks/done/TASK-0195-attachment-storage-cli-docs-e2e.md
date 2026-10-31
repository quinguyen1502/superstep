# Task

## Metadata

- Project: superstep
- Task ID: TASK-0195
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

CLI install prompts, doctor, handbook and e2e. Operators choose the backend at install time and can check it; docs in en and vi.

## Scope

### In Scope

- `superstep install` and `deploy` ask "Where should chat attachments be stored?" (database, folder, S3-compatible): `fs` is offered for single-host installs and `s3` for the full stack; `db` stays the default. Flags `--attachment-storage` and the S3 flags for `--yes`; S3 secrets to `.env` with mode 600, never printed.
- The Render demo stays on `db`.
- `superstep doctor` reports the backend and the probe result.
- Handbook en and vi: Configuration, Operate: Backup, Chat: Attachments (backends, R2/B2/MinIO notes, migration, backup).
- Playwright e2e in en and vi: upload and download on `fs` (and `db`); CHANGELOG.

### Out Of Scope

- New backends.

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

- TASK-0194

## Acceptance Criteria

- `superstep install --yes --attachment-storage s3 ...` writes the settings; `fs` and `db` likewise.
- `doctor` shows the backend and reports a failing folder or bucket clearly, without secrets.
- Handbook pages in en and vi build strictly; e2e passes in en and vi.

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

- 2026-10-30: implemented on `factory/task-0195-attachment-storage-cli-docs-e2e` from `develop`. Adds the storage question and flags to `superstep install`/`deploy`, the attachment line in `doctor`, compose env passthrough in generated instances, an `install.sh` hint, handbook en/vi, and the Playwright spec `attachment-storage.spec.ts` (en and vi, run on db and fs). `factory verify run --profile full` passed. The owner authorized merging the REQ-0080 task PRs when CI is green. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0195-attachment-storage-cli-docs-e2e` from `develop`.
- Review: `.factory-state/artifacts/REV-0184-task-0195.md`. QA: `.factory-state/artifacts/QA-0184-task-0195.md`.
