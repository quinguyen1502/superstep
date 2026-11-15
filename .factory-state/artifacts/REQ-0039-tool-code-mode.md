# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0039
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: owner question "Then can we add a mode for writing and executing code in a node?" (2026-10-19), after the explanation of the Tool node's Python function mode

## Summary

A third mode for the Tool node, **Code**, next to `function` and `http`. The user writes a short Python function in the node, and each run executes it in an isolated container. It gets the run state and returns a value that goes into the node's output field.

## Problem Or Opportunity

- **Function mode** only offers functions registered on the server with `@register_tool` (`backend/app/engine/tools.py`). New logic needs a code change and a deploy.
- **HTTP and MCP** need a service someone else hosts.
- Small transformations have no home in the canvas: parse a string, reshape a JSON object, compute a score, pick fields. They push users to stand up a service or ask for a server change.

## Scope

### In Scope

- `mode: "code"` on the Tool node:
  - `data.code` holds the source; the entry point is `def main(state): ...`;
  - the return value is written to `output_field`.
- Execution in the Docker sandbox from TASK-0015 (`backend/app/engine/sandbox/container.py`):
  - a fresh container per call;
  - read-only root, `--cap-drop ALL`, `no-new-privileges`;
  - limits on memory, CPU and pids, and a wall-clock time limit;
  - an empty environment that never holds server secrets.
- A small in-container runner:
  - reads the state as JSON on stdin and calls `main(state)`;
  - writes one JSON result to stdout;
  - captures `print()` output and the traceback.
- The trace shows each call's result, captured stdout (truncated) and, on failure, the traceback as the node error.
- Editor: a Python code field with syntax highlighting, a starter template, and **Test with sample state**, which runs the code once against the run panel's input and shows the result or the error.
- Validation before a run:
  - the code is not empty;
  - it compiles (`compile()` only; nothing is executed on the server);
  - it defines `main`;
  - the editing user has `code.write`;
  - the configured runtime is available (Docker, or the explicit host subprocess mode).
- en and vi strings. New error codes go in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- README (en and vi): what the mode is for, its limits, and how to enable it.

### Out Of Scope

- Languages other than Python.
- Changing the existing `function` mode or the `@register_tool` registry.
- Installing packages per node at run time (CLAR-0001: fixed image only).
- Network access from code, and credentials passed to code (CLAR-0001: not in the first version).
- Keeping state between calls: no shared filesystem and no warm interpreter between runs.
- A full IDE: no debugger, breakpoints or language server.

## Stakeholders Or Users

- Workflow authors who hold `code.write` (admins by default).
- Project owner or administrator, who enables the feature and sets limits.
- Viewers and other users who run a shared workflow containing a Code node.

## Current Context

- Tool node runtime: `backend/app/engine/nodes.py` (`t == "tool"`, modes `http` and the default `function`).
- Validator: `backend/app/engine/validator.py` (Tool node checks).
- Sandbox: TASK-0015 / REQ-0009, `container.build`, `captured`, `sandbox_env`, `allow_secret`. The flags are `STUDIO_IMPORT_*` (image, memory, CPUs, pids, network, host dir).
- Node settings: REQ-0019 (retry, wait, timeout, cache TTL per working node).
- Idempotency keys for side effects: TASK-0021 (`engine/effects.py`).
- Roles and permissions: `backend/app/core/permissions.py` (DEC-0023):
  - roles: admin, editor, viewer;
  - workflow access: owner, editor or viewer share.
- Runs execute in the API process or the worker (`services/run_worker.py`). Both need Docker for this mode.
- Templates: save-as-template strips secrets (TASK-0028); the code would travel with templates, exports and imports.
- Outbound HTTP elsewhere goes through the SSRF guard (`core/net.py`, REQ-0027). Traffic from inside the container would not.

## Desired Behavior

- In the Tool node config the user picks **Code**, writes `main(state)` and picks an output field.
- A run reaching the node starts a sandbox container:
  - it passes the state and waits for at most the node timeout (or a server default);
  - the returned value is stored in the output field;
  - the run continues.
- Failures stop the node with a clear error and the run follows the node's retry settings: an exception in user code, a non-JSON return value, the time limit, the memory limit, or the runtime being unavailable.
- The run panel and trace show the result, the captured `print()` output (truncated) and the traceback.
- **Test with sample state** gives the same result as a real run for the same state, and writes no run history.

