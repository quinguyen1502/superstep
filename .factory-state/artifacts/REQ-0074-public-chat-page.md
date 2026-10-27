# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0074
- Status: Proposed. It waits for the owner's answers to CLAR-0005.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Source: owner request in chat on 2026-10-27. The owner first asked why Agent chat was not next ("Sao k làm agent
  chat?"), then asked to ship it in the same release as REQ-0073 ("Tôi muốn đưa vào chung release luôn"). This
  requirement is phase 2 of REQ-0048.

## Summary

- A builder can **publish** a workflow's chat at `/c/{slug}`. People who do not use the studio can then talk to the
  workflow there.
- The page reuses the phase 1 chat:
  - sessions and turns;
  - one run per message;
  - the history window;
  - Human nodes answered in the chat;
  - the step setting.
- It adds three things: visitor access (`anonymous` or `signed_in`), a public connection to the run, and limits against
  abuse.
- It ships in **0.9.0** together with REQ-0073. The 0.9.0 release PR waits until this requirement is done.

## Owner Decisions

CLAR-0005 holds them. They are not answered yet.

## Problem Or Opportunity

- Phase 1 (REQ-0048) built the chat for builders only. To let someone else try a workflow, a builder must give them a
  studio account with the run right, or wire up Slack or Telegram, or call the public API from their own page.
- The data model already has room for this phase:
  - `chat_sessions.visitor` and `channel`;
  - the trigger's `command` holds the slug;
  - the access values `anonymous` and `signed_in` are reserved, and a request for them is refused today with
    `CHAT_ACCESS_NOT_AVAILABLE`.
- Langflow ("Playground" or shareable), Flowise ("Share Chatbot") and Dify ("WebApp") all have a public chat page for
  a flow. The comparison pages (REQ-0069) name this as a gap.

## Scope

### In Scope

- **Publish setting** in the Chat settings dialog:
  - the slug, unique across the studio, with a default and a check;
  - the access value: `studio`, `anonymous` or `signed_in`;
  - a "Copy link" button and an "Open page" button.
  - The page is live only while the web chat is enabled and the access value is not `studio`.
- **Public page `/c/{slug}`**, built on the same chat components as the Chat tab:
  - the workflow's chat title, an intro text and suggested messages (CLAR-0005 question 6);
  - the visitor's earlier chats and a "New chat" button;
  - Human questions answered inline;
  - "waiting for approval" when a reviewer must answer;
  - steps shown as the `steps` setting says;
  - light and dark themes, and a phone layout;
  - en and vi, by the browser's language.
- **Visitor identity**:
  - for `anonymous`, a visitor id that the page keeps (CLAR-0005 question 2);
  - for `signed_in`, the studio account (CLAR-0005 question 1).
  - A visitor reads and continues only their own sessions.
- **Public API and connection**, by slug and with no studio session:
  - read the page settings;
  - list and read the visitor's sessions;
  - send a message and answer a Human node, streaming as the Chat tab does.
  - It can start only that workflow's chat runs, never any other run.
- **Limits** (CLAR-0005 question 3):
  - messages per visitor and per IP in a window, shared through Redis when it is set;
  - a cap per workflow per day;
  - the existing `TEXT_MAX` and `max_turns`.
  - A refusal is `RATE_LIMITED` with `Retry-After`, or a new `CHAT_*` code.
- **Runs**:
  - each message runs as the workflow's owner, with the owner's credentials, knowledge bases and MCP servers, as Slack
    and Telegram chat triggers already do;
  - runs show in the run history with `source = "chat"`;
  - the version that runs is set by CLAR-0005 question 8.
- **Builders**:
  - the Chat tab can list visitor chats, read-only (CLAR-0005 question 7);
  - retention (`retention_days`) applies to visitor sessions too.
- Errors in `core/errors.py`, `docs/api-errors.md` and both locales. Glossary rows. Handbook en and vi (the chat guide
  and the public API page). CHANGELOG.
- Tests: pytest (access, isolation between visitors, limits, published and unpublished), vitest, and an e2e test of an
  anonymous visitor in a new browser context, in vi and en.

### Out Of Scope

- File attachments, feedback (thumbs), and streaming over SSE.
- Custom domains, custom colours and logos (CLAR-0005 question 6 keeps the page plain).
- The embed widget, unless CLAR-0005 question 5 brings it in.
- A visitor deleting their own history (retention handles it), and exporting a chat.
- Billing or quotas per visitor beyond the limits above.

## Stakeholders Or Users

- Builders who want to share a workflow with colleagues or customers.
- Visitors, who have no studio account (`anonymous`) or a studio account without the run right (`signed_in`).
- The deployment's operator, who pays for model calls and sets the limits.

## Current Context

