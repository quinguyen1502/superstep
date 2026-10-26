# Project Repository Structure

Real projects live outside the factory framework repository. A project
repository contains project-specific source code, reusable factory
assets under `.factory/`, and generated factory workflow state under
`.factory-state/`.

## Recommended Structure

```text
project/
├── AGENTS.md
├── project-specs.md
├── vision.md
├── project.md
├── roadmap.md
├── .claude/
│   └── CLAUDE.md
├── .factory/
│   ├── AGENTS.md
│   ├── agents/
│   ├── workflows/
│   ├── templates/
│   └── docs/
└── .factory-state/
    ├── factory.yaml
    ├── intake/
    ├── scaffolding/
    │   ├── generated.yaml
    │   └── proposals/
    ├── dependencies/
    │   └── installed.yaml
    ├── skills/
    │   └── generated.yaml
    ├── standards/
    │   ├── architecture.md
    │   ├── coding.md
    │   ├── delivery.md
    │   ├── documentation.md
    │   ├── operations.md
    │   ├── review.md
    │   ├── security.md
    │   └── testing.md
    ├── decisions/
    ├── tasks/
    │   ├── backlog/
    │   ├── todo/
    │   ├── doing/
    │   ├── review/
    │   ├── qa/
    │   └── done/
    └── artifacts/
```

Project documentation, source, and validation assets are intentionally
omitted. Each project chooses its own layout based on its stack and
conventions.

## Directory Purpose

- `AGENTS.md` — project-local agent instructions; points agents to
  `.factory/`.
- `project-specs.md` — optional source specification used during
  onboarding when the project already has a consolidated vision, MVP,
  roadmap, stack, feature, or design brief. Use
  `.factory/templates/project-specs-template.md` when creating from
  scratch.
- `vision.md` — problem statement, high-level idea, and goals without
  technical assumptions.
- `project.md` — project context, domain, actors, modules, constraints,
  discovered stack.
- `roadmap.md` — priority bands such as P0, P1, P2.
- `.claude/CLAUDE.md` — imports the canonical root `AGENTS.md` when
  Claude Code is enabled.
- `.factory/` — reusable factory framework assets.
- `.factory-state/factory.yaml` — enabled AI coding tools, refiner, link
  mode, integration branch.
- `.factory-state/intake/` — resumable project-spec input and
  provenance.
- `.factory-state/scaffolding/` — source-generator provenance, managed
  output hashes, conflict proposals, `INCOMPLETE` when review remains
  open.
- `.factory-state/dependencies/` — reviewed package-manager commands,
  manifest and lockfile hashes, observed results, `INCOMPLETE` on
  failure.
- `.factory-state/standards/` — project-specific architecture, coding,
  delivery, documentation, operations, review, security, and testing
  standards.
- `.factory-state/decisions/` — project-specific decision records.
- `.factory-state/tasks/` — lifecycle-based task artifacts.
- `.factory-state/artifacts/` — requirements, discovery, design,
  architecture, review, QA, completion summaries, and other delivery
  artifacts.
- Project documentation, source, and validation asset layout remains
  project-defined.

## Framework Integration

The project root `AGENTS.md` must:

- Instruct agents to inspect project files first.
- Require verifying and reading `.factory/AGENTS.md` before running
  factory workflow.
- Require initializing `.factory` with
  `git submodule update --init .factory` when `.factory/AGENTS.md` is
  missing and `.factory` is configured as a submodule.
- Require stopping and recording a blocker if `.factory/AGENTS.md`
  remains unavailable.
- Reference `.factory/AGENTS.md`, `.factory/agents/`,
  `.factory/workflows/`, `.factory/templates/`, and `.factory/docs/`.
- Document any project-specific overrides.

### Linking mode: submodule vs copy

`factory init` prefers a Git submodule at `.factory/` and falls back to
a copy. Choose deliberately with `--copy` when needed.

| Mode | Pros | Cons | Use when |
| --- | --- | --- | --- |
| **Submodule** (default) | Framework updates are explicit and reviewable. Many projects can track one framework version. No repeated framework history per project. | Requires submodule familiarity and explicit `git submodule update --init .factory`. Awkward in tools with limited submodule support. | Multiple projects share a controlled framework version. |
| **Copy** (`--copy`) | Plain-file checkout, no submodule setup. Each project can customize its local copy. | Framework updates must be re-copied or scripted. Projects drift from the shared framework. Harder to compare framework versions across projects. | Submodules are not supported, or a project intentionally needs a detached framework copy. |

## Optional Workflow Skills

`templates/skills/` contains reusable, tool-neutral skill definitions
that describe common Factory workflows. Each skill uses the
Anthropic-style `SKILL.md` format with YAML frontmatter (`name`,
`description`) plus a Markdown body.

Available skills:

