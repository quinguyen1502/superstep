# Task

## Metadata

- Project: superstep
- Task ID: TASK-0163
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0075
- Design IDs: none
- Architecture IDs: DEC-0070

## Objective

Let a visitor rate a finished answer on the public page. The embed uses that same page, so it gains the thumbs too.

## Scope

### In Scope

- Thumbs up and thumbs down under each finished answer (`ok` and `error`) in `ChatThread`, shown when the caller
  passes `onRate`.
- A second click on the active thumb removes the rating.
- Thumbs down opens an optional comment ("What went wrong?"). Sending it updates the rating.
- The public page wires `onRate` to the public rating route and reloads the session.
- en and vi strings.
- e2e on the public page, in vi and en: rate down with a comment, reload, the same rating is shown.

### Out Of Scope

- The studio Chat tab's filter, totals and "Save as test case" (TASK-0164).
- LangSmith (TASK-0165).

## Inputs

- TASK-0162's API.
- `frontend/src/components/chat/chat-thread.tsx`, `frontend/src/pages/PublicChat.tsx`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- Decisions: `DEC-0067-public-chat-page.md`, `DEC-0008` (`docs/ui-conventions.md`)
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`

## Expected Outputs

- The public page and the embed show the thumbs and keep the rating across a reload.

## Implementation Notes

- shadcn `Button` only. The pressed thumb uses `variant="secondary"` and `aria-pressed`. No hard-coded colours.
- The comment field is an `Input` with `maxLength` 1000.

## Constraints

- Every UI string is in `locales/en.json` and `locales/vi.json` under the same keys.

## Dependencies

- TASK-0162.

## Acceptance Criteria

- On the public page, thumbs down, a comment, and a reload show the same thumb and the comment.
- Clicking that thumb again clears it after the next read.
- A waiting answer has no thumbs.

## Validation Plan

- `cd frontend && npx vitest run src/lib/__tests__/chat.test.ts`
- `cd frontend && npm run e2e -- e2e/public-chat.spec.ts`

## Assumptions

- The embed iframe and the widget both load `/c/{slug}`, so one control covers both.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0075 and DEC-0070.
- 2026-10-27: implemented and moved to review. Renumbered before push: DEC-0069 and TASK-0157 to TASK-0161 are held on factory/task-0157-parallel-tool-waves (REQ-0076). Draft PR #204.
- 2026-10-27: REV-0132, no blocking findings, approved for QA. QA-0132 pass with follow-up. Task stays in review.
- 2026-10-27: owner approved ("duyệt"). REV-0132 has no blocking findings. QA-0132 passed with the documented follow-ups. Moved to done. Not merged.

## Handoff Notes

- `ChatThread`'s `onRate` is also how TASK-0164 rates a builder's own studio chat.
