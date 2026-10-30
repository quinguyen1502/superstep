# AI Software Factory

This repository contains reusable agent, workflow, template, and documentation assets for artifact-driven software delivery. It must remain independent of any project, business domain, architecture, language, framework, platform, or coding standard.

## Working In This Repository

This checkout is the factory framework, not a product project. There is no `.factory/` directory here; this `AGENTS.md` is the framework source.

To create a project:

```bash
factory init <name> --no-interactive \
  [--intake FILE.yaml] [--from-specs FILE.md] [--preset web-app|api|cli|mobile] \
  [--tool grok] [--copy]
```

To attach factory to an existing source repository:

```bash
factory import <project-dir> --apply --no-interactive
```

Then open the new project directory and follow its `AGENTS.md`. Use `create-project` or `import-project` when those skills are available. Do not implement product features in this repository.

A newly initialized project is not ready for implementation until `factory ready` passes in that project.

## Core Behavior

- Inspect the repository before changing files.
- Before applying any factory workflow in a project repository, verify `.factory/AGENTS.md` exists and read it.
- If `.factory/AGENTS.md` is missing and `.factory` is configured as a submodule, initialize it with `git submodule update --init .factory`.
- If factory initialization requires credentials, network access, or approval, request it before implementation.
- If `.factory/AGENTS.md` remains unavailable, stop implementation and record a blocker in `.factory-state/`.
- Do not proceed with factory workflow using only project-local instructions when `.factory/AGENTS.md` is required but unavailable.
- Discover project context dynamically from project artifacts, standards, decisions, implementation, tests, and documentation.
- Read `.factory-state/artifacts/` selectively. Start from the current task, `project.md`, `roadmap.md`, standards, and direct artifact references; do not read every artifact by default.
- Discover technology stack dynamically from files; do not assume one.
- Record discovered install, run, test, build, lint, typecheck, format, delivery, and operations commands before relying on them.
- Communicate through files and artifacts, not private conversation state.
- Document assumptions, blockers, and open questions in artifacts.
- Resolve discoverable facts before asking the owner. Use direct conversation for one to three simple questions and a linked clarification artifact for larger, grouped, checklist, or conditional question sets.
- Create task and blocker artifacts for project delivery state, not for routine assistant execution mechanics.
- Do not create standalone project tasks or blocker artifacts for command trials, missing local tool authentication, sandbox or network retries, or other transient execution issues unless they materially block an active project delivery task after reasonable retry or approval handling.
- Preserve existing conventions unless an approved artifact requires change.
- Request human approval before destructive, irreversible, security-sensitive, production-impacting, or broad-scope changes.
- Require review and QA before work is marked complete.

## Artifact Flow

Agents operate by reading inputs, producing outputs, and moving task artifacts through the lifecycle:

`backlog -> todo -> doing -> review -> qa -> done`

In project repositories, this lifecycle state lives under `.factory-state/tasks/`.

Each task must have enough context for the next agent to continue without relying on chat history.

## Branch And Review Flow

- Each implementation task must start from the project integration branch, normally `develop` unless project standards define a different branch.
- Each task must be implemented on its own tool-neutral task branch, normally named `factory/task-<id>-<short-name>`.
- Artifact IDs must be allocated after `git fetch --all --prune` and against every ref, not the integration branch alone (`factory ids next <TYPE> --all-refs`), because an ID is free only when no branch holds it and unmerged sibling branches hold IDs for days.
- Immediately before any push that adds artifacts, re-run `factory ids next <TYPE> --all-refs` and confirm it still returns the number taken; `factory ids check --ref origin/<integration-branch>` is the gate for whether the branch can land. On a collision, renumber the unmerged side before pushing.
- Agents must not merge task branches into the integration branch unless the human owner explicitly asks them to merge.
- Normal delivery is: create/update the task artifact, implement and validate on
  the task branch, then push and open one Draft PR when the task enters review.
  Owner feedback, review, and QA continue on that same branch and PR.
- After owner review and QA pass, update final artifacts and move the task to
  done, rebase onto the latest integration branch, squash the task into one
  commit, rerun required validation, push rewritten history with
  `--force-with-lease`, and mark the existing PR Ready for review.
- Done means approved, validated, and ready to merge. It does not mean the
  task commit is already present on the integration branch.
- The task PR carries its own move to done. If the owner approves the merge
  while the task is still in review or QA, push one commit on that PR that moves
  it to done and logs the approval, wait for the required checks, then merge.
  Never open a separate pull request only to move a task to done.
- Dependent tasks should start only after the previous task has been approved and merged, or must explicitly document that they are stacked on an unmerged task branch.
- If local-only work is necessary because remote access or PR tooling is unavailable, record the blocker and stop at a committed task branch instead of merging into the integration branch.
- If PR tooling, authentication, network access, or other local execution mechanics fail outside an active delivery task, report the issue to the human owner instead of creating durable project artifacts.

## Artifact Reading

- Prefer reference-following over folder-wide artifact scans.
- Read artifacts directly linked from the current task, requirement, design, architecture, decision, review, QA, or completion summary.
- Use discovery artifacts and standards when they affect stack, commands, conventions, risk, or validation.
- Scan all artifacts only for discovery, audit, planning, migration, traceability repair, or when required references are missing.
- When creating or updating tasks and artifacts, add explicit related artifact paths so future agents can read narrowly.

## Completion Rules

- Requirements must state scope, constraints, acceptance criteria, and open questions.
- User-facing work must state user flows, states, accessibility expectations, and UX acceptance criteria when applicable.
- Architecture decisions must include rationale, tradeoffs, and impacts.
- Plans must split work into verifiable tasks.
- Development must update implementation and task artifacts together.
- Reviews must record findings or explicitly state that no blocking findings exist.
- QA must record validation performed, evidence, results, gaps, and residual risk.
- Task completion requires updated artifacts, owner review outcome, QA outcome,
  required validation, a rebased and single-commit task branch, a Ready PR, and
  no unresolved blocking items.
- Integration completion requires a pull request into the integration branch and explicit human approval before merge.

## Repository Layout

- `agents/` contains reusable agent role definitions.
- `workflows/` contains task workflow definitions.
- `templates/` contains reusable artifact templates.
- `docs/` contains framework-level operating models.

Actual projects must live in separate project repositories, consume reusable framework assets through `.factory/`, and keep project-owned generated workflow state under `.factory-state/`.
