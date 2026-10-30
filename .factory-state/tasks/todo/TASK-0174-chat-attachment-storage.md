# Task

## Metadata

- Project: superstep
- Task ID: TASK-0174
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0077
- Design IDs: none
- Architecture IDs: DEC-0072

## Objective

Store chat attachments in the database and expose upload and download routes for the public chat and the studio Chat tab, with type checks from the bytes, size and count limits, isolation per session, and retention.

## Scope

### In Scope

- Model and Alembic revision `chat_attachments` (DEC-0072 decision 1): `id`, `session_id`, `turn_id` (null until the message is sent), `name`, `kind` (`document`|`image`), `mime`, `size`, `data` (bytes), `text` (extracted, capped), `text_cut`, `created`.
- Repository `chat_attachments.py`; service `chat_attachment_service.py`: magic-byte detection for PDF, PNG, JPEG, WebP, and UTF-8 text for `.txt`, `.md`, `.csv` (as the chat logo check does).
- Limits: per-file size and per-message count from the chat settings (TASK-0175 adds the settings; this task reads defaults 10 MB / 5 files) under the operator ceilings `STUDIO_CHAT_ATTACHMENT_MAX_MB` and `STUDIO_CHAT_ATTACHMENT_MAX_FILES`. `limit_body` bounds the request.
- Routes: `POST /api/public/chat/{slug}/sessions/{sid}/attachments` (multipart, one file), `GET .../attachments/{aid}` (download), `DELETE .../attachments/{aid}` (only while unsent); the same under `/api/chat/sessions/{sid}/attachments` for the studio; builder download from the Visitors list route.
- Downloads always `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, never inline.
- Text extraction reuses `engine/documents.py` (adds `.csv` as text), capped at 50,000 characters with `text_cut`.
- Retention and session/workflow delete remove the files; unsent uploads older than one hour are swept by the existing retention job.
- Upload counts as a message for the REQ-0074 visitor rate limit. Refused in demo mode.
- Error codes: `CHAT_ATTACHMENTS_OFF`, `CHAT_ATTACHMENT_TYPE`, `CHAT_ATTACHMENT_TOO_LARGE`, `CHAT_ATTACHMENT_TOO_MANY`, `CHAT_ATTACHMENT_NOT_FOUND`, `CHAT_ATTACHMENT_DEMO`.

### Out Of Scope

- Chat settings UI and the workflow state field (TASK-0175).
- Model image parts (TASK-0176).
- Composer UI (TASK-0177).
- Slack and Telegram files.
- OCR, virus scanning, Office files.

## Inputs

- REQ-0077 scope 'Storage', 'The type', 'Limits'; DEC-0072 decisions 1 to 3.
- `backend/app/models/chat_session.py`, `chat_logos` handling (TASK-0145), `engine/documents.py`, `services/public_chat_service.py`, `services/rate_limit.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0077-chat-attachments.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0072-chat-attachments.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0008-chat-attachments.md`

## Expected Outputs

- Upload, download and delete work for a visitor and a studio user.
- The table has no orphan rows after retention.

## Implementation Notes

- Store the bytes in a separate table, not in `chat_turns`, so listing turns never loads files. `chat_turns.attachments` keeps only the list of ids.
- Never trust the filename or the browser type for the kind.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- None. Based on `develop` (DEC-0033).

## Acceptance Criteria

- A PDF and a PNG upload succeed; a `.pdf` whose bytes are not a PDF is refused with `CHAT_ATTACHMENT_TYPE`.
- An 11 MB file is refused with `CHAT_ATTACHMENT_TOO_LARGE` without reading past the limit; a sixth file for one message is refused with `CHAT_ATTACHMENT_TOO_MANY`.
- A second visitor and a guessed id both get `CHAT_ATTACHMENT_NOT_FOUND`.
- Downloads carry `attachment` disposition and `nosniff`.
- Retention removes the session's files and stale unsent uploads.
- Demo mode refuses uploads.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py tests/test_api_envelope.py`

## Assumptions

- The designer step is skipped. REQ-0077 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0072 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0077 (DEC-0072). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.

## Handoff Notes

- Branch `factory/task-0174-chat-attachment-storage` from `develop`.
