# Factory CLI

The `factory` CLI initializes and operates artifact-driven project
repositories. Initialization publishes artifacts directly. Dependency
installation and verification are later commands.

For a step-by-step introduction, follow [`quickstart.md`](quickstart.md).

## Commands

```text
factory init <project-name> [--tool codex|cursor|claude-code|grok] [--refiner TOOL] [--tool-kit LEVEL] [--preset PRESET] [--intake FILE] [--from-specs FILE] [--with-skills|--no-skills] [--no-interactive]
factory import [project-dir] [--apply] [--tool-kit LEVEL] [--with-skills|--no-skills] [--no-interactive]
factory ready -C <project-dir>
factory specs -C <project-dir> [--refiner TOOL] [--no-ai] [--no-interactive]
factory validate [project-dir]
factory tools status|configure|plan|apply|validate -C <project-dir>
factory tools configure [--no-interactive] [--level LEVEL] [--status proposed|approved] [--tool TOOL] [--command NAME=COMMAND] -C <project-dir>
factory gc [-C <project-dir>] [--keep N] [--apply] [--no-artifacts]
factory deps plan|apply|validate -C <project-dir>
factory verify plan|run|validate -C <project-dir> [--profile quick|full] [--check KIND]
factory skills plan|apply|validate -C <project-dir> [--skill NAME] [--force]
factory task create <task-id> <title> [--state backlog|todo|doing|review|qa|done]
factory task move <task-id> <state>
factory task archive [task-id] [--state STATE] -C <project-dir>
factory ids check [--ref REF ...] [--all-refs] -C <project-dir>
factory ids next [TYPE ...] [--ref REF ...] [--all-refs] -C <project-dir>
```

Running `factory` with no arguments prints this help. `--no-interactive`
is accepted on `init`, `import`, `specs`, and `tools configure` so
existing scripts keep working. Those commands always publish without a
prompt.

## Artifact ID Allocation

An artifact ID is free only when **no branch holds it**. Work sits in
unmerged branches for days, so a scan of the integration branch alone
cannot see a number a parallel session allocated an hour ago — it will
hand out the same number a second time, and the collision only surfaces
at merge.

Allocate against every ref, and fetch first so remote-tracking branches
are current:

```text
git fetch --all --prune
factory ids next TASK --all-refs -C <project-dir>
```

Then re-verify immediately before pushing. `--ref` is repeatable and
composes with `--all-refs`:

```text
factory ids check --ref origin/develop -C <project-dir>
factory ids check --all-refs -C <project-dir>
```

The two scopes answer different questions, and `check` is the one where
the difference matters:

- **`check --ref origin/<integration-branch>` is the merge gate.** It
  asks whether this branch can land, and every collision it reports is
  one somebody has to resolve now.
- **`check --all-refs` is a survey.** A repository that has been
  renumbering collisions for a while still has the losing filenames on
  the branches they were fixed on, so this scope reports pairs that were
  settled months ago. Read the bracketed sources: a name held by one
  abandoned branch and nothing else is history, not a defect.

`next --all-refs` has no such caveat. A number that only a stale branch
ever held is a number worth skipping anyway, so the widest scope is
always the safe one to allocate from.

Neither command fetches. A stale `origin/develop` produces a confident
wrong answer, so the fetch is the caller's job.

`ids` is the one command that runs on the standard library alone. It is
required before every push that adds artifacts, and a checkout that has
not installed the CLI's dependencies is exactly where that push happens,
so `factory ids` is dispatched before the rest of the CLI is imported:

```text
python3 bin/factory ids next TASK --all-refs -C <project-dir>
```

Every other command imports the adapter, model, and storage stack and
needs `pip install -e .` first.

IDs are compared by full filename rather than by number, so a task
moving `backlog -> done` is not a duplicate, while two artifacts sharing
one number under different slugs always are. `check` exits 1 on a
collision and 2 when the directory is not a project repository. On a
collision, renumber the unmerged side and keep the number already on the
integration branch.

## Project Initialization

