# Quickstart (5 minutes)

Walk from an empty machine to a project ready for AI-driven task work.
Follow the steps in order; each block is a single copy-paste.

## 1. Install the CLI

```bash
git clone <factory-repository-url> sw-ai-factory
cd sw-ai-factory
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Verify it works:

```bash
factory --help
```

## 2. Create a project

`factory init` publishes the artifact bundle from flags. Agents pass
`--no-interactive` so the same command works in a terminal and in CI:

```bash
factory init demo-project --no-interactive --preset api --from-specs ./brief.md
```

The project lands next to `sw-ai-factory/`. It contains `AGENTS.md`,
`vision.md`, `project.md`, `roadmap.md`, `project-specs.md`, and
`.factory-state/` with an initial discovery task in `backlog/`.

## 3. Complete the initial discovery task

Every new project starts with `TASK-0001-confirm-project-context` in
`backlog/`. Move it forward from the project directory:

```bash
cd demo-project
factory task move TASK-0001 doing
```

Edit the task's Markdown file to record what you confirmed, then move it
to `review`, `qa`, and `done` the same way. Convert `project-specs.md`
with the `onboard-specs` skill, then run `factory ready` before
implementation.

## 4. (Optional) Install dependencies and verify

When the repository already has manifests, install project-local
dependencies and run the deterministic checks:

```bash
factory deps plan
factory deps apply --allow-network
factory verify plan --profile full
factory verify run --profile full
```

`factory stack plan` previews CI and database configuration derived from
`Approved` technology choices. `factory stack apply` publishes that
configuration and keeps existing files as proposals.

## Where to go next

- [`pipeline.md`](pipeline.md) — every milestone in detail.
- [`cli.md`](cli.md) — every subcommand and flag.
- [`task-lifecycle.md`](task-lifecycle.md) — branch, review, and QA flow.

## Troubleshooting

- **`factory: command not found`** — activate the venv
  (`source .venv/bin/activate`) or run `python -m pip install -e .`.
- **A stage reports "INCOMPLETE"** — a previous `apply` left proposals to
  resolve. Run the matching `validate` action to see what remains, or
  read `.factory-state/<stage>/INCOMPLETE`.
