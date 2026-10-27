# Task

## Metadata

- Project: superstep
- Task ID: TASK-0141
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067, DEC-0052, DEC-0054, DEC-0023

## Objective

Let visitors chat: add the public socket, which runs each message as the workflow's owner and streams only what the
`steps` setting allows. Visitors answer Human nodes. Message limits and the daily cap apply, and builders get a
read-only list of visitor chats.

## Scope

### In Scope

- `WS /ws/public/chat/{slug}` (DEC-0067, decisions 2 and 4):
  - it accepts only `{chat_session_id, message}` or `{chat_session_id, resume_run_id, response}`;
  - it checks the visitor as TASK-0140 does;
  - it plans the run through the phase 1 chat path as the owner.
- A stream filter in the service: the reply `node_token` deltas, steps cut down to the mode, the visitor's Human
  question, and the final status with its error code.
- Limits (decision 5): per visitor, per IP and per window, then `daily_limit` through `make_counter`.
  `RATE_LIMITED` or `CHAT_DAILY_LIMIT` is returned before the run starts.
- A Human node answered by a visitor, and the reviewer case with `CHAT_ANSWER_BY_REVIEWER`, both as in DEC-0054.
- `GET /api/workflows/{wid}/chat/visitors` and reading one visitor session in builder view (decision 8).
- nginx `location /ws/` already covers the new socket. Check that the all-in-one image routes it.
- Tests: `backend/tests/test_public_chat_runs.py`.

### Out Of Scope

- The UI (TASK-0142) and frames (TASK-0143).

## Inputs

- TASK-0140's `PublicChatService`.
- `api/routes/runs_ws.py`, `services/run_service.py` (`plan` with `chat_session_id`), `services/chat_session_service.py`
  (`steps_of`, `answer`, `answer_visitor`), `services/chat_run_service.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md`
- Decisions: `DEC-0052-web-chat-model.md`, `DEC-0054-human-answered-by.md`, `DEC-0023-rbac-sharing.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md`

## Expected Outputs

- An anonymous socket client chats over several turns with memory. It never receives a run id, state or node
  input or output, except in `full` mode.

## Implementation Notes

- Reuse the phase 1 planning and answer code. Only the auth, the acting user and the event filter are new.
- The visitor's IP comes from `client_ip`, with the trusted proxies.

## Constraints

- Layers (DEC-0009). No new run sources: the source stays `chat`.

## Dependencies

- TASK-0140.

## Acceptance Criteria

- pytest:
  - a two-turn chat with a messages field keeps the history;
  - the run has the owner's `owner` and `source = "chat"`;
  - in `labels` and `none` modes the streamed frames have no state, input or output and no `run_id`;
  - a Human node answered by the visitor resumes the run;
  - a reviewer node refuses a visitor answer.
- The eleventh message in a window from one visitor gets `RATE_LIMITED` with `retry_after`. The daily cap gives
  `CHAT_DAILY_LIMIT`. Neither starts a run.
- A socket for an unpublished slug closes with `CHAT_NOT_PUBLISHED`. A frame with `workflow_id` or any other key is
  refused.
- The visitors list shows web and embed sessions to a user with the run right and refuses others.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0074.

## Handoff Notes

- TASK-0142 builds the page on this socket.
