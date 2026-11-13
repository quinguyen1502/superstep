# Task

## Metadata

- Project: superstep
- Task ID: TASK-0323
- Title: Align Studio form controls and delete confirmation
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Review: owner approval on 2026-11-13 after the layout review in chat and green CI on PR #379. No separate REV artifact.
- QA: GitHub checks on PR #379 passed on 27c411e3, including factory verify, backend pytest, frontend builds, and Playwright. No separate QA artifact.
- Requirement IDs: REQ-0098
- Design IDs: DEC-0008
- Architecture IDs: DEC-0025
- Size: S

## Objective

Apply the owner's Settings and editor layout notes without changing the Dataset UI that just landed on develop.

## Owner-Facing Outcome

Connection counts read as a phrase. External-link icons sit before their labels. Multi-field forms fill their columns, a single-field form stays compact, and the create-team row matches one team card. A typed delete name is bold text inside quotes.

## Scope

### In Scope

- Connection heading in `editor-config.tsx` and the `editor.nodeInfo` plural keys in both locales.
- Icon order in `HandbookLink` and the two Usage Grafana anchors. Horizontal gridlines on the runs-over-time chart.
- Budget form column alignment. Create-team row on the same `lg:grid-cols-2` grid as the team cards.
- Shared `ConfirmDeleteDialog` name styling, locale strings, and the Playwright confirm helper.
- Question-card select trigger `w-full`.

### Out Of Scope

- Dataset pages and dialogs.
- Stretching the access-token form or the team member email field.
- A separate review or QA artifact. The owner approved the merge from the chat review and the green checks.

## Dependencies

- None. Branched from `origin/develop` at `0c391eda`.

## Acceptance Criteria

- The behaviors in REQ-0098 hold on top of the merged Dataset stack.
- Locale keys match between English and Vietnamese.
- Delete confirmation still requires an exact name and does not send a confirm field.

## Validation Plan

- GitHub CI on 27c411e3 passed, including factory verify. This done move does not change product code.

## Assumptions

- The owner already accepted the layout from screenshots on 2026-11-13. No separate design artifact. DEC-0008 remains the visual-token rule.
- Designer, BA, and Architect roles are skipped because the owner specified the layout directly.

## Open Questions

- None

## Activity Log

- 2026-11-13: Owner asked to open the pull request after the Dataset review found no further UI changes. Implementation was already on the local tree. Reapplied it onto `origin/develop` and moved this task to review.
- 2026-11-13: Owner asked to check CI and merge. CI on 27c411e3 was green. Moved to done on PR #379.

## Handoff Notes

- Branch `factory/task-0323-studio-form-layout`. Pull request #379 into `develop`. Merge with a merge commit after the checks on this done move are green.
