# Task

## Metadata

- Project: superstep
- Task ID: TASK-0164
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0075
- Design IDs: none
- Architecture IDs: DEC-0070

## Objective

Show ratings to the builder in the Chat tab: a mark and the comment, a thumbs-down filter, totals for 7 and 30 days,
and "Save as test case" on a rated answer. The builder can also rate their own studio chat.

## Scope

### In Scope

- Own studio chats use the same thumbs as TASK-0163, through the studio rating route.
- A visitor chat is read-only: the mark and the comment, no thumbs that write.
- "Save as test case" on a rated answer opens the existing test-case dialog with the from-run draft. The button is
  disabled when `run_exists` is false. Shown when the user can edit the workflow.
- A "Thumbs down" filter on the visitors list (`?thumbs_down=1`), including the narrow panel.
- Totals from `GET /api/workflows/{wid}/chat/ratings` in the Chat tab. The share of down is `down / (up + down)`.
- en and vi strings.
- e2e: the builder sees the visitor's comment and the filter.

### Out Of Scope

- Sending the rating to LangSmith (TASK-0165).
- Handbook (TASK-0166).

## Inputs

- TASK-0162 and the `ChatThread` props from TASK-0163.
- `frontend/src/components/chat/chat-panel.tsx`, `editor-tests-panel.tsx` (`TestCaseDialog`).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- Decisions: `DEC-0067-public-chat-page.md`, `docs/ui-conventions.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`

## Expected Outputs

- The Chat tab filters visitor chats that have a thumbs down, shows the comment, and opens a draft test case.

## Implementation Notes

- `canEdit` comes from the editor (`studio.edit && !studio.source`), the same gate as Save as test case on a run.
- The dialog is `TestCaseDialog`, already inside `StudioContext`.

## Constraints

- shadcn components and theme tokens. Identical locale keys.

## Dependencies

- TASK-0162. The thumbs control is shared with TASK-0163; this task can land after that control exists.

## Acceptance Criteria

- A builder's own finished answer can be rated and the rating survives a reload of the session.
- A visitor chat shows the rating and the comment, and the builder's rating request is not sent.
- The thumbs-down filter lists only chats that have a down rating.
- The totals line shows up, down and the share of down for 7 and 30 days.
- "Save as test case" opens the draft. It is disabled when the run was deleted.

## Validation Plan

- `cd frontend && npx vitest run src/lib/__tests__/chat.test.ts`
- `cd frontend && npm run e2e -- e2e/public-chat.spec.ts`

## Assumptions

- The share is rounded to a whole percent in the UI. Zero ratings show an em dash for the share.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0075 and DEC-0070.
- 2026-10-27: implemented and moved to review. Renumbered before push: DEC-0069 and TASK-0157 to TASK-0161 are held on factory/task-0157-parallel-tool-waves (REQ-0076). Draft PR #204.
- 2026-10-27: REV-0133, no blocking findings, approved for QA. QA-0133 pass with follow-up. Task stays in review.
- 2026-10-27: owner approved ("duyệt"). REV-0133 has no blocking findings. QA-0133 passed with the documented follow-ups. Moved to done. Not merged.

## Handoff Notes

- None.
