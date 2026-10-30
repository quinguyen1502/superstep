# Task

## Metadata

- Project: superstep
- Task ID: TASK-0191
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

Storage port and the `db` backend. Introduce the `AttachmentStore` port and move today's in-database bytes behind it as the `db` backend, with rows saying where their bytes are.

## Scope

### In Scope

- `AttachmentStore` port: `put(key, stream, size, mime)`, `open(key)` (stream), `delete(key)`, `exists(key)`, `iter_keys()`; a factory from `STUDIO_ATTACHMENT_STORAGE` (default `db`).
- `db` backend over `chat_attachments.data`; the attachment service depends only on the port; repositories keep metadata.
- Migration: columns `storage` (`db`, `fs`, `s3`) and `key` on `chat_attachments`; existing rows become `storage=db`.
- Write order: object first, then row; a failed row write deletes the object. Retention, the unsent sweeper and session delete remove the object after the row. Orphan sweep (objects without a row, older than one hour).
- Upload size check and streaming in chunks; downloads keep owner-only access and the DEC-0072 headers.
- A shared contract test suite every backend must pass.

### Out Of Scope

- Other binary data (logos, knowledge documents).
- `fs` and `s3` backends (TASK-0192, TASK-0193).

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

- none (first task)

## Acceptance Criteria

- With no new setting, uploads, downloads, retention and the sweeper behave exactly as today (existing tests pass).
- The `db` backend passes the contract suite; reads use each row's `storage`/`key`.
- A failed row write leaves no object; the orphan sweep removes objects without rows older than one hour.
- Owner-only downloads and headers unchanged (`attachment`, `nosniff`, `no-store`, CSP sandbox).

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

- Branch `factory/task-0191-attachment-store-port` from `develop`.
