# Task

## Metadata

- Project: superstep
- Task ID: TASK-0214
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0048 (web chat), REQ-0072 (agent node)
- Design IDs: none
- Architecture IDs: DEC-0052, DEC-0063, DEC-0073

## Objective

Fix at the cause the bug found on v0.10.2 with a Start -> Agent -> End chat: the current message reached the model
twice, once as the last item of the conversation (history) field and once as the Agent's task prompt.

## Findings

- `ChatSessionService.prepare` sets the conversation field to the last `max_turns` exchanges plus the new message
  (DEC-0052, documented in run/chat.md "Memory", used by LLM prompts like `{{state.messages}} Answer the last user
  message.`). The Agent node copied the whole history field, then appended its rendered task prompt as a user message;
  with `{{state.message}}` (the built-in agent template, `templates.py`) the message was sent twice. The Python and
  TypeScript exports generated the same code.
- LLM node: it sends only its rendered prompt (no history list), so it had no separate duplication; a prompt that
  renders `{{state.messages}}` gets the message inside that text by design (documented pattern).
- Public chat (web page and embed): same `prepare`, so it was affected through the Agent exactly as the studio chat;
  no separate path.
- TASK-0210 history (a waiting question kept before its chat answer; truncation by whole exchanges) is built in
  `history()` and is unchanged; the fix only removes the trailing current message on the Agent side.
- Hand-off targets (DEC-0073) get the source agent's conversation plus their own task prompt; unchanged here.

## Fix

The Agent (studio `agents.history`, and both exports) leaves out the history's last item when it is a user message
whose text the rendered task prompt already contains. The conversation field contract and the LLM documented pattern
stay as they are, so saved workflows and templates need no migration; a prompt without the message keeps the history
whole (nothing is lost).

## Acceptance Criteria

- The exact messages sent to the model for turns 1 and 3 of a Start -> Agent -> End chat contain each message once.
- The same with a Human node answered in the chat before the Agent (question and answer kept in order, TASK-0210).
- Exports behave as the studio; `factory verify run --profile full` and `factory validate` pass; CI green.

## Validation

- `backend/tests/test_chat_agent_messages.py`: 3 of 4 fail on develop (a6192e11) with the duplicate user message;
  4/4 pass after. The fourth (prompt without the message) passes before and after.
- Python/TypeScript export parity runs with a history ending in the current message.

## Review And QA

- Review: `.factory-state/artifacts/REV-0202-task-0214.md`. QA: `.factory-state/artifacts/QA-0202-task-0214.md`.

## Activity Log

- 2026-10-31: created from the owner's bug report; implemented on `factory/task-0214-chat-duplicate-message` from
  `develop` (a6192e11). REV/QA 0202 because #270 uses 0201. Moved to done on this PR before the merge.
