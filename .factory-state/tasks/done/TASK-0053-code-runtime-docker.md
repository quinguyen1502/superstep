# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0053
- Status: done
- Phase: nodes
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0039
- Design IDs: none (backend only)
- Architecture IDs: DEC-0041, DEC-0009, REQ-0009

## Objective

Run a Tool node's Python code (`mode: "code"`) in a Docker container with no network. The returned value goes to the output field, and the trace shows stdout and errors.

## Scope

### In Scope

- `engine/sandbox/code_runner.py`: reads `{source, state}` from stdin, calls `main(state)`, and writes one JSON result line. It captures `print()` and the traceback.
- `engine/code_runtime.py`: `run_code` and `CodeResult`, plus the Docker backend:
  - built on `container.build`, `captured` and `failure_event`;
  - `--network none`, an empty env, and only the runner mounted.
- `core/config.py`:
  - `STUDIO_ENABLE_CODE_NODES`, `STUDIO_CODE_RUNTIME` (only `docker` in this task; `subprocess` comes in TASK-0056);
  - `STUDIO_CODE_IMAGE`, `STUDIO_CODE_MEMORY`, `STUDIO_CODE_CPUS`, `STUDIO_CODE_PIDS`, `STUDIO_CODE_MAX_SECONDS`;
  - `code_runtime()`.
- `docker/studio-code/Dockerfile`: `python:3.12-slim` with pinned `pydantic` and `python-dateutil`, tagged `studio-code:1`.
- `engine/nodes.py`: the Tool node `mode == "code"` branch. Trace event fields `stdout` (truncated) and `runtime`.
- `engine/validator.py`:
  - non-empty source, at most 64 KB;
  - `compile()` passes;
  - a top-level `main` exists;
  - the runtime is not `off`;
  - Docker can be reached (the check is cached briefly).
- Size limits: state 1 MB, result 1 MB, stdout 64 KB.
- A cancelled run kills the container.
- Error codes, each in CATALOG, `docs/api-errors.md` and both locales:
  - `CODE_RUNTIME_OFF`;
  - `CODE_RUNTIME_UNAVAILABLE`;
  - `CODE_INVALID`;
  - `CODE_FAILED`;
  - `CODE_TIMEOUT`;
  - `CODE_MEMORY`;
  - `CODE_RESULT_NOT_JSON`;
  - `CODE_TOO_LARGE`.
- Tests for runner I/O, limits, isolation and validation. Tests that need Docker skip when it is missing; runner-only tests run everywhere.
- Docs: README en and vi (enabling the mode, building the image, Compose and the Docker socket), plus `.env.example`.

### Out Of Scope

- The permission check (TASK-0054), the editor UI (TASK-0055), and the subprocess backend and its warnings (TASK-0056).
- Network, credentials and per-node packages (CLAR-0001).

## Inputs

- REQ-0039, CLAR-0001, DEC-0041.
- `engine/sandbox/container.py`, `engine/nodes.py`, `engine/validator.py`, `engine/runtime.py` (cancel path), `core/config.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0039-tool-code-mode.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0041-tool-code-mode.md`, `.factory-state/artifacts/REQ-0009-sandboxed-imports.md`
- Decisions: DEC-0009, DEC-0041
- Discovery: `.factory-state/artifacts/REV-0029-task-0015-container-sandbox.md`
- Clarifications: `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`

## Expected Outputs

- New: `engine/code_runtime.py`, `engine/sandbox/code_runner.py`, `docker/studio-code/Dockerfile`, `tests/test_code_node.py`.
- Changes: `engine/nodes.py`, `engine/validator.py`, `core/config.py`, `core/errors.py`, `docs/api-errors.md`, both locales, README en and vi, `.env.example`.

## Implementation Notes

- The runner must not import anything from `app`. It runs inside the image, where `app` does not exist.
- Reject non-JSON return values with the type name. Do not fall back to `str()`.
- A Code node is a normal runtime-policy type: retry, timeout and cache apply. It is not in `SIDE_EFFECT_TYPES`.

## Constraints

- No user code ever runs in the API or worker process; the server only calls `compile()`.
- Layers per DEC-0009: the engine imports only `core`.
- Workflows without Code nodes must not need Docker.

## Dependencies

- None. TASK-0054 can be built in parallel.

## Acceptance Criteria

- A Code node returning `state["message"].upper()` writes that value to its output field, and the next node reads it.
- `print()` output shows in the trace. An exception fails the node with the traceback, and retry applies.
- An endless loop stops at the time limit and an oversized allocation stops at the memory limit; both are node errors.
- In the container, `os.environ` has no `JWT_SECRET` or `STUDIO_*`, `socket.create_connection` fails, and the server's files cannot be seen.
- With `STUDIO_ENABLE_CODE_NODES` unset, or Docker missing, a Code node fails validation with a clear code. Other workflows still run.
- `tests/test_layers.py` and `tests/test_api_envelope.py` pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`, with Docker running locally so the container tests run.
- Python 3.12 import check: `uv run --python 3.12` (CI uses 3.12).
- `docker build -t studio-code:1 docker/studio-code`

## Assumptions

- About 0.5–1.5 s of overhead per call on a warm image is acceptable (REQ-0039).

## Open Questions

- None.

## Activity Log

- 2026-10-19: Created from REQ-0039 (owner: "Split REQ-0039 into tasks (plan-tasks) on the same PR #60"); not started.
- 2026-10-19: Task set and DEC-0041 approved by the owner ("Approve the task set and DEC-0041").
- 2026-10-19: Started on `factory/task-0053-code-runtime-docker` (owner: "Do task 0053, CI is out of quota").
- 2026-10-19: Implemented. The runner goes in as `python -I -c`, so nothing is mounted. Cancel uses `Ports.cancelled`. Review REV-0050, QA QA-0050 (pass). PR open; not merged.
- 2026-10-19: Merged in PR #61 (owner: "Merge PR #61").

## Handoff Notes

- TASK-0055 reuses `run_code` for Test with sample state, and TASK-0056 adds the subprocess backend behind the same interface.
