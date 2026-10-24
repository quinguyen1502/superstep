# Task

## Metadata

- Project: superstep
- Task ID: TASK-0084
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0048
- Design IDs: none
- Architecture IDs: DEC-0052, DEC-0053, DEC-0054

## Objective

The web chat's backend: model, migration, repository, service, API, reply-once answers, memory, tagged reply tokens,
Human "answered by", retention and errors.

## Scope

### In Scope

- `models/chat_session.py` (`ChatSession`, `ChatTurn`), `WorkflowChatTrigger.settings`, migration `0035_chat_sessions`.
- `repositories/chat_sessions.py`; `ChatTriggerRepository.web/webs` (the Slack/Telegram list leaves the web chat out).
- `services/chat_session_service.py` (settings, sessions, `input_for`/`record`, `answer`, `check_answer`, `history`,
  `steps_of`, `cleanup`); `ChatRunService.on_settled` hands `web` messages to it; `RunService._plan_chat`.
- `api/routes/chat_sessions.py`, `schemas/chat.py`; `node_token.field`; validator `answered_by`; worker cleanup;
  workflow delete removes its chats.
- `errors.py`, `docs/api-errors.md`, en/vi error strings.
- `tests/test_chat_sessions.py`.

### Out Of Scope

- The UI (TASK-0085), phase 2 (public page, visitor access, SSE).

## Validation Plan

- pytest (new tests and the full suite, Postgres in CI).

## Activity Log

- 2026-10-23: implemented on `feat/agent-chat-p1-backend`; draft PR #116 into develop.
- 2026-10-24: PR #116 merged into develop (98516a8); moved to done by TASK-0110.

## Handoff Notes

- Merged (see Activity Log).
- Review REV-0077, QA QA-0077.
