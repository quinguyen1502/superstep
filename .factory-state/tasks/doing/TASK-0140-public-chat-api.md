# Task

## Metadata

- Project: superstep
- Task ID: TASK-0140
- Status: doing
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067, DEC-0052, DEC-0053, DEC-0009

## Objective

Let a web chat be published and give it a public REST API by slug. This covers the publish settings, the visitor
identity for `anonymous` and `signed_in`, the visitor's own sessions, the limits and the new error codes. Messages do
not stream yet; that is TASK-0141.

## Scope

### In Scope

- `chat_session_service._check` (DEC-0067, decisions 1 and 9):
  - `access` accepts `anonymous` and `signed_in`;
  - slug rules and uniqueness among web chats, with `CHAT_SLUG_INVALID` and `CHAT_SLUG_TAKEN`;
  - the new keys `title`, `intro`, `suggestions`, `daily_limit` and `embed_origins`, the last checked with
    `CHAT_EMBED_ORIGIN_INVALID`;
  - publishing refused in demo mode.
- `services/public_chat_service.py` and `api/routes/public_chat.py` (decision 2):
  - `GET /api/public/chat/{slug}`;
  - list, read and create sessions;
  - `GET /api/public/chat/{slug}/frame`, which returns the frame header for TASK-0143;
  - `CHAT_NOT_PUBLISHED` when the chat is not published.
- Visitor identity (decision 3):
  - a signed visitor token, with HMAC over the studio secret;
  - the HttpOnly cookie with its path and its SameSite or Partitioned flags;
  - the `X-Chat-Visitor` header;
  - for `signed_in`, the studio user, or `CHAT_SIGN_IN_REQUIRED`.
- Limits on session creation and reads per IP. The settings for the message limits in decision 5 go in
  `core/config.py`.
- A migration only if the slug uniqueness needs an index that does not exist yet.
- New error codes in `core/errors.py`, `docs/api-errors.md`, `en.json` and `vi.json`.
- Tests: `backend/tests/test_public_chat_api.py`.

### Out Of Scope

- The public socket, running messages and the visitors list (TASK-0141).
- The page and the settings UI (TASK-0142).
- Frame headers and the embed (TASK-0143).

## Inputs

- REQ-0074, DEC-0067 and CLAR-0005.
- `services/chat_session_service.py`, `repositories/chat_sessions.py`, `repositories/chat_triggers.py`,
  `services/rate_limit.py`, `core/security.py`, `api/deps.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md`
- Decisions: `DEC-0052-web-chat-model.md`, `DEC-0053-chat-access-and-steps.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md`

## Expected Outputs

- A published chat answers `GET /api/public/chat/{slug}` without a studio session.
- A visitor gets a token and can only see their own sessions.

## Implementation Notes

- The public service reads the trigger by slug and uses the workflow's owner as the acting user for every
  repository call. It never calls `_workflow(wid, uid, P.RUN)` with the visitor.
- Compare tokens in constant time. A bad or foreign token is treated as no token, and a new one is issued.

## Constraints

- Layers (DEC-0009): no FastAPI in services.
- Use the envelope and the central error handlers.
- `tests/test_layers.py` and `tests/test_api_envelope.py` must pass.

## Dependencies

- None. Based on develop.

## Acceptance Criteria

- An unpublished chat (disabled, or `studio`) returns `CHAT_NOT_PUBLISHED`, and the response says nothing about the
  workflow.
- Two anonymous clients each see only their own sessions. A forged token or another visitor's session id returns
  not found.
- `signed_in` with no session returns `CHAT_SIGN_IN_REQUIRED`. A signed-in user without the run right can create a
  session, and its `owner` is that user.
- The slug and settings checks give each error code. A duplicate slug gives `CHAT_SLUG_TAKEN`.
- The cookie has HttpOnly, the slug path and the SameSite flags of DEC-0067 decision 3.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx vitest run`, for the locale keys

## Assumptions

- The studio secret (`security`) is stable across restarts, as it already is for sessions.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0074 after the owner answered CLAR-0005.

## Handoff Notes

- TASK-0141 adds the socket on top of `PublicChatService`.
