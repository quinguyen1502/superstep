# Task

## Metadata

- Project: superstep
- Task ID: TASK-0085
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0048
- Design IDs: none
- Architecture IDs: DEC-0052, DEC-0053, DEC-0054

## Objective

The studio Chat tab (REQ-0048 phase 1) on the official shadcn chat components, the per-workflow Chat settings, the
Human node's "Answered by" option, docs, handbook and tests.

## Scope

### In Scope

- shadcn `message-scroller`, `message`, `bubble`, `marker`, `trace`, `code-block` (+ `hooks/use-highlighted-code.ts`,
  `lib/highlighter.tsx`; deps `@shadcn/react`, `shiki`); `react-markdown` + `remark-gfm` (no raw HTML, safe links only,
  no remote images).
- `lib/chat.ts` (types, `liveReply` from `node_token.field`, `liveSteps` by mode, `waitingTurn`, `answers`, `safeUrl`).
- `components/chat/`: `use-chat-run.ts` (the run socket with `{chat_session_id, message}` / resume, then the saved
  answer), `chat-panel.tsx` (chats list, New chat, Builder/Visitor view), `chat-thread.tsx`, `chat-steps.tsx`
  (Trace), `chat-confirmation.tsx` (Human node: inline answer or "waiting for approval"), `chat-composer.tsx`
  (Prompt Input pattern), `chat-markdown.tsx` (Code Block), `chat-settings-dialog.tsx`.
- Editor: Chat tab in the run panel; **⋯ → Chat settings**; Human config "Answered by".
- en/vi strings; glossary rows in `docs/ui-conventions.md`; handbook `run/chat.md` en/vi with screenshots.
- vitest (`lib/__tests__/chat.test.ts`, `components/__tests__/chat-markdown.test.tsx`), e2e `e2e/agent-chat.spec.ts`.

### Out Of Scope

- Phase 2: the public `/c/{slug}` page, anonymous / signed-in access, attachments, embed.

## Validation Plan

- tsc, oxlint, vitest, the e2e spec and the full e2e suite; handbook build (en/vi) and image check.

## Activity Log

- 2026-10-23: implemented on `feat/agent-chat-p2-ui` (stacked on `feat/agent-chat-p1-backend`); draft PR #117 (base #116).
- 2026-10-23: owner approved the panel layout mockup; implemented on #117: bottom panel Run · Test · Code, Chat as a
  resizable side panel with fullscreen (REV-0078 revision 3, QA-0078 revision 3).
- 2026-10-24: PR #117 merged into develop (861668f); moved to done by TASK-0110.

## Handoff Notes

- Merged (see Activity Log). A Human node's timeout is its existing deadline (TASK-0066); there is no chat-only
  timeout action.
- Review REV-0078, QA QA-0078.