## Business Rules

Owner decisions from CLAR-0001 (2026-10-19):

- **Who may write code:** a new global permission `code.write`.
  - Admins have it by default; editors and viewers do not.
  - It is added to `core/permissions.py` and shown in the admin role matrix.
  - It is checked when a user saves, imports or uses a template with a Code node, or changes its code, and not only in the UI.
  - A user without it can still see the code read-only, run the workflow, and move or delete the node. The API refuses an added or changed `code` field.
- **Network:** always off. The container runs with `--network none`, and no node or workflow can change that.
- **Packages:** a fixed image set by `STUDIO_CODE_IMAGE`. Nothing is installed at run time.
  - The default image is a small `studio-code` image on `python:3.12-slim` with the standard library plus `pydantic` and `python-dateutil` (no `requests`, since the network is off).
  - The editor shows which packages the image has.
- **Credentials:** none in the first version. The process gets no credential values and no server environment variables.
- **Without Docker:** a host subprocess is allowed only when the admin sets it explicitly. Users must always be able to see that their code is not isolated (see Host Subprocess Mode below).

Other rules:

- User code never runs inside the API or worker process. It always runs in a separate container or child process.
- The state passed in is a JSON copy; the code cannot change the run except through its return value.
- Size limits apply to state in, result out, and stdout. For example 1 MB for the result and 64 KB for stdout; final values are set in the task.
- A workflow shared with a viewer can still be run by that viewer. The code runs with the sandbox's rights, never the viewer's or the owner's.

## Host Subprocess Mode

The owner chose to allow running without Docker and asked that users be made aware of it. The owner accepted the rules below on 2026-10-19, all eight points included.

**Turning it on**

- It needs two flags: `STUDIO_ENABLE_CODE_NODES=1` and `STUDIO_CODE_RUNTIME=subprocess`.
- There is never an automatic fallback. With `docker` (the default) and no Docker available, Code nodes fail validation with a clear error.

**Limits that still apply**

- The process starts with an empty environment (no `JWT_SECRET`, `DATABASE_URL` or `STUDIO_*`).
- Its working directory is a temporary folder that is deleted afterwards.
- On Linux, rlimits cap memory, CPU time, open files and processes.
- The time limit kills the whole process group.
- The README states what this mode cannot stop:
  - network access;
  - reading files the server user can read;
  - a weaker memory limit on macOS.

**How users and admins are told**

1. **Server log:** one `WARNING` at start-up, saying that code nodes run on the host without isolation.
2. **API:** `GET /api/meta` (or the existing tools endpoint) returns `code_runtime`, one of `docker`, `subprocess` or `off`. The UI reads this one value; nothing else guesses the runtime.
3. **Editor:** the Code mode config shows a warning Alert. It uses theme tokens (`--warning`), in en and vi, and reads roughly "Code runs directly on the server, without isolation". It cannot be dismissed.
4. **Canvas:** a Code node carries a small warning badge with a tooltip explaining the risk.
5. **Mode picker:** the **Code** entry shows a "Not isolated" badge next to its name.
6. **Run results:**
   - each Code call's trace row shows `runtime: subprocess`;
   - the run panel shows one warning line per run that used it;
   - the run record keeps the runtime, so history shows it later.
7. **Admin Settings:** a sandbox status card shows the code runtime (Docker, host subprocess, or off), the image, and the limits, with a short risk note when it is `subprocess`.
8. **Audit log:** the first Code node run after a server start in this mode records `system.code_runtime_subprocess`, so admins can see when the mode was in use.

## Constraints

- Docker is the only isolation runtime (REQ-0009 decision). gVisor and Firecracker stay out of scope. The host subprocess mode is not isolation; it exists only for servers without Docker and is always labelled as such.
- Mock or offline mode must keep working. A workflow without Code nodes must not need Docker.
- Layers per DEC-0009:
  - the runner and the container call live in `engine/`;
  - the permission check lives in `services/`;
  - schema changes, if any, go through Alembic.
- UI: shadcn components and theme tokens only (DEC-0008). The code editor component must follow the theme in light and dark.

## Acceptance Criteria

