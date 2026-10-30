# Task

## Metadata

- Project: superstep
- Task ID: TASK-0144
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067

## Objective

Document the public chat page and the embed in the handbook, in en and vi. Update the comparison pages and the
CHANGELOG.

## Scope

### In Scope

- The handbook's chat guide, en and vi, gains a "Publish a chat" section:
  - access values, the slug, the page text and the limits;
  - the visitor chats;
  - the iframe and widget snippets;
  - the Safari note, the note that the host site can read the widget token, and a note that visitor chats are kept
    for `retention_days`.
- The public API reference: the public chat routes and the socket.
- The comparison pages, en and vi: the public chat page gap is closed.
- Operator settings: `STUDIO_PUBLIC_CHAT_RATE_*` in the configuration page.
- Screenshots from the e2e captures (`handbook.spec.ts`).
- CHANGELOG `## Unreleased` › Added.

### Out Of Scope

- Code changes, except the capture test.

## Inputs

- TASK-0140 to TASK-0143.
- `handbook/docs/{en,vi}/`, `frontend/e2e/handbook.spec.ts`, `CHANGELOG.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md`
- Decisions: none
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md`

## Expected Outputs

- Handbook pages in en and vi with matching anchors, and new screenshots.

## Implementation Notes

- Follow the existing handbook style and the Vietnamese glossary (REQ-0045).

## Constraints

- The strict handbook build must pass.

## Dependencies

- TASK-0143.

## Acceptance Criteria

- The handbook strict build passes, the en and vi pages carry the same sections, and the CHANGELOG lists the feature.

## Validation Plan

- The handbook strict build, and `npx playwright test e2e/handbook.spec.ts`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0074.
- 2026-10-27: merged into develop (PR #190) with the owner's approval.

## Handoff Notes

- After this task, the 0.9.0 release (TASK-0139, #184) updates its contents and is taken out of draft.
- Review: `.factory-state/artifacts/REV-0127-task-0144.md`.
- QA: `.factory-state/artifacts/QA-0127-task-0144.md`.
