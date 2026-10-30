# Task

## Metadata

- Project: superstep
- Task ID: TASK-0148
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: none (owner request)
- Design IDs: none
- Architecture IDs: none

## Objective

A task PR carries its own move to `done`, so no separate PR is needed only to change lifecycle state. Owner request
on 2026-10-27: "Có cách nào khi merge thì tự chuyển luôn k? Tốn thêm 1 PR", then "Có thể quy định vào workflow của
factory k?".

The lifecycle already said done means "approved, validated, and ready to merge", with no post-merge commit needed,
but no step covered the common case: the owner approves the merge while the task is still in review or QA. Tasks were
then left in review and moved later in a chore PR (TASK-0139's release PR moved TASK-0140 to TASK-0146).

## Scope

### In Scope

- `.factory/docs/task-lifecycle.md`: step 12, and a note under Done (a PR closed without merging moves the task back).
- `.factory/AGENTS.md`, and the small, medium and large task workflows: the same rule at the merge step.
- `.factory/templates/skills/finish-pr/SKILL.md`: finish-pr moves the task to done, and a merge approval moves it
  first when it is not there yet. `factory skills apply` regenerates the Claude, Codex, Cursor and Grok copies.
- `AGENTS.md`: the rule among the required rules.
- TASK-0147 (merged in PR #198, left in review) moves to done here.
- `factory validate` failed on develop: TASK-0139 to TASK-0144 were moved to done without naming their review and QA.
  They now link REV-0123 to REV-0127 and QA-0123 to QA-0127; TASK-0139 says the owner's approval and CI stand in for
  them, as the earlier release tasks do.

- Upstream sw-ai-factory 338d7a8 (pushed to its `main`): the same framework changes plus a CHANGELOG entry;
  `.factory` here is vendored at 338d7a8 (byte-identical to that commit's framework files).

### Out Of Scope

- A GitHub Action that commits the move after a merge: it would write to `develop` without an approved PR.

## Inputs

- The owner's two questions above.

## Related Artifacts

- Requirements: none
- Design: none
- Architecture: none
- Decisions: none
- Discovery: none

## Expected Outputs

- Every agent's instructions say to move a task to done on its own PR before merging.

## Implementation Notes

- Wording only; no CLI change.

## Constraints

- Agents still merge only with the owner's explicit approval.

## Dependencies

- None.

## Acceptance Criteria

- The lifecycle doc, the framework AGENTS.md, the three workflows, the finish-pr skill and the project AGENTS.md all
  state the rule.
- `factory skills validate` reports every skill in sync, and `factory validate` passes.
- TASK-0147 is in done.

## Validation Plan

- `PATH="$PWD/backend/.venv/bin:$PATH" .factory/bin/factory skills validate`
- `PATH="$PWD/backend/.venv/bin:$PATH" .factory/bin/factory validate`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: asked for by the owner and written on `factory/task-0148-done-on-merge`.
- 2026-10-27: the owner asked to send the change upstream, sync it back and merge ("Thay đổi ngược về repo gốc và
  sync về rồi merge đi"): upstream 338d7a8 (144 unittest tests pass), vendored here; moved to done on PR #199 before
  the merge, under the rule this task adds.

## Handoff Notes

- Review: documentation and generated skills only; `skills validate` 70 in sync; `factory validate` and
  `ids check --ref origin/develop` pass.
- QA: all acceptance criteria hold; upstream `python -m unittest discover -s tests` 144 OK and `git diff --check`
  clean. This task moved to done on its own PR, the first use of the rule.