`factory init` publishes project intent, enabled AI coding tools,
explicit technology statuses, and expected commands from flags,
`--intake`, `--from-specs`, and `--preset`. It renders a deterministic
specification before optional AI refinement. There is no setup wizard.

**Presets.** Web App, API Service, CLI, and Mobile App projects have
starter values that fill blank fields only, mark inserted technology
choices `Proposed`, and never overwrite owner input. Technology
selections trigger deterministic, non-blocking architecture and
compatibility insights. Expected command suggestions are reordered from
the selected stack but remain free-text and are not `Observed` evidence.

**Technology statuses.**

- `Approved` — explicitly selected by the owner. Only Approved choices
  drive dependency installation and stack configurators.
- `Preferred` — favored but not fixed.
- `Proposed` — suggested and awaiting a decision.
- `Unknown` — requires discovery.

Commands entered before source exists are marked `Expected`, never
`Observed`.

**Catalog.** Intake technology values come from a catalog of common
options plus free-text custom values. Each catalog option states its
available Factory capabilities (dependencies, verification,
configuration). Options without automation remain specification-only.
The current source catalog includes React, Vue, Angular, Next.js,
SvelteKit, Flutter, FastAPI, Django, Python CLI, NestJS, Spring Boot,
ASP.NET Core Web API, and Go with Gin. Database: PostgreSQL, MySQL,
SQLite, MongoDB. Infrastructure: Docker Compose, major cloud IaC
options, managed platforms, GitHub/GitLab container delivery.

**Generated project layout.**

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
└── .factory-state/
    ├── factory.yaml
    ├── tooling/
    │   ├── tool-policy.yaml
    │   ├── generated.yaml
    │   └── hooks/
    ├── intake/
    ├── standards/
    ├── decisions/
    ├── artifacts/
    ├── archive/
    └── tasks/
