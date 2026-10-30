# Large Task Workflow

Use this workflow for broad, high-risk, cross-cutting, multi-agent, or multi-stage work.

## Flow

1. PO defines outcome, priority, scope boundaries, and success criteria.
2. BA decomposes requirements, workflows, rules, edge cases, and unresolved questions.
3. Designer creates or updates design artifacts when work affects users, interfaces, CLI UX, API developer experience, or documentation experience.
4. Architect creates or updates architecture artifacts and decision records under `.factory-state/`.
5. Planner decomposes work into phases, tasks, dependencies, and validation checkpoints.
6. Developer completes tasks in lifecycle order on dedicated task branches.
7. Developer moves each completed task to review, pushes its branch, and opens
   one Draft PR into the integration branch.
8. Reviewer and human owner review each task and may request rework on the same
   branch and Draft PR.
9. QA validates each task and may request rework.
10. After owner review and QA pass, Developer updates final artifacts, moves
    the task to done, rebases onto the latest integration branch, squashes the
    task into one commit, reruns validation, pushes with
    `--force-with-lease`, and marks the existing PR Ready for review.
11. Human owner approves each Ready PR before merge.
    If the task is not in done yet, it moves to done on that PR before the merge;
    no separate PR only for the move.
12. Planner tracks phase completion.
13. PO confirms final requirement completion from done artifacts.

## Required Artifacts

- Requirement artifacts in `.factory-state/artifacts/`.
- Analysis artifacts or requirement refinements.
- Design artifacts in `.factory-state/artifacts/` when user-facing behavior or experience changes.
- Architecture artifacts in `.factory-state/artifacts/` and decision records in `.factory-state/decisions/`.
- Task artifacts in `.factory-state/tasks/` for each work item.
- Review artifacts in `.factory-state/artifacts/`.
- QA artifacts in `.factory-state/artifacts/`.
- Completion summary in `.factory-state/artifacts/` when the large effort closes.

## Rules

- Large work must be split into independently reviewable tasks.
- Artifact IDs are allocated after `git fetch --all --prune` and against every ref (`factory ids next <TYPE> --all-refs`), since an unmerged sibling branch can hold a number the integration branch cannot see. Before every push that adds artifacts the allocation is re-confirmed the same way, and `factory ids check --ref origin/<integration-branch>` gates whether the branch can land; collisions are renumbered on the unmerged side before pushing.
- Every implementation task must use a dedicated task branch and pull request into the integration branch unless the human owner explicitly approves a direct merge.
- Each task uses one PR. Do not replace the Draft PR when it becomes Ready.
- Agents must not merge task branches into the integration branch without explicit human approval.
- Designer may be skipped only when the work has no user-facing, operator-facing, developer-facing, or documentation-facing experience impact; the skip must be documented.
- Destructive changes, migrations, broad rewrites, or irreversible operations require explicit approval.
- Risks, dependencies, and rollback or recovery considerations must be documented when relevant.
- Completion requires all blocking review and QA findings to be resolved or explicitly accepted by the appropriate owner.
- Command trials, local authentication gaps, sandbox or network retries, and other assistant execution mechanics are not project tasks. Record them only when they materially affect a real project task, and otherwise summarize them to the owner.
