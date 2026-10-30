# Small Task Workflow

Use this workflow for narrow, low-risk work with clear requirements and limited impact.

## Flow

1. PO records or confirms a requirement.
2. Designer is consulted only when user-facing behavior or experience is unclear.
3. Planner creates a single task from the requirement under `.factory-state/tasks/`.
4. Developer creates a dedicated task branch from the integration branch, inspects project context, and implements the task.
5. Developer moves the task to review, pushes the branch, and opens one Draft
   PR into the integration branch.
6. Reviewer and human owner review the change; feedback stays on the same
   branch and Draft PR.
7. QA validates acceptance criteria.
8. After owner review and QA pass, Developer updates final artifacts, moves the
   task to done, rebases onto the latest integration branch, squashes the task
   into one commit, reruns validation, pushes with `--force-with-lease`, and
   marks the existing PR Ready for review.
9. Human owner approves the Ready PR before merge.
   If the task is not in done yet, it moves to done on that PR before the merge;
   no separate PR only for the move.

## Required Artifacts

- Requirement artifact in `.factory-state/artifacts/`.
- Design artifact in `.factory-state/artifacts/` when UX direction is needed.
- Task artifact in `.factory-state/tasks/`.
- Review artifact in `.factory-state/artifacts/`.
- QA artifact in `.factory-state/artifacts/`.

## Rules

- BA, Designer, and Architect may be skipped only when requirements, experience direction, and technical direction are already clear.
- Artifact IDs are allocated after `git fetch --all --prune` and against every ref (`factory ids next <TYPE> --all-refs`), since an unmerged sibling branch can hold a number the integration branch cannot see. Before every push that adds artifacts the allocation is re-confirmed the same way, and `factory ids check --ref origin/<integration-branch>` gates whether the branch can land; collisions are renumbered on the unmerged side before pushing.
- Every implementation task must use a dedicated task branch and pull request into the integration branch unless the human owner explicitly approves a direct merge.
- Each task uses one PR. Do not replace the Draft PR when it becomes Ready.
- Agents must not merge task branches into the integration branch without explicit human approval.
- Skipped roles must be documented in the task assumptions or activity log.
- Any discovered ambiguity returns the task to the appropriate earlier role.
- Do not create additional tasks or blocker artifacts for command trials, local authentication gaps, sandbox or network retries, or other assistant execution mechanics unless they materially block this task after reasonable retry or approval handling.
