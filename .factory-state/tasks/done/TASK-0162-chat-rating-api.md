# Task

## Metadata

- Project: superstep
- Task ID: TASK-0162
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0075
- Design IDs: none
- Architecture IDs: DEC-0070, DEC-0009, DEC-0067

## Objective

Store one thumbs up or thumbs down per chat answer, and expose it on the public API and the studio API. The page and
the Chat tab are later tasks.

## Scope

### In Scope

- Migration `0042_chat_ratings` and `ChatRating` (DEC-0070 decision 1).
- `PUT` and `DELETE` for a rating on the public chat API and on `/api/chat/sessions/{sid}/turns/{tid}/rating`.
- Session reads include `rating` and, on assistant turns, `run_exists`.
- `GET /api/workflows/{wid}/chat/visitors?thumbs_down=1` and `thumbs_down` on each row.
- `GET /api/workflows/{wid}/chat/ratings` with `d7` and `d30` counts.
- Retention and the other session deletes remove ratings in the same transaction.
- Error codes in `core/errors.py`, `docs/api-errors.md`, and both locales.
- pytest: own visitor only, one row, waiting turns refused, unpublished chat refuses a new rating, retention.

### Out Of Scope

- The thumbs in the UI (TASK-0163, TASK-0164).
- The LangSmith job (TASK-0165). The column `feedback_id` is created here and left empty.
- Handbook (TASK-0166).

## Inputs

- REQ-0075, DEC-0070, CLAR-0006.
- `models/chat_session.py`, `repositories/chat_sessions.py`, `services/chat_session_service.py`,
  `services/public_chat_service.py`, `api/routes/public_chat.py`, `api/routes/chat_sessions.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- Decisions: `DEC-0067-public-chat-page.md`, `DEC-0052-web-chat-model.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`

## Expected Outputs

- A visitor can rate their own finished answer and see that rating on the next read.
- Another visitor cannot rate or read it.

## Implementation Notes

- Upsert on `turn_id`. The public route uses `PublicChatService.published` and `own`, then one method on
  `ChatSessionService`.
- A comment omitted on `down` stores `""`. A comment with `up` is `CHAT_RATING_INVALID`.

## Constraints

- Layers (DEC-0009): no FastAPI in services.
- Envelope and the central error handlers.
- `tests/test_layers.py` and `tests/test_api_envelope.py` must pass.

## Dependencies

- None. Based on develop.

## Acceptance Criteria

- A visitor rates an answer up, then down with a comment. Reading the session returns that one rating.
- A second visitor, and a guessed turn id, get `CHAT_TURN_NOT_FOUND` or `CHAT_SESSION_NOT_FOUND`, and no rating body.
- A waiting turn returns `CHAT_RATING_NOT_ALLOWED`. The later final answer of that run can be rated.
- After the chat is unpublished, a new rating returns `CHAT_NOT_PUBLISHED` and the stored rating is still on the
  builder's visitor read.
- Idle retention deletes the rating with the session.
- A builder's `PUT` on a visitor session returns `CHAT_SESSION_NOT_FOUND`.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q tests/test_chat_ratings.py tests/test_api_envelope.py tests/test_layers.py`

## Assumptions

- The per-IP read limit is the visitor limit that applies to rating. A rating does not count as a chat message.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0075 and DEC-0070.
- 2026-10-27: implemented and moved to review. Renumbered before push: DEC-0069 and TASK-0157 to TASK-0161 are held on factory/task-0157-parallel-tool-waves (REQ-0076). Draft PR #204.
- 2026-10-27: REV-0131, no blocking findings, approved for QA. QA-0131 pass with follow-up. Task stays in review.
- 2026-10-27: owner approved ("duyệt"). REV-0131 has no blocking findings. QA-0131 passed with the documented follow-ups. Moved to done. Not merged.

## Handoff Notes

- TASK-0163 and TASK-0164 consume `rating`, `run_exists`, `thumbs_down` and `GET .../chat/ratings`.
- TASK-0165 fills `feedback_id` from the worker.
