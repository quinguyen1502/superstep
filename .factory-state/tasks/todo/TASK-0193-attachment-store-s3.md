# Task

## Metadata

- Project: superstep
- Task ID: TASK-0193
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

The `s3` backend with a MinIO CI test. S3-compatible object storage (AWS S3, R2, B2, MinIO) through `boto3` as an optional extra.

## Scope

### In Scope

- `s3` backend with `STUDIO_ATTACHMENT_S3_BUCKET`, `_ENDPOINT` (empty for AWS), `_REGION` (`auto` for R2), `_PREFIX`, `_ACCESS_KEY_ID`, `_SECRET_ACCESS_KEY` (or the default credential chain), `_PATH_STYLE`.
- `boto3` in an optional extra (`superstep-backend[s3]`) installed in the published images; the backend fails with a clear error when the extra is missing.
- Streaming upload (multipart above a threshold) and streaming download through the backend; no presigned URLs, no bucket URL in the page.
- Health probe (write, read, delete); errors never include the keys.
- CI job running the contract suite against a MinIO service container.

### Out Of Scope

- Presigned uploads or downloads (DEC-0074 decision 3).
- Azure Blob and GCS native APIs.

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

- The `s3` backend passes the contract suite against MinIO in CI.
- Downloads stream through the backend with the same headers and owner check; another visitor gets 404.
- A missing extra, wrong bucket or bad credentials give a clear error in the health probe without printing secrets.
- `db` and `fs` installs need no new dependency.

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

## Handoff Notes

- Branch `factory/task-0193-attachment-store-s3` from `develop`.
