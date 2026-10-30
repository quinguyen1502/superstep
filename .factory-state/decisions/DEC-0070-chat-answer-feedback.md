# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0070
- Status: Accepted. The owner gave the CLAR-0006 answers on 2026-10-27; this record writes them down.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Related Requirements: REQ-0075 (CLAR-0006), REQ-0074, REQ-0042, REQ-0050
- Related Architecture:
  - DEC-0009 (layers)
  - DEC-0052 (web chat model)
  - DEC-0067 (public chat page)
- Related Tasks: TASK-0162, TASK-0163, TASK-0164, TASK-0165, TASK-0166

## Context

- Each answer is a `chat_turns` row. A run that waits at a Human node writes a `waiting` turn, then a later turn for the
  final state. The waiting row is not rewritten.
- The person who owns a session is the studio user (`owner`) or the anonymous visitor (`visitor`). Builders read
  visitor chats through `/api/workflows/{wid}/chat/visitors` and cannot act as that visitor.
- A run already becomes a draft test case at `POST /api/workflows/{wid}/tests/from-run/{rid}` (REQ-0042).
- LangSmith traces a run from `runs.trace_root` (`run_id_of` in `services/langsmith.py`). Test suites already send
  feedback with `create_feedback`, from a worker job, so a slow or failed LangSmith call does not fail the request.
- CLAR-0006: thumbs on the public page, the embed and the studio Chat tab; an optional comment on thumbs down only;
  marks, a thumbs-down filter and 7-day and 30-day totals; LangSmith feedback key `user_rating`; "Save as test case"
  on rated answers; Slack and Telegram stay out.

## Decision

1. **One rating per answer.** Table `chat_ratings` (migration `0042_chat_ratings`):
   - `turn_id` is the primary key;
   - `session_id` and `workflow_id` are stored so retention and the totals do not join through turns;
   - `value` is `up` or `down`;
   - `comment` is plain text, empty when there is none;
   - `created` and `updated`;
   - `feedback_id`, the LangSmith feedback id once one has been sent, empty until then.
   - A second write updates the same row. The last write wins.
2. **Who may rate.** Only the session's owner: the visitor on the public API, the studio user on
   `PUT /api/chat/sessions/{sid}/turns/{tid}/rating`. A builder reading a visitor chat is not that owner, so the
   studio route answers `CHAT_SESSION_NOT_FOUND`. Ratings are returned only with a session the caller may already read.
3. **Which turns.** An assistant turn whose status is `ok` or `error`. A user turn, and a turn that is `waiting`,
   `cancelled`, `expired` or `timeout`, answers `CHAT_RATING_NOT_ALLOWED`. A turn id that is not in that session
   answers `CHAT_TURN_NOT_FOUND`. The waiting turn of a Human question stays unrateable after the final answer is
   written, so only the final answer of that run can be rated.
4. **Comment.** At most 1,000 characters, and only with `down`. A comment sent with `up` answers
   `CHAT_RATING_INVALID` (`field` is `comment` or `value`). Omitting `comment` on a new `down` stores an empty
   comment. Sending `comment` later updates it.
5. **Removing.** `DELETE` on the same path removes the row. The UI treats a second click on the active thumb as
   delete. A removed rating is not sent to LangSmith again.
6. **Routes.**
   - Public: `PUT` and `DELETE /api/public/chat/{slug}/sessions/{sid}/turns/{tid}/rating`, with the same visitor
     check as reading the session. The per-IP read limit of DEC-0067 applies. An unpublished chat answers
     `CHAT_NOT_PUBLISHED`; ratings already stored stay.
   - Studio: `PUT` and `DELETE /api/chat/sessions/{sid}/turns/{tid}/rating`.
   - A session read adds `rating` (`{value, comment, updated}` or null) on each turn, and `run_exists` on assistant
     turns.
   - `GET /api/workflows/{wid}/chat/visitors?thumbs_down=1` keeps chats that have a thumbs down. Each row adds
     `thumbs_down`.
   - `GET /api/workflows/{wid}/chat/ratings` returns `{d7: {up, down}, d30: {up, down}}` from `updated` in the last
     7 and 30 days. The share of down is computed in the UI.
7. **Save as test case.** The Chat tab calls the existing from-run route. The button is shown on a rated answer and
   is disabled when `run_exists` is false.
8. **LangSmith.** After a saved rating, the API enqueues `{kind: "chat_rating", turn_id}`. The worker calls
   `LangSmithService.on_rating`. When `LANGSMITH_API_KEY` is set, tracing is on, and the run has `trace_root`, it
   sends feedback key `user_rating` with score 1 or 0 and the comment. The first send is `create_feedback` and stores
   `feedback_id`; a later rating updates that feedback. A LangSmith error is logged. The rating request has already
   succeeded. No key, tracing off, or no `trace_root`: the job does nothing.
9. **Retention.** Deleting a session, idle cleanup, deleting a workflow's chats, or deleting an owner's chats deletes
   the ratings of those sessions in the same transaction.

## Rationale

- One row per turn matches "the last rating wins" and makes the thumbs a toggle.
- Reusing the session owner check keeps a visitor's ratings as private as their messages.
- A background job matches how test-suite feedback already avoids blocking the request on LangSmith.
- The from-run route already builds the draft, so the new work is a button and `run_exists`.

## Alternatives Considered

- Option: store the rating columns on `chat_turns`.
  - Benefits: no new table.
  - Tradeoffs: every turn write path would carry rating fields, and a rating update would rewrite the message.
  - Reason Not Chosen: a rating is not part of the message the workflow sees.
- Option: send the rating to LangSmith inside the request.
  - Benefits: the test can assert the call before the response returns.
  - Tradeoffs: a slow LangSmith call holds the visitor's click.
  - Reason Not Chosen: REQ-0075 says the rating still works when LangSmith is down.

## Impacts

- New error codes `CHAT_TURN_NOT_FOUND`, `CHAT_RATING_NOT_ALLOWED`, `CHAT_RATING_INVALID`.
- Session JSON gains `rating` and `run_exists`. Visitor list rows gain `thumbs_down`.
- The public page, the embed (the same page) and the studio Chat tab show the thumbs.

## Risks

- Two quick clicks from two tabs can enqueue two jobs. The second updates the same LangSmith feedback when the first
  has stored `feedback_id`. If both run before either stores the id, LangSmith can show two feedbacks. The studio
  still has one row.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-10-27
- Scope And Limits: The CLAR-0006 answers. Slack and Telegram ratings are out of scope.

## Review Or Revisit Trigger

- A need to retract a LangSmith feedback when the visitor removes the rating.
- A scale other than up and down.

## Allocation

- 2026-10-27: renumbered from DEC-0069 before the first push. That number, and TASK-0157 to TASK-0161, are held on `factory/task-0157-parallel-tool-waves` (REQ-0076).
