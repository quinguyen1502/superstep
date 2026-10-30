# Task

## Metadata

- Project: superstep
- Task ID: TASK-0181
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Keep the conversation with the agent that answered last across messages of one chat session.

## Scope

### In Scope

- Chat session column `active_agent` (Alembic revision), set when a run that answers a chat message ends at an Agent node reached by a hand-off.
- The next message's run starts at that agent: the run input carries `__start_agent`, and a start router added by the compiler routes there when it names an existing Agent node (DEC-0073 decision 4).
- If the agent was deleted or is no longer a hand-off target, the run starts at the entry and the column is cleared.
- Public chat, studio Chat tab and Slack/Telegram chat triggers share the behaviour through the chat session services.

### Out Of Scope

- Engine hand-off (TASK-0180).
- UI (TASK-0182).

## Inputs

- REQ-0078 'Chat'; DEC-0073 decision 4.
- `services/chat_session_service.py`, `services/public_chat_service.py`, `services/chat_run_service.py`, `models/chat_session.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- A test proves the second message goes to the agent that answered the first.

## Implementation Notes

- Keep the start router a no-op when `__start_agent` is absent so runs outside chats are unchanged.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0180.

## Acceptance Criteria

- Second message of a session runs at Billing after a hand-off in the first.
- Deleted target falls back to the entry agent.
- A new session starts at the entry.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py tests/test_api_envelope.py`

## Assumptions

- The designer step is skipped. REQ-0078 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0073 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0078 (DEC-0073). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.

## Handoff Notes

- Branch `factory/task-0181-agent-handoff-chat-state` from `develop`.
