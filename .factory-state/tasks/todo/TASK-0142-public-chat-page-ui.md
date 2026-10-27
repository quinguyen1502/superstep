# Task

## Metadata

- Project: superstep
- Task ID: TASK-0142
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067, DEC-0008

## Objective

Build the public chat page `/c/{slug}` and the publish settings. Builders also get the read-only "Visitors" list in the
Chat tab.

## Scope

### In Scope

- Route `/c/:slug`, outside `Protected`, built from the phase 1 chat components:
  - the title, the intro (sanitised Markdown) and the suggested messages;
  - the visitor's chats and "New chat";
  - streaming answers;
  - Human questions answered inline, and "waiting for approval";
  - the steps as the mode allows;
  - limit messages that give the retry time;
  - "This chat is not available";
  - for `signed_in`, a redirect to `/login?next=/c/{slug}`, with `next` supported on the login page.
- Light and dark themes, the phone layout, and en or vi from the browser.
- Chat settings dialog:
  - the access choice with three values;
  - the slug field with its errors;
  - the title, intro and suggestions;
  - the daily limit;
  - "Copy link" and "Open page".
- Chat tab: the "Visitors" list and the read-only view of a visitor chat.
- `lib/chat.ts` gains the public API calls through `api()` and a `usePublicChat` hook on the public socket.
- Every string goes in `en.json` and `vi.json`, with glossary rows in `docs/ui-conventions.md`.
- Tests:
  - vitest for the new helpers;
  - e2e `frontend/e2e/public-chat.spec.ts`, in vi and en: an anonymous context chats, a second context cannot see the
    first one's chat, `signed_in` redirects, unpublished pages and limits show their messages, and the builder sees
    the visitor chat.

### Out Of Scope

- `?embed=1`, the snippets and the widget (TASK-0143).

## Inputs

- TASK-0140 and TASK-0141.
- `components/chat/*`, `lib/chat.ts`, `components/editor/*` (the Chat tab and Chat settings), `App.tsx`,
  `docs/ui-conventions.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none; the page reuses the Chat tab's components
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md`
- Decisions: `DEC-0008-shadcn-ui-and-theme-tokens-only.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md`

## Expected Outputs

- Screenshots of the page (light, dark and phone, in vi and en) and of the settings dialog, for review.

## Implementation Notes

- The public page must not load studio-only data: no `/api/me` call for `anonymous`, and no workflow list.

## Constraints

- shadcn/ui and tokens only. Run the UI review checklist. Every string in en and vi.

## Dependencies

- TASK-0141.

## Acceptance Criteria

- The e2e test above passes in vi and en.
- `npm run lint`, `npx vitest run` and the locale key test pass.
- The UI checklist is recorded in the review.

## Validation Plan

- `cd frontend && npm run lint && npx vitest run && npx playwright test e2e/public-chat.spec.ts e2e/agent-chat.spec.ts`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0074.

## Handoff Notes

- TASK-0143 adds the embed layout to this page.
