# Task

## Metadata

- Project: superstep
- Task ID: TASK-0173
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0075, REQ-0076, REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

Bring the factory records in line with what is merged on `develop`. Records only, no source change.

## Scope

### In Scope

- REQ-0079 status line: phase 1 PRs, TASK-0167 to TASK-0171 merged (PRs #214 to #218), TASK-0172 in PR #219, not released.
- REQ-0075 and REQ-0076 status lines use the `Done (tasks, PRs, merged date)` wording of other finished requirements.
- DEC-0071 status line: TASK-0168 to TASK-0171 merged too.

### Out Of Scope

- Deleting branches. Source, tests and handbook changes.

## Inputs

- The audit of 2026-10-30 (GitHub PR list and `develop` history).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`, `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`, `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: none
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: none

## Expected Outputs

- Status lines that match the merged PRs.

## Implementation Notes

- Only the `- Status:` metadata lines change, so this does not conflict with PR #219, which edits the REQ-0079 phase 2 list.

## Constraints

- `factory validate` exits 0.

## Dependencies

- None. Based on `develop` at `f8b3aa1`.

## Acceptance Criteria

- REQ-0075, REQ-0076 and REQ-0079 and DEC-0071 status lines name the merged PRs.
- `factory validate` exits 0.

## Validation Plan

- `factory validate`
- `factory verify run --profile full`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-30: owner approved the record cleanup after the audit. Branch `factory/task-0173-record-cleanup` from `develop` at `f8b3aa1`. Status lines updated. Moved to review with the PR.
- 2026-10-30: owner approved the merge of PR #220. CI green (15 pass). Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Review: `.factory-state/artifacts/REV-0149-task-0173.md`. QA: `.factory-state/artifacts/QA-0149-task-0173.md`.
- Stale branches found by the audit are listed in the PR description; none were deleted.