- Phase 1:
  - TASK-0084 (#116): the backend, the `web` chat trigger, sessions, turns and retention;
  - TASK-0085 (#117): the Chat tab.
- Decisions:
  - DEC-0052: the model;
  - DEC-0053: access and steps; `anonymous` and `signed_in` are reserved;
  - DEC-0054: `answered_by`.
- The run socket `/ws/run` needs a studio session today. `ChatSessionService` checks the run right.
- Rate limiters already exist for triggers, chat triggers, approval callbacks and demo mode (`services/rate_limit.py`).
  They are fixed-window and shared through Redis.
- The vision lists a "public multi-tenant SaaS" as a non-goal. This page serves the visitors of one self-hosted
  deployment, so it does not make Superstep multi-tenant.

## Desired Behavior

1. **The builder publishes the chat.** They open Chat settings, choose `anonymous`, keep or edit the slug and save.
   The dialog shows the link `/c/{slug}`.
2. **A visitor opens the link.**
   - They see the title, the intro and the suggested messages.
   - They send a message. The answer streams in, with the steps the setting allows.
   - When they come back in the same browser, their earlier chats are listed.
3. **A Human node asks a question.**
   - When `answered_by` is `visitor`, the visitor answers it in the page.
   - When it is `reviewer`, the page shows "waiting for approval" and updates when the reviewer answers in the inbox.
4. **The visitor hits a limit.** The page says when they can try again.
5. **The builder unpublishes** by setting access back to `studio` or disabling the chat.
   - The page shows "This chat is not available".
   - A message sent from a page that is already open is refused.
6. **With `signed_in`**, a visitor who is not signed in is sent to the sign-in page and comes back to the chat after
   signing in.

## Business Rules

- A slug is lowercase letters, digits and `-`, from 3 to 64 characters, unique across the studio, and not a reserved
  word.
- The public API never shows:
  - the workflow's graph or its state beyond what the `steps` setting allows;
  - the owner, other visitors, or run ids of other sessions.
- A visitor's session is reachable only with that visitor's id, or for `signed_in`, that user's account.
- An Agent node's tool approval is always a reviewer's (DEC-0054, `agent_of`). A visitor cannot approve the agent's own
  actions.
- A published chat is refused in demo mode (`STUDIO_DEMO_MODE`), unless CLAR-0005 says otherwise.

## Constraints

- Layers (DEC-0009): routers call services, and services call repositories. Migrations go through Alembic, and there is
  no raw SQL.
- shadcn/ui and tokens only. Every string in en and vi with identical keys.
- The response envelope and the central error handlers are used. Each new code goes in CATALOG, `docs/api-errors.md`
  and both locales.
- The public routes do not use the studio's session cookie for `anonymous`, so a visitor cannot make a studio action
  happen through the page. CORS stays same-origin.

## Acceptance Criteria

- A builder publishes a workflow's chat with `anonymous` access, and an anonymous browser context chats with it at
  `/c/{slug}`. The context is not signed in to the studio.
  - The answer streams, and the history window works across turns.
  - A Human node answered by the visitor resumes the run.
- A second anonymous context cannot list or read the first one's sessions. A guessed session id returns not found.
- With `signed_in`:
  - an anonymous context is sent to sign in;
  - a signed-in user without the run right can chat;
  - their sessions are their own.
- Unpublishing makes the page and its API refuse new messages with a `CHAT_*` code, and the page explains why.
- Going over the per-visitor, per-IP or per-workflow limit is refused with a stated retry time. The run is not started.
- The runs use the owner's resources and show in the run history. Visitor chats appear read-only in the Chat tab, if
  CLAR-0005 question 7 says so.
- The page passes the UI review checklist (`docs/ui-conventions.md`) in light, dark and phone layouts, en and vi.
- `tests/test_layers.py`, `tests/test_api_envelope.py`, the backend suite, vitest, the new e2e test and the strict
  handbook build pass.

## Edge Cases

- The slug changes while a page is open: the old link stops working, and an open page refuses new messages.
- The workflow is deleted or its owner loses access. The page shows "not available", and waiting runs are cancelled as
  they are today.
- A run waits on a reviewer and the visitor leaves. The answer is written to the turn when the reviewer answers, and
  the visitor sees it next time.
- A visitor clears their browser storage. Their old sessions stay until retention deletes them, but the visitor can no
  longer reach them.
- Two tabs of the same visitor send at once. `CHAT_RUN_WAITING` and reply-once behave as in phase 1.
- A very long message, or messages in a burst, are refused by `TEXT_MAX` and the limits.

## Assumptions

- Visitors use a modern browser with WebSocket.
- The deployment sits behind a proxy that sets the client IP, as the existing IP limits already assume.

## Open Questions

CLAR-0005 holds the eight owner questions.

## Related Artifacts

- `.factory-state/artifacts/REQ-0048-agent-chat.md` (phase 1)
- `.factory-state/artifacts/CLAR-0005-public-chat-page.md`
- `.factory-state/decisions/DEC-0052-web-chat-model.md`
- `.factory-state/decisions/DEC-0053-chat-access-and-steps.md`
- `.factory-state/decisions/DEC-0054-human-answered-by.md`
- `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md` (ships in the same release)
- `.factory-state/tasks/doing/TASK-0139-version-0-9-0.md` (the 0.9.0 release, waiting for this requirement)
- `docs/ui-conventions.md`, `docs/backend-architecture.md`