- `create-project` - create a project from the factory repository via `factory init`.
- `import-project` - attach factory to an existing source repository.
- `onboard-specs` - convert `project-specs.md` into factory artifacts.
- `create-requirement` - write one requirement artifact.
- `plan-tasks` - split a requirement into verifiable tasks.
- `discuss` - stay in analysis mode; no edits or validation.
- `next-task` - recommend the next task by lifecycle and dependencies.
- `task-start` - prepare branch and lifecycle to begin an approved task.
- `scoped-change` - implement or fix then stop before validation.
- `task-validation` - run declared validation commands and report results.
- `task-review` - produce a review artifact with blocking and non-blocking findings.
- `task-qa` - produce a QA artifact verifying acceptance criteria.
- `finish-pr` - finalize an approved task: rebase, squash, ready.
- `cleanup-branches` - audit and clean local branches and stale refs.

The workflow-neutral naming (`discuss`, `next-task`, `finish-pr`,
`cleanup-branches`) is grandfathered from earlier project usage.
Lifecycle-facing skills follow a `task-<action>` convention that reads
naturally alongside artifact names like `REV-####-TASK-####` and
`QA-####-TASK-####`. `scoped-change` is intentionally outside that
convention because it describes a mode of working, not a lifecycle
transition.

Projects opt in by copying skills into the paths their AI coding tools
read:

- Codex-style: `.agents/skills/<name>/SKILL.md` (or the project's own
  Codex convention), plus a generated `agents/openai.yaml` adapter
  alongside it.
- Claude Code: `.claude/skills/<name>/SKILL.md`. The file format is
  identical, so copies can be verbatim.
- Grok: `.grok/skills/<name>/SKILL.md`. Same format as Claude Code.
- Cursor: `.cursor/rules/<name>.mdc`. Convert the frontmatter to
  Cursor's rule schema (`description`, `alwaysApply: false`) and copy
  the body unchanged.

Skills are documentation; adopting them does not enable any permission
or hook.

### Applying skills via the CLI

The `factory skills` command automates emission for the tools enabled
in `.factory-state/factory.yaml`:

- `factory skills plan -C <project>` — preview what would be
  created, kept, updated, or conflict without touching the filesystem.
- `factory skills apply -C <project> [--force] [--skill NAME]` —
  emit skill files and record their hashes in
  `.factory-state/skills/generated.yaml`. A file that still has its
  recorded hash was not edited, so a newer template updates it. A file
  edited by hand is a conflict and is preserved; `--force` overwrites it.
- `factory skills validate -C <project>` — check that emitted files
  match the framework templates (drift detection).

`factory init` emits skills by default. Pass `--no-skills` to skip.
`--with-skills` remains accepted and is the default.

## Standard Templates

`templates/standards/` contains templates for project standards that a
project instantiates under `.factory-state/standards/` and fills with
its own thresholds. Available templates:

- `dependencies-template.md` - selection standard for third-party
  packages, plugins, and libraries. Covers stability, maintenance,
  provenance, status, platform support, license, and necessity.
  Projects instantiate as `.factory-state/standards/dependencies.md`
  with concrete ecosystem-specific thresholds.

The `scoped-change` skill references
`.factory-state/standards/dependencies.md` before adding a dependency
and falls back to the template shape when no project standard exists
yet.

## Example Tool Policy

`templates/tool-policy.example.yaml` is a documented example of the
canonical `.factory-state/tooling/tool-policy.yaml`. It shows the
schema fields, the `proposed`/`approved` status flow, kit `level`
options, and how to describe named `commands` with `Expected` or
`Observed` evidence. Copy it into the project during discovery and
fill in the project-specific commands.

`factory init` and `factory import --apply` emit the policy. A
repository that attached Factory before the tooling bundle, or that
never ran apply, will not have the file until someone backfills it.
Re-run `factory import --apply --no-interactive` or
`factory tools configure --no-interactive`. A `.factory` pin bump
does not create it.

## Project Bootstrap Checklist

1. Create the project repository.
2. Add or copy the factory framework into `.factory/`.
3. Create the project root `AGENTS.md` with factory preflight rules and
   references to `.factory/AGENTS.md`.
4. Create `vision.md`, `project.md`, and `roadmap.md`.
5. Create `.factory-state/standards/`, `.factory-state/decisions/`,
   `.factory-state/tasks/`, and `.factory-state/artifacts/`.
6. Record project-specific assumptions, standards, and approval gates.
7. Complete an initial project discovery task before implementation
   work begins.
8. If `project-specs.md` exists, convert it into factory artifacts using
   `templates/prompts/onboard-project-specs.md`.
9. Use `templates/clarification-template.md` only when a task has many,
   grouped, checklist, or conditional owner questions.
10. Optionally copy `templates/skills/` entries into the enabled tools'
    skill/rule directories, and copy
    `templates/tool-policy.example.yaml` into
    `.factory-state/tooling/tool-policy.yaml` to draft project
    permissions.