- A Code node returning `state["message"].upper()` writes the upper-cased message to its output field, and the next node can use it.
- `print()` output and a raised exception appear in the trace. The run fails with the traceback, and retry settings apply.
- An endless loop is stopped at the time limit; allocating past the memory limit is stopped. Both are reported as node errors.
- In Docker mode, code cannot read server environment variables (for example `JWT_SECRET`), cannot read files outside the container, and cannot reach the network (`--network none`).
- A user without `code.write` gets an error code, shown in en and vi, when they save or import a workflow that adds or changes a Code node. Running such a workflow still works.
- With the default runtime and no Docker, a Code node fails validation with a clear message, and other workflows run as before.
- In host subprocess mode:
  - the process environment has no server secrets, and the time limit kills it;
  - `code_runtime` is `subprocess`;
  - the editor Alert, the canvas badge, the trace label, the run warning and the admin status card are all visible;
  - the start-up warning is logged.
- pytest covers runner I/O, limits, isolation, permissions and both runtimes; Docker-dependent tests skip when Docker is missing. Playwright covers editing, Test with sample state, a run, and the subprocess warnings.

## Edge Cases

- `main` missing, wrong signature, or a syntax error: shown at validation, before the run starts.
- A return value that is not JSON-serialisable (a set, a datetime, a custom object): node error naming the type.
- Very large state or result: refused with a size error, not truncated silently.
- Cancelling a run while the container is running: the container is killed (the same path as imports).
- Many parallel Code nodes, for example inside For each: container start-up cost and a cap on concurrent containers.
- Loop iterations call the code each time; the trace shows each call as its own row.
- A Code node in a template or export: the code is kept, and the permission rule applies when it is used or imported.
- An admin removes `code.write` from a role later: existing Code nodes keep running; members of that role can no longer change them.
- The runtime changes between save and run (for example Docker removed): the run fails at validation and names the missing runtime; nothing falls back silently.

## Assumptions

- A new container per call is acceptable, at about 0.5–1.5 s overhead per call on a warm image. A warm pool is a later optimisation if needed.
- The container uses its own image setting, `STUDIO_CODE_IMAGE`, separate from the import image.
- The feature is off by default behind `STUDIO_ENABLE_CODE_NODES`, like repo import. `STUDIO_CODE_RUNTIME` is `docker` (default) or `subprocess`.

## Open Questions

Answered 2026-10-19 in `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`:

- Who may write code: the `code.write` permission (admins by default).
- Network: always off.
- Packages: a fixed image set by `STUDIO_CODE_IMAGE`.
- Credentials: none.
- Without Docker: an explicit host subprocess mode, with the warnings in Host Subprocess Mode.

Closed 2026-10-19 (owner in chat):

- Default image packages: the standard library plus `pydantic` and `python-dateutil`, as proposed.
- Host Subprocess Mode warnings: accepted as proposed, all eight points including the audit entry.

## Owner Acceptance

- 2026-10-19: the owner accepted REQ-0039 with the CLAR-0001 answers, the default image packages and the Host Subprocess Mode warnings. Planned 2026-10-19 as TASK-0053 to TASK-0056 (DEC-0041); the owner approved the tasks and accepted DEC-0041 the same day.
- 2026-10-19: Implemented and merged into `develop` by the owner's request: TASK-0053 (PR #61), TASK-0054 (PR #62), TASK-0055 (PR #63) and TASK-0056 (PR #64). The accepted residual risk is the Host Subprocess Mode: it is not a sandbox, and the README and the eight warnings say so.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`
- `.factory-state/decisions/DEC-0041-tool-code-mode.md`
- Tasks: `.factory-state/tasks/todo/TASK-0053-code-runtime-docker.md`, `TASK-0054-code-write-permission.md`, `TASK-0055-code-mode-editor.md`, `TASK-0056-code-subprocess-runtime.md`
- `.factory-state/artifacts/REQ-0009-sandboxed-imports.md`
- `.factory-state/artifacts/REV-0029-task-0015-container-sandbox.md`
- `.factory-state/artifacts/REQ-0019-node-execution-settings.md`
- `.factory-state/artifacts/REQ-0027-review-hardening.md` (SSRF guard)
- `backend/app/engine/tools.py`, `backend/app/engine/nodes.py`, `backend/app/engine/sandbox/container.py`, `backend/app/core/permissions.py`
