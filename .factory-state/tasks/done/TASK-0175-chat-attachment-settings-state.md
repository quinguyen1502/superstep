# Task

## Metadata

- Project: superstep
- Task ID: TASK-0175
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0077
- Design IDs: none
- Architecture IDs: DEC-0072

## Objective

Let a builder turn attachments on per chat, choose kinds, limits and the state field, and pass a sent message's files to the workflow as a list field.

## Scope

### In Scope

- Chat settings gain `attachments: {enabled, kinds: ['document','image'], max_files, max_mb, field}`; off by default; validated against the operator ceilings; `CHAT_SETTINGS_INVALID` for a bad field name.
- Sending a message (public WebSocket, studio Chat tab) accepts `attachment_ids`; the service checks they belong to the session and are unsent, links them to the turn and stores the ids in `chat_turns.attachments`.
- The run input sets the named field to a list of `{id, name, type, size, text?, text_cut?}`; image bytes never enter the state (DEC-0072 decision 2).
- Session JSON shows each turn's attachments (id, name, kind, size) for the page to render.
- Turning attachments off makes the API refuse uploads and sends with ids (`CHAT_ATTACHMENTS_OFF`).
- A Human node answer in the chat stays text only.

### Out Of Scope

- Model calls with images (TASK-0176).
- UI (TASK-0177).

## Inputs

- REQ-0077 'Allowing attachments' and 'How the workflow sees the files'; DEC-0072 decision 2.
- `services/chat_session_service.py`, `services/public_chat_service.py`, `schemas` for chat settings, `engine/state_schema.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0077-chat-attachments.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0072-chat-attachments.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0008-chat-attachments.md`

## Expected Outputs

- A run started from a chat message with files has the list in the configured field.

## Implementation Notes

- The field is a reserved list field in the workflow state schema; declare it like other chat input fields so the validator knows it.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0174.

## Acceptance Criteria

- With attachments on and field `files`, a message with a PDF and an image starts a run whose `files` lists both, the PDF with text.
- Ids from another session or already sent are refused.
- Settings above the operator ceiling are refused with a translated message.
- With attachments off, a send with ids is refused with `CHAT_ATTACHMENTS_OFF`.

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
- 2026-10-30: implemented on `factory/task-0175-chat-attachment-settings-state` from `develop`. Chat settings gain `attachments` (kinds, limits under the ceilings, list field); messages send `attachment_ids` on both sockets; the run gets file records without bytes; turns list their files; `CHAT_ATTACHMENT_LIMIT`. `factory verify run --profile full` passed. The owner authorized the merge of the REQ-0077/REQ-0078 task PRs. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0175-chat-attachment-settings-state` from `develop`.
- Review: `.factory-state/artifacts/REV-0151-task-0175.md`. QA: `.factory-state/artifacts/QA-0151-task-0175.md`.