```

`AGENTS.md` is canonical for Codex, Cursor, and Grok. Claude Code receives
`.claude/CLAUDE.md`, which imports `@../AGENTS.md`. Cursor rules are not
generated by default. Grok skills are written to `.grok/skills/`.

Non-interactive creation can load owner input instead of an empty skeleton:

- `--intake FILE.yaml` loads a `ProjectIntake` document.
- `--from-specs FILE.md` publishes that markdown as `project-specs.md` and
  fills blank intake text fields from matching headings.
- `--preset web-app|api|cli|mobile` fills remaining blank stack and command
  fields as `Proposed`. It never marks a technology `Approved`.

Skills are emitted after a successful init unless `--no-skills` is passed.

Initialization creates the artifact bundle and initial discovery task, but
it does not run source generators, install project dependencies, or
implement application code. The project is not ready for implementation
until `factory ready` passes. See
[`project-repository-structure.md`](project-repository-structure.md) for
the layout in detail and [`tool-kits.md`](tool-kits.md) for tool kit
levels.

## AI Refinement

The configured adapter invokes the selected local CLI in an isolated
temporary directory:

- Codex through `codex exec` with a read-only sandbox.
- Cursor through `cursor-agent -p`.
- Claude Code through `claude -p` in plan mode with read access.
- Grok through `grok --single` in plan mode with a read-only sandbox.

Only the factory CLI publishes output. If refinement fails, the
deterministic draft remains available and no other provider is selected
automatically.

Interactive AI refinement starts only after the owner reviews the
deterministic draft and confirms the separate refinement configuration.
The progress screen displays the selected tool, current stage, elapsed
time, and the isolated read-only execution boundary. Codex progress is
read from its JSONL event stream while the validated final response is
read separately. Cancelling the progress screen terminates the child
process and leaves project files unchanged. Non-interactive runs emit
the same high-level stages to stderr.

Review screens use a Markdown viewer before publishing. AI refinement
can target the entire specification or selected section groups.
Interactive runs show every eligible changed level-two section and let
the owner accept or reject it independently; rejected and out-of-scope
sections preserve deterministic content exactly. `factory specs` can
save intake progress without publishing a new `project-specs.md`. A
successful publish snapshots the previous specification under
`.factory-state/intake/` and records the refiner, target sections,
accepted/rejected sections, timestamp, status, and input/output hashes
in the intake state.

## Safe Import

`factory import` scans an existing repository without writing. It
records manifests, source/test layout, existing AI instructions, the
current integration branch, and commands inferred from repository
evidence. The plan classifies paths as `create`, `keep`, `conflict`, or
`invalid`.

- Interactive runs require confirmation and offer `skip` or an
  owner-reviewed `merge` for each conflict.
- Non-interactive runs require `--apply` to write.
- Existing files are never overwritten automatically. Only content
  explicitly reviewed and selected as `merge` in the interactive editor
  is published.
- Proposed content for conflicts is written under
  `.factory-state/import/proposals/`.
- Instruction conflicts leave `.factory-state/import/INCOMPLETE`,
  causing validation to fail until the owner resolves them.

A project imported before the tooling bundle, or that never ran
`import --apply` after the bundle landed, will not have
`.factory-state/tooling/tool-policy.yaml`. `factory validate` reports
that as a missing tool policy. Moving the `.factory` pin does not
create the file. Re-run `factory import --apply --no-interactive` to
create missing tooling files without overwriting owner files, or write
the policy and run `factory tools configure --no-interactive`. This is
a project backfill, not a framework defect.

## Factory-state gc

`factory gc` compacts a large `.factory-state/`. It moves old `done`
tasks to `.factory-state/archive/tasks/done/` and, by default, companion
`REV` / `QA` / `SUM` artifacts that only reference those tasks to
`.factory-state/archive/artifacts/`. Requirements, decisions,
standards, and live tasks stay put. Archived IDs remain reserved, so
`factory ids` will not reuse them. It also deletes timestamped files
under `.factory-state/verification/runs/`. The current
`verification/latest.yaml` stays.

```text
factory gc -C project
factory gc --apply --keep 20 -C project
factory gc --apply --keep 0 -C project
```

The default is a dry-run inventory and plan. `--apply` moves tasks and
deletes verification runs.
`--keep N` leaves the N highest-numbered done tasks in the lifecycle
folders (default 20). `--keep 0` archives every done task. `--no-artifacts`
moves tasks only. `factory task archive` remains the primitive for one
task or a whole column.

`factory validate` checks review/QA references on `tasks/done/` only,
so archiving historical done tasks also drops those files out of that
gate.

## Factory Linking And Validation

Initialization prefers a Git submodule at `.factory/` and falls back to
a copy. `--copy` selects copying explicitly.

Agents must verify `.factory/AGENTS.md` before running workflows. If a
configured submodule is uninitialized, run:

```text
git submodule update --init .factory
```

During `factory import --apply`, a configured but uninitialized
`.factory` submodule is initialized only after the owner confirms the
import. Credential or network failure stops the import instead of
replacing the configured submodule with a copy.

`factory validate` checks the required structure, config schema,
enabled tool bridges, tooling policy and hashes, dependency and
verification state, standards, task lifecycle folders, import
completion, done-task review/QA references, and clarification schemas.
Retired `factory.yaml` keys
(`storage_backend`, `storage_dsn`, `budget_enforcement`, `budgets`)
still load and are reported as warnings. Unanswered clarification
questions are warnings rather than automatic lifecycle locks in v1.
Implementation readiness gaps are also warnings on `validate`.

`factory ready` is the implementation gate. It exits 0 only when discovery
`TASK-0001` has left backlog, at least one `REQ-*` artifact exists, a
non-discovery task in `todo` has acceptance criteria, and any `Approved`
source stack has a published scaffold (or the owner has not approved a
source stack yet).

## Local Development

```text
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

## Reference index

Per-command details live in dedicated docs:

- Dependencies: [`dependencies.md`](dependencies.md)
- Verification: [`verification.md`](verification.md)
- CI workflow: [`stack-configuration.md`](stack-configuration.md)
- Task lifecycle: [`task-lifecycle.md`](task-lifecycle.md)
- Clarifications: [`clarifications.md`](clarifications.md)
- Tool kits: [`tool-kits.md`](tool-kits.md)
- Pipeline milestones: [`pipeline.md`](pipeline.md)
- 0.3 migration: [`migration-0.3.md`](migration-0.3.md)
