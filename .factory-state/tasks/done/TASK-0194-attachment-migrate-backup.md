# Task

## Metadata

- Project: superstep
- Task ID: TASK-0194
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

Migrate command and backup/restore. Move existing files between backends and cover them in backup and restore.

## Scope

### In Scope

- Admin service and endpoint plus `superstep attachments migrate --to db|fs|s3 [--dry-run] [--batch N]`: copy, verify size and SHA-256, switch the row, delete the source; resumable in batches; safe to run twice.
- Backup: `db` unchanged; `fs` adds `attachments/` to the archive; `s3` writes bucket and prefix to the manifest, and `--include-attachments` copies the objects into the archive.
- Restore refuses a manifest whose backend does not match the target's configuration unless `--force`; for `s3` it warns that objects are not in the archive unless they were included.

### Out Of Scope

- Install prompts (TASK-0195).

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

- TASK-0192
- TASK-0193

## Acceptance Criteria

- Migration moves rows both ways between all three backends, checks checksums, resumes after an interruption and is a no-op the second time.
- Backup and restore round-trip for `db` and `fs`; for `s3` the manifest records bucket and prefix, and `--include-attachments` round-trips the objects.
- A mismatched restore is refused without `--force`.

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

- 2026-10-30: implemented on `factory/task-0194-attachment-migrate-backup` from `develop`. Adds `AttachmentMigration` (copy, verify size and SHA-256, switch the row, delete the old copy), `AttachmentArchive` (tar export/import of external files), the admin route `/api/admin/attachments`, `app.admin_cmd attachments-*`, `superstep attachments migrate`, attachments in backup/restore with the backend check, errors in the envelope, handbook en/vi. `factory verify run --profile full` passed. The owner authorized merging the REQ-0080 task PRs when CI is green. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0194-attachment-migrate-backup` from `develop`.
- Review: `.factory-state/artifacts/REV-0183-task-0194.md`. QA: `.factory-state/artifacts/QA-0183-task-0194.md`.
