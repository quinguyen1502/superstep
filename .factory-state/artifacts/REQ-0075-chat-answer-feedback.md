# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0075
- Status: Accepted on 2026-10-27 with the CLAR-0006 answers (all recommended options). Planned on 2026-10-27. Done on 2026-10-27, not merged (PR #204, DEC-0070, TASK-0162 to TASK-0166).
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Source: owner request in chat on 2026-10-27. Asked "Công việc tiếp theo là gì?", the agent listed what REQ-0074
  and REQ-0073 left out. The owner asked for a requirement for each direction ("3 hướng có thể làm thì bạn viết REQ
  trước đi").

## Summary

- People who chat with a workflow can rate each answer with a thumbs up or a thumbs down. With a thumbs down, they can
  also write a short comment.
- Builders see the ratings in the Chat tab. They can find the chats with a thumbs down, open the run behind the
  answer, and turn it into a test case.
- When LangSmith is set up, the rating is also sent there as feedback on the run's trace (CLAR-0006).

## Owner Decisions

The owner answered CLAR-0006 on 2026-10-27 with the recommended option for every question ("Trả lời CLAR-0006 đến
CLAR-0009 theo đề xuất, rồi merge #200").

1. **Where**: the public page, the embed and the studio Chat tab.
2. **Comment**: optional, with a thumbs down only.
3. **Builders**: marks on rated answers, a "thumbs down" filter in the Visitors list, and totals for the workflow
   (up, down, share of down over 7 and 30 days) in the Chat tab.
4. **LangSmith**: a rating is sent in the background when LangSmith is configured, as the feedback key `user_rating`
   (1 or 0, with the comment).
5. **Test cases**: "Save as test case" on rated answers, reusing the draft from the run (REQ-0042).
6. **Channels**: not now. Slack and Telegram ratings stay out of scope.

## Problem Or Opportunity

- Since 0.9.0, a workflow's chat is open to people outside the studio (REQ-0074). Builders can read visitor chats, but
  nothing tells them which answers were wrong. They would have to read every chat.
- REQ-0074 left feedback out of scope. REQ-0048 put it in a later phase.
- The building blocks exist already:
  - each answer is a `chat_turns` row linked to its run;
  - a run can become a draft test case (`POST /api/workflows/{wid}/tests/from-run/{rid}`, REQ-0042);
  - LangSmith already gets feedback from test runs (REQ-0050).
- Comparable tools: Dify's WebApp and Flowise's chatbot both have thumbs on answers, and Langfuse and LangSmith store
  them as scores. The comparison pages (REQ-0069) list Dify's annotation and feedback features.

## Scope

### In Scope

- **Rating an answer**:
  - a thumbs up and a thumbs down under each finished answer;
  - the person can change or remove their rating;
  - with a thumbs down, an optional comment (CLAR-0006 question 2).
  - The controls appear on the public page, the embed and the studio Chat tab (CLAR-0006 question 1).
- **Storage**: one rating per answer turn, with its time and the comment. Retention deletes ratings together with
  their session.
- **Builder view** in the Chat tab:
  - a mark on each rated answer;
  - a filter for chats that have a thumbs down;
  - totals for the workflow: up, down and the share of down over 7 and 30 days (CLAR-0006 question 3).
- **From feedback to a test**: "Save as test case" on a rated answer opens the existing draft from that answer's run
  (CLAR-0006 question 5).
- **LangSmith**: when it is configured, the rating goes to the run's LangSmith trace as feedback, in the background
  (CLAR-0006 question 4).
- **API**:
  - the public page rates through its own API, by slug, under the visitor's identity;
  - the studio rates through the workflow's chat API.
  - The visitor limits of REQ-0074 apply.
- Errors in CATALOG, `docs/api-errors.md` and both locales. en and vi strings. Handbook en and vi. CHANGELOG.
- Tests: pytest (only a session's own visitor can rate, one rating per turn, retention), vitest, and e2e on the public
  page and the Chat tab, in vi and en.

### Out Of Scope

- Ratings in Slack and Telegram chats (CLAR-0006 question 6).
- Rating a run outside a chat, for example from the run history.
- Scales other than up and down (stars, categories), and answers edited by the builder (Dify's "annotation reply").
- Sending feedback to Langfuse or OTel backends other than LangSmith.

## Stakeholders Or Users

- Visitors and studio users who chat with a workflow.
- Builders who improve the workflow from what people report.

## Current Context

- `chat_turns`: `role`, `text`, `status`, `run_id`. Answers are `assistant` turns.
- The visitor's identity (cookie or account) and the per-visitor limits come from REQ-0074 (DEC-0067).
- Builder side:
  - the Chat tab with its Visitors list (TASK-0142);
  - the test cases built from a run (REQ-0042);
  - `services/langsmith.py` with `LangSmithService`.

## Desired Behavior

1. A visitor gets an answer and clicks thumbs down. A small box asks "What went wrong?". They write a sentence and
   send it. The thumbs down stays highlighted. They can click it again to remove it.
2. The builder opens the Chat tab, then Visitors, and turns on the "Thumbs down" filter. They open a chat, see the
   comment under the answer, and click "Save as test case". The test editor opens with that run's input.
3. With LangSmith set up, the run's LangSmith trace shows the feedback.

## Business Rules

- Only the person who owns the session can rate its answers: the visitor for an anonymous session, the account for a
  signed-in or studio session.
- Only finished answers can be rated: `ok`, and `error` too, since a failed answer is worth reporting. A waiting turn
  cannot be rated.
- A comment is plain text of at most 1,000 characters.
- A builder who reads visitor chats sees the ratings and comments, but cannot rate on the visitor's behalf.

## Constraints

- The layers of DEC-0009 apply, and the migration goes through Alembic.
- shadcn/ui and theme tokens only. en and vi have the same keys.
- The response envelope and the central error handlers are used.
- The public API never shows another visitor's ratings.

## Acceptance Criteria

- On the public page, a visitor rates an answer up and then down with a comment. Reloading the page shows the same
  rating.
- A second visitor cannot rate or read the first visitor's ratings. A guessed turn id returns not found.
- The Chat tab shows the rating and the comment, filters chats with a thumbs down, and opens a draft test case from
  the rated answer's run.
- With LangSmith configured (the e2e test uses a stub), the rating is sent once. When LangSmith is down, rating still
  works.
- Retention deletes the ratings together with the session.
- `tests/test_layers.py`, `tests/test_api_envelope.py`, the backend suite, vitest, e2e and the strict handbook build
  pass.

## Edge Cases

- The answer's run was deleted: the rating stays, but "Save as test case" is disabled.
- The visitor rates twice quickly from two tabs. The last rating wins, and there is still one row.
- The chat is unpublished. The visitor's existing ratings stay. New ratings are refused with the chat's `CHAT_*` code.
- The answer that is rated is a Human question that was later answered. Only the final answer turn can be rated.

## Assumptions

- A thumbs up or down per answer is enough to start. Finer scales can come later.

## Open Questions

None. CLAR-0006 is answered.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`
- `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- TASK-0162 rating API, TASK-0163 public thumbs, TASK-0164 Chat tab, TASK-0165 LangSmith, TASK-0166 handbook
- `.factory-state/artifacts/REQ-0074-public-chat-page.md`, `.factory-state/artifacts/REQ-0048-agent-chat.md`
- `.factory-state/artifacts/REQ-0042-workflow-tests.md`, `.factory-state/artifacts/REQ-0050-langsmith-evals.md`
- `.factory-state/decisions/DEC-0052-web-chat-model.md`, `.factory-state/decisions/DEC-0067-public-chat-page.md`
- `docs/ui-conventions.md`, `docs/backend-architecture.md`
