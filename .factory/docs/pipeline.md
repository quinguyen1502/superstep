# Factory pipeline

Every Factory project moves through the same milestones. Each stage
leaves a durable marker under `.factory-state/`, so tools can tell where
a project stands without asking. This page names the milestones, explains
what each one produces, and points to the commands that drive them.

## Milestones

```
 ┌──────┐    ┌─────────┐    ┌────────┐    ┌───────┐
 │ Init │ ─▶ │  Deps   │ ─▶ │ Verify │ ─▶ │ Tasks │
 └──────┘    └─────────┘    └────────┘    └───────┘
     required      optional      optional     checkpoint
```

Deps and Verify are optional. A project can skip them when it does not
need them. Verify is the check CI runs after the project has source.
Init is required. Tasks is the day-to-day checkpoint.

### 1. Init  ·  `factory init <name>` (or `factory import`)

Creates the artifact bundle — `AGENTS.md`, `project.md`, `vision.md`,
`roadmap.md`, `project-specs.md`, `.factory-state/`, an initial discovery
task, and a project-local tool policy. Init is not the implementation
gate; run `factory ready` after discovery, requirements, and planning.

Marker: `.factory-state/factory.yaml`. Docs: [`cli.md`](cli.md#project-initialization).

### 2. Dependencies  ·  `factory deps plan|apply|validate`

Installs project-local dependencies from the manifests and lockfiles
already in the repository. Never installs adapter prerequisites globally.
A failed install records an `INCOMPLETE` marker for retry.

Marker: `.factory-state/dependencies/installed.yaml`. Incomplete:
`.factory-state/dependencies/INCOMPLETE`. Docs: [`dependencies.md`](dependencies.md).

### 3. Verify  ·  `factory verify plan|run|validate`

Runs the verification commands declared in `tool-policy.yaml` — test,
lint, typecheck, format, analyze, build — and records the pass or fail
result. An empty command list is discovered from manifests once and then
recorded into the policy. This is the check a project CI workflow runs
on pull requests.

Marker: `.factory-state/verification/latest.yaml`. Docs: [`verification.md`](verification.md).

Copy [`templates/ci/factory-verify.yml`](../templates/ci/factory-verify.yml)
to `.github/workflows/` when the project should run that check on pull
requests. Docs: [`stack-configuration.md`](stack-configuration.md).

### 4. Tasks  ·  `factory task create|move|archive`

Once the pipeline is set up, day-to-day work moves through the lifecycle:

```
backlog  ─▶  todo  ─▶  doing  ─▶  review  ─▶  qa  ─▶  done
```

Agents move task files with `factory task move` on a dedicated task
branch. They do not dispatch parallel worktrees from Factory.

Docs: [`task-lifecycle.md`](task-lifecycle.md).

## How status is decided

- **Done** — the stage's marker file exists and no `INCOMPLETE` sits
  alongside it.
- **In progress** — an `INCOMPLETE` marker exists (either alone,
  meaning the `apply` failed halfway; or next to the marker, meaning
  proposals still need review).
- **Not started** — no marker at all.

The **Tasks** stage is a checkpoint rather than a build phase: any task
counts as in progress, and only when every task is in `done` does the
stage read done.
