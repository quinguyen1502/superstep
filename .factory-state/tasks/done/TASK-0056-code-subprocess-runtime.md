# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0056
- Status: done
- Phase: nodes
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0039
- Design IDs: none (it reuses the Alert, Badge and Card patterns)
- Architecture IDs: DEC-0041, DEC-0009, DEC-0008

## Objective

Allow Code nodes on servers without Docker through an explicit host subprocess runtime, and always show users and admins that the code is not isolated.

## Scope

### In Scope

- A subprocess backend in `engine/code_runtime.py`:
  - it runs `sys.executable -I code_runner.py` with an empty env, a temporary working directory and a new session;
  - a timeout kills the whole process group;
  - on Linux it sets `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NOFILE` and `RLIMIT_NPROC`;
  - it is selected only by `STUDIO_CODE_RUNTIME=subprocess`.
- The eight warnings from REQ-0039 Host Subprocess Mode:
  1. one `WARNING` log at start-up;
  2. `code_runtime: "subprocess"` from `GET /api/meta/runtime`;
  3. an editor Alert (`--warning`) in the Code config, which cannot be dismissed;
  4. a canvas node badge with a tooltip;
  5. a "Not isolated" badge on the Code mode in the picker;
  6. `runtime: subprocess` on trace rows, one run-panel warning per run, and a `code_runtime` column on runs (Alembic migration) shown in history;
  7. an admin Settings card with the runtime, the image and the limits, plus a risk note;
  8. an audit entry `system.code_runtime_subprocess` on the first Code call after each server start.
- en and vi strings, plus `activity.actions.system_code_runtime_subprocess`.
- README en and vi: the risks this mode cannot stop (network, files the server user can read, a weaker memory limit on macOS), and when to use it.
- pytest for both runtimes sharing the runner protocol, and for the env, the timeout, the audit entry and the run column. An e2e spec with the server in subprocess mode checks the Alert, the badges and the trace label.

### Out Of Scope

- Any automatic fallback from Docker to subprocess.
- Network blocking in subprocess mode.

## Inputs

- REQ-0039 Host Subprocess Mode, DEC-0041 decisions 3 and 6.
- `engine/code_runtime.py` (TASK-0053), the editor components (TASK-0055), `services/audit_service.py`, the run model and migrations, `pages/settings/`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0039-tool-code-mode.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0041-tool-code-mode.md`
- Decisions: DEC-0041
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`

## Expected Outputs

- The subprocess backend and the start-up log.
- A migration adding `runs.code_runtime`.
- The audit entry.
- The UI badges, Alert and admin card.
- Locales, README, pytest, and `e2e/code-subprocess.spec.ts`.

## Implementation Notes

- The audit entry is "first call since start", so keep a process-level flag; per worker process is fine.
- The admin card can live in an existing Settings section or a new one (`sections.ts`); pick the smaller change.

## Constraints

- Code never runs inside the API or worker process itself.
- Schema changes go through Alembic (DEC-0009).

## Dependencies

- TASK-0053 and TASK-0055.

## Acceptance Criteria

- With `STUDIO_CODE_RUNTIME=subprocess`, a Code node runs without Docker and the process env holds no server secrets.
- The time limit kills the process, including any child processes it started.
- All eight warnings appear, and each is covered by a test.
- With the default runtime and no Docker, there is no fallback: Code nodes fail validation.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- Playwright with the server in subprocess mode.

## Assumptions

- `preexec_fn` rlimits are acceptable, since the server is not multi-threaded at fork time in the worker. Otherwise use a small wrapper script that sets the limits before exec.

## Open Questions

- None.

## Activity Log

- 2026-10-19: Created from REQ-0039; not started.
- 2026-10-19: Task set and DEC-0041 approved by the owner ("Approve the task set and DEC-0041").
- 2026-10-19: Started on `factory/task-0056-code-subprocess-runtime`, branched from TASK-0055 (owner: "Do the tasks as one chain: 54, 55, 56").
- 2026-10-19: Implemented: the subprocess runtime and all eight warnings, plus migration `0029_run_code_runtime`. Review REV-0053, QA QA-0053 (pass). PR open; not merged.
- 2026-10-19: Merged in PR #64 (owner: "Merge PR #62, #63, #64 in turn").

## Handoff Notes

- After this task, update REQ-0039 to Implemented and record owner acceptance.
