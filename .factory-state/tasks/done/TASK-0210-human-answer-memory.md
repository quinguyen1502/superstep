# Task

## Metadata

- Project: superstep
- Task ID: TASK-0210
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0048 (chat)
- Design IDs: none
- Architecture IDs: DEC-0052

## Objective

The two minor points of the post-merge review of #264 (TASK-0209): the chat memory had a Human-node answer without its
question (two `user` messages in a row, and the `-2 * max_turns` cut off by one message per answer), and an object
(form) answer was not saved by `record_answer`.

## Findings

- Point 1, confirmed: `history` kept `user` turns and `ok` answers only, so the waiting question was dropped while its
  answer (saved since TASK-0209) was kept. `history` now keeps a waiting question when the person's answer follows it
  (an unanswered question, or one answered by a reviewer, stays out), and cuts by exchanges: an exchange starts at each
  of the person's messages that is not an answer.
- Point 2, confirmed: `record_answer` returned for any non-string. `answer_text` renders a form as `field: value`
  lines (non-strings as JSON, empty fields left out); `None`, blank text and an empty form still save nothing. The turn
  is a plain `user` text turn, so the thread, rating (assistant only), `answers()` and `waitingTurn` are unchanged; no
  UI change.

## Acceptance Criteria

- The memory alternates roles across a Human answer and `max_turns` counts exchanges.
- A form answer is saved as a readable user turn.
- Regression tests fail before the fix and pass after; `factory verify run --profile full` and `factory validate` pass; CI green.

## Validation

- `test_chat_sessions.py::test_visitor_answers_the_human_node_in_the_chat` (memory) and
  `test_chat_sessions.py::test_a_form_answer_is_saved_as_readable_text`: both fail on develop 8dd49d74, pass after.

## Review And QA

- Review: `.factory-state/artifacts/REV-0198-task-0210.md`. QA: `.factory-state/artifacts/QA-0198-task-0210.md`.

## Activity Log

- 2026-10-31: created from the owner's request to fix the two minor review points of #264 if quick; implemented on
  `factory/task-0210-human-answer-history` from `develop` (8dd49d74). Moved to done on this PR before the merge.
