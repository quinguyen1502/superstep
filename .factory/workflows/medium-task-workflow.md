# Medium Task Workflow

Use this workflow for work with moderate ambiguity, multiple files, dependency changes, or meaningful user-visible behavior.

## Flow

1. PO defines requirement and priority.
2. BA refines rules, edge cases, and acceptance criteria.
3. Designer confirms or updates UX direction when user-facing, operator-facing, developer-facing, or documentation-facing experience may be affected.
4. Architect confirms or updates technical direction when structure, interfaces, data, or operational behavior may be affected.
5. Planner splits work into one or more tasks.
6. Developer creates a dedicated task branch from the integration branch, implements each task, and records validation.
7. Developer moves each task to review, pushes its branch, and opens one Draft
   PR into the integration branch.
8. Reviewer and human owner review each task; feedback stays on the same branch
   and Draft PR.
9. QA validates each task against acceptance criteria.
10. After owner review and QA pass, Developer updates final artifacts, moves
    the task to done, rebases onto the latest integration branch, squashes the
    task into one commit, reruns validation, pushes with
    `--force-with-lease`, and marks the existing PR Ready for review.
11. Human owner approves the Ready PR before merge.
    If the task is not in done yet, it moves to done on that PR before the merge;
    no separate PR only for the move.
12. Planner or PO confirms the requirement is complete when all tasks are done.

## Required Artifacts

- Requirement artifact in `.factory-state/artifacts/`.
- Refined analysis notes when needed.
- Design artifact in `.factory-state/artifacts/` when experience direction changes or needs confirmation.
- Architecture artifact in `.factory-state/artifacts/` when technical direction changes or needs confirmation.
- One or more task artifacts in `.factory-state/tasks/`.
- Review artifact in `.factory-state/artifacts/` for each task.
- QA artifact in `.factory-state/artifacts/` for each task.

## Rules

- Work may proceed incrementally, but every task must complete review and QA.
- Artifact IDs are allocated after `git fetch --all --prune` and against every ref (`factory ids next <TYPE> --all-refs`), since an unmerged sibling branch can hold a number the integration branch cannot see. Before every push that adds artifacts the allocation is re-confirmed the same way, and `factory ids check --ref origin/<integration-branch>` gates whether the branch can land; collisions are renumbered on the unmerged side before pushing.
- Every implementation task must use a dedicated task branch and pull request into the integration branch unless the human owner explicitly approves a direct merge.
- Each task uses one PR. Do not replace the Draft PR when it becomes Ready.
- Agents must not merge task branches into the integration branch without explicit human approval.
- User-facing assumptions must be explicit.
- Architectural assumptions must be explicit.
- Follow-up work must be tracked as new tasks in `.factory-state/tasks/`, not hidden in review or QA notes.
- Do not create follow-up tasks or blocker artifacts for command trials, local authentication gaps, sandbox or network retries, or other assistant execution mechanics unless they materially block delivery after reasonable retry or approval handling.
