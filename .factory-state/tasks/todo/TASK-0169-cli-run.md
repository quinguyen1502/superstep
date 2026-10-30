# Task

## Metadata

- Project: superstep
- Task ID: TASK-0169
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

`superstep run` starts a workflow as the signed-in user and follows the same socket as the run panel. `runs list`, `show` and `cancel` use the run routes that already exist.

## Scope

### In Scope

- DEC-0071 decision 5.
- `run`, `runs list`, `runs show` and `runs cancel`.
- The `websockets` pin on the `cli` extra, chosen from a release that still declares Python 3.9, recorded in the task activity log.
- Exit codes 0, 1, 2, 3 and 4 as DEC-0071 decision 5. Catalog lines for the trace and for a waiting prompt, en and vi, same keys.

### Out Of Scope

- Answering a Human node from the CLI.
- A new REST start route. The start message is the websocket body the panel already sends.
- Changing cancel-on-disconnect. The CLI keeps the socket open until the run ends.

## Inputs

- REQ-0079 group C (`run`, `runs`).
- DEC-0071 decision 5.
- `backend/app/api/routes/runs_ws.py`, `backend/app/api/routes/runs.py`, the token loader from TASK-0167.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: `DEC-0068-superstep-cli.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- A run started with the PAT, its final status as the process exit code, and `--json` limited to one final object.
- `runs cancel` stops a waiting or running run the user can see.

## Implementation Notes

- Resolve an id or an exact name inside this command's module (`AMBIGUOUS` when two names match). If a shared helper is already on `develop` from TASK-0168, call it. Do not edit that task's branch from here.
- `--input -` reads one JSON object from stdin. A missing `--input` sends `{}`.
- Do not log the websocket URL. The token stays in the query string the server already accepts and nowhere else.
- Tests drive a fake socket or the backend TestClient websocket. No Docker.

## Constraints

- The new dependency is `websockets` on the `cli` extra only. Record the pin and its `Requires-Python` in the activity log before adding it.
- Python >= 3.9 for every other command. argparse. No Click or Typer.
- `--json` writes nothing until the final object. Trace lines go to stderr and only with `--follow`.

## Dependencies

- TASK-0167 merged into `develop`.
- May proceed in parallel with TASK-0168, TASK-0170 and TASK-0171. If two of those edit `sdk/python/src/superstep/cli/__init__.py`, stack the later branch on the earlier one or split registration into each command module the way `install.py` already does. Do not edit the same lines on two unmerged branches.

## Acceptance Criteria

- `run <id> --input sample.json --follow` sends that input on `/ws/run`, prints a stderr line for `run_started` and for each node event, and exits 0 when the final status is `ok`.
- Status `error` exits 1, `waiting` exits 2 and the prompt is on stderr, a local timeout exits 3 after a cancel message, `cancelled` exits 4. `paused` exits 0.
- Without `--follow`, those trace lines are absent. With `--json`, stdout is one object and includes `run_id`, `status` and `final_state`.
- The token does not appear in stdout, stderr or a log line the test captures.
- `runs list` prints the pending rows. `runs list --workflow <name>` prints that workflow's history. `runs show` prints one run. `runs cancel` returns the cancel payload and a later show is `cancelled` or no longer waiting.
- `--help` on `run` and `runs` includes an example.

## Validation Plan

- `cd sdk/python && python -m pytest -q` including the new run tests.
- A backend websocket test only if the CLI test cannot see the cancel-on-disconnect rule. The server behaviour is already shipped; do not change it.

## Assumptions

- The designer step is skipped. The trace is one catalog line per event, not a panel layout.
- Default `--timeout` 300 matches the requirement's non-zero timeout exit. The flag overrides it.
- `paused` is a successful step run, so it exits 0. `waiting` is not success.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071). Not started.

## Handoff Notes

- Register the command from its own module, as `admin.py` does, so a parallel task can add another module without editing the same lines.
- The websockets pin is part of the commit. Do not leave it floating.
