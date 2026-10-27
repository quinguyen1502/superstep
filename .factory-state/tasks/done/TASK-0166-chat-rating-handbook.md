# Task

## Metadata

- Project: superstep
- Task ID: TASK-0166
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0075
- Design IDs: none
- Architecture IDs: DEC-0070

## Objective

Document thumbs on chat answers in the handbook (en and vi) and name the change in the changelog.

## Scope

### In Scope

- `handbook/docs/en/run/chat.md` and `handbook/docs/vi/run/chat.md`: visitors rate a finished answer, the comment on
  thumbs down, and what the builder sees (mark, filter, totals, save as test case, LangSmith when tracing is on).
- `CHANGELOG.md` under Unreleased.

### Out Of Scope

- New screenshots. The existing chat screenshots stay.
- Comparison pages. REQ-0075 does not change the comparison claims beyond the handbook chapter.

## Inputs

- The behaviour from TASK-0162 to TASK-0165.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- Decisions: none beyond DEC-0070
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`

## Expected Outputs

- A reader of either handbook can find how to rate an answer and where the builder sees it.

## Implementation Notes

- Keep the new subsection next to "Visitor chats", in the same tone as that page.

## Constraints

- en and vi handbooks say the same thing.

## Dependencies

- TASK-0163, TASK-0164, TASK-0165.

## Acceptance Criteria

- Both handbook pages describe the thumbs, the comment, the filter, the totals and save as test case.
- CHANGELOG Unreleased has an Added entry for the rating.

## Validation Plan

- Read the two handbook sections side by side.
- The strict handbook build is `cd handbook && mkdocs build --strict` when that environment is installed.

## Assumptions

- No new image, so the image checker has nothing new to fail.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0075 and DEC-0070.
- 2026-10-27: implemented and moved to review. Renumbered before push: DEC-0069 and TASK-0157 to TASK-0161 are held on factory/task-0157-parallel-tool-waves (REQ-0076). Draft PR #204.
- 2026-10-27: REV-0135, no blocking findings, approved for QA. QA-0135 pass with follow-up. Task stays in review.
- 2026-10-27: owner approved ("duyệt"). REV-0135 has no blocking findings. QA-0135 passed with the documented follow-ups. Moved to done. Not merged.

## Handoff Notes

- None.
