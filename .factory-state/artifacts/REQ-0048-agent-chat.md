# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0048
- Status: Phase 1 implemented (TASK-0084 PR #116, TASK-0085 PR #117); phase 2, the public page `/c/{slug}`, done as REQ-0074 (PRs #186 to #191, 0.9.0)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-27
- Source: owner request in chat, 2026-10-23, after the agent chat UI research (`/workspace/scratch/agent-chat-ui-research.md`,
  recommendation (a): our own UI on the shadcn chat components over our run protocol). The owner approved phase 1 with
  decisions (1)-(6) below.

## Summary

People talk to a workflow in a chat. Phase 1 is a **Chat tab in the editor** for builders; the data model and API are
shaped so the published page `/c/{slug}` (phase 2) and the embed (later) reuse them.

## Owner Decisions

1. Audience: builders and the public. Phase 1 = the studio Chat tab; phase 2 = the public page.
2. Access is a per-workflow setting: `studio` now; `anonymous` and `signed_in` are reserved for phase 2.
3. Memory: the history goes into a `messages` list field (convention), window = `max_turns` exchanges.
4. Each Human node has "answered by": `visitor` (default, answered inline) or `reviewer` (the chat shows "waiting for
   approval"; the Approvals inbox answers it), with the existing deadline as its timeout and an error code.
5. Step visibility per workflow: `none` / `labels` (default) / `full`; builders in the studio always see full.
6. Attachments and the embed come later (room left in the model); history retention per workflow (days) with a cleanup job.

## Acceptance Criteria (phase 1)

- Backend: `chat_sessions` / `chat_turns` (migration 0035), repositories, a service and the API in the common envelope;
  the web chat is a chat trigger of kind `web` reusing the chat run service and its reply-once logic; `node_token`
  carries the output `field`; Human `answered_by`; retention setting and cleanup; new `CHAT_*` codes in `errors.py`,
  `docs/api-errors.md` and en/vi.
- Frontend: a Chat tab in the editor run panel with the shadcn chat components (Message Scroller, Message, Bubble, Trace,
  Code Block), Human questions as Confirmation/Questionnaire, `useChatRun` over `/ws/run` and `lib/trace.ts`, sanitised
  markdown, a session list / new chat, and a Chat settings section.
- en/vi per the glossary (new rows), handbook pages en/vi.
- Tests: pytest, vitest, and an e2e with a multi-turn memory chat, a visitor-answered Human node and the step modes.

## Out Of Scope (phase 1)

- The public page, anonymous / signed-in visitor access, SSE, attachments, the embed, feedback.
