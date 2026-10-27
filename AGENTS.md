# Project Agents

This project uses the AI Software Factory framework in `.factory/`. This file is the canonical project instruction entrypoint for Codex, Cursor, and Grok. Claude Code imports it through `.claude/CLAUDE.md`.

Init creates a valid factory skeleton. It is not ready for implementation until `factory ready` passes.

## Required Rules

- Before applying factory workflows, verify `.factory/AGENTS.md` exists and read it.
- If `.factory/AGENTS.md` is missing and `.factory` is configured as a submodule, initialize it with `git submodule update --init .factory`.
- If initialization requires credentials, network access, or approval, request it before implementation.
- If `.factory/AGENTS.md` remains unavailable, stop implementation and record a blocker in `.factory-state/`.
- Read `vision.md`, `project.md`, `roadmap.md`, and the current task before work.
- Treat `project-specs.md` as source onboarding context and preserve explicit approval statuses.
- Discover project context and commands from repository evidence; do not treat expected commands as observed.
- Read `.factory-state/artifacts/` selectively by following task and artifact references.
- Store generated workflow state under `.factory-state/`, never `.factory/`.
- Record assumptions, blockers, open questions, review results, and QA evidence in artifacts.
- Do not create standalone tasks or blocker artifacts for command trials, missing local authentication, sandbox or network retries, or other transient assistant execution mechanics unless they materially block an active delivery task.
- Allocate new artifact IDs after `git fetch --all --prune` with `factory ids next <TYPE> --all-refs`. Do not guess the next number.
- Use task branches named `factory/task-<id>-<short-name>` unless project standards define another convention.
- Do not merge without explicit human approval.
- When the owner approves a merge and the task is not in `done` yet, move it to `done` on that same PR (one commit), wait for the checks, then merge. Never open a separate PR only to move a task to `done`.
- UI work: use shadcn/ui components and theme tokens only; no hard-coded colours; new status colours go in as shadcn-style CSS variables (`--success`, `--warning`, `--info`). Follow `docs/ui-conventions.md` (DEC-0008) and run its review checklist.
- Every delete feature (delete, remove, revoke, unlink) must make the user type the item's name to confirm: use the shared `ConfirmDeleteDialog` / `useConfirmDelete` (button disabled until the exact name is typed, en+vi strings). The confirmation is UI-only: the API stays a plain DELETE with no confirm field (`docs/ui-conventions.md` rule 7, DEC-0025).
- Backend work: keep the layers in `docs/backend-architecture.md` (DEC-0009): routers call services, services call repositories/engine, no FastAPI in services, no raw SQL (SQLAlchemy models + Alembic migrations for every schema change). `tests/test_layers.py` must pass.
- Coding rules: **DRY, SOLID, KISS**. One source of truth per concern, minimal abstractions, no speculative layers. Concretely:
  - API responses: use the shared envelope (`schemas/envelope.py`) and the central handlers in `api/error_handlers.py`; no per-route try/except or hand-built error JSON.
  - Errors: add new codes only to `core/errors.py` `CATALOG` (English message), `docs/api-errors.md`, and both `frontend/src/locales/*.json` (`errors.<CODE>`). `tests/test_api_envelope.py` enforces this.
  - Frontend: call the API only through `lib/api.ts` `api()` (it unwraps the envelope). Show errors via `errorText`/`eventErrors` (`lib/i18n.ts`). Put every UI string in `locales/en.json` + `locales/vi.json` with identical keys; no literal UI text in components.
- Do not start implementation source work until `factory ready` exits 0, unless the owner explicitly overrides that gate.

## Workflow Skills

Use the matching installed skill when the user asks for that job. If the skill files are missing, run `factory skills apply`.

- `onboard-specs` — convert `project-specs.md` into vision, project, roadmap, REQ/DES/ARCH, and tasks.
- `create-requirement` — write one requirement artifact.
- `plan-tasks` — split an approved requirement into verifiable tasks.
- `discuss` — analysis only; no edits.
- `next-task` — recommend the next lifecycle task.
- `task-start` — branch and move a task to doing; do not implement.
- `scoped-change` — implement or fix, then stop before validation.
- `task-validation` — run declared project checks.
- `task-review` — write a review artifact.
- `task-qa` — write a QA artifact.
- `finish-pr` — rebase, squash, and mark the existing PR Ready.
- `cleanup-branches` — prune merged or obsolete local branches.

## Factory References

- Shared behavior: `.factory/AGENTS.md`
- Agent roles: `.factory/agents/`
- Workflows: `.factory/workflows/`
- Templates: `.factory/templates/`
- Framework docs: `.factory/docs/`
