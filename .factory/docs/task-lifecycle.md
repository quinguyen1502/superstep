# Task Lifecycle

Tasks move through the following lifecycle:

`backlog -> todo -> doing -> review -> qa -> done`

Each state is represented by a folder under `.factory-state/tasks/` inside an individual project repository:

- `.factory-state/tasks/backlog/`
- `.factory-state/tasks/todo/`
- `.factory-state/tasks/doing/`
- `.factory-state/tasks/review/`
- `.factory-state/tasks/qa/`
- `.factory-state/tasks/done/`

## States

## Branch And PR Expectations

Each implementation task should be developed on a dedicated task branch created from the project integration branch, normally `develop`.

The default delivery sequence is:

1. Create or update the task artifact.
2. Create a task branch named `factory/task-<id>-<short-name>`.
3. Implement the task and update related artifacts.
4. Run and record required validation.
5. Move the task to review, push the branch, and open one Draft PR into the
   integration branch.
6. Address owner feedback and record review on the same branch and Draft PR.
7. Move the task to QA and validate the acceptance criteria.
8. After owner review and QA pass, update final artifacts and move the task to
   done.
9. Rebase onto the latest integration branch, squash the task into one commit,
   and rerun required validation.
10. Push rewritten history with `--force-with-lease` and mark the existing PR
    Ready for review.
11. Wait for explicit human approval before merge.
12. When the owner approves the merge and the task is not in done yet (the owner
    approved straight from review or QA), move it to done on the same task PR:
    one commit that sets `Status: done` and logs the approval, then wait for the
    required checks and merge. Never open a separate pull request only to move a
    task to done.

Agents must not merge a task branch into the integration branch without explicit human approval. If PR tooling or remote access is unavailable for an active delivery task, leave the work committed on the task branch and document the blocker in the task or a blocker artifact.

Do not create a second or replacement pull request when a Draft PR advances to
Ready. Owner feedback, QA fixes, and final delivery all use the same task PR.
Never use an unrestricted force push for the final rewritten branch history.

Do not create tasks or blocker artifacts for routine command trials, missing local authentication, sandbox or network retries, or other assistant execution mechanics unless they materially block an active delivery task after reasonable retry or approval handling. When no active task is blocked, report the issue to the human owner instead of adding durable project artifacts.

### Backlog

Potential work that is not ready for implementation.

Entry criteria:

- Request or need is recorded.
- Owner or source is identified when known.
- The item represents project work, product scope, delivery planning, or durable project knowledge rather than transient assistant execution mechanics.

Exit criteria:

- Requirement has enough context for planning, or the item is closed or deferred.

### Todo

Planned work ready for development.

Entry criteria:

- Task artifact exists.
- Scope, inputs, outputs, constraints, and acceptance criteria are documented.
- Dependencies are resolved or explicitly tracked.
- Requirement, design when applicable, architecture when applicable, and validation inputs are linked.

Exit criteria:

- Developer accepts the task and moves it to doing.

### Doing

Work actively being implemented or reworked.

Entry criteria:

- Developer has inspected project context and task inputs.
- Assumptions and blockers are documented.

Exit criteria:

- Implementation and task artifact are updated.
- Local validation is complete or limitations are documented.
- Task is ready for review.
- Any changed discovery, standard, decision, design, or architecture artifacts are updated.

### Review

Work waiting for or undergoing review.

Entry criteria:

- Developer handoff notes exist.
- Changed files and validation results are documented.
- The task branch is pushed and a Draft PR into the integration branch is open
  when remote access is available.

Exit criteria:

- Review artifact exists.
- No blocking review findings remain before moving to QA.
- Blocking findings return the task to doing.

### QA

Work waiting for or undergoing validation against acceptance criteria.

Entry criteria:

- Passing or conditionally passing review artifact exists.
- QA has enough context to validate the task.

Exit criteria:

- QA artifact exists.
- No blocking QA findings remain before moving to done.
- Owner review has no unresolved blocking feedback.
- Blocking QA findings return the task to doing.

### Done

Completed work.

Entry criteria:

- Requirement, task, review, and QA artifacts are linked.
- Design, architecture, decision, and discovery artifacts are linked when applicable.
- Review passed or accepted with documented follow-up.
- QA passed or accepted with documented residual risk.
- Final review and QA outcomes are recorded before the task move.
- Task branch is rebased onto the latest integration branch and squashed into
  one task commit.
- Required validation passes after the rebase and squash.
- When remote access is available, the existing PR is Ready for review.
- No unresolved blocking items remain.

Exit criteria:

- Merge still requires explicit human approval.
- Reopened only through a new task or approved lifecycle transition.

Done means approved, validated, and ready to merge. It does not assert that the
task commit is already present on the integration branch, so no separate
post-merge administrative commit is required only to change lifecycle state.
A task PR therefore carries its own move to done (step 12 above). If the PR is
closed without merging, move the task back to the state it left.
