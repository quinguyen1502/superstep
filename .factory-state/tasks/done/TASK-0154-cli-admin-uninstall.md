# Task

## Metadata

- Project: superstep
- Task ID: TASK-0154
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-28
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

An operator can create an admin, reset a password, or list admins when nobody can sign in, and can remove the instance without deleting its volumes unless they name it.

## Scope

### In Scope

- `backend/app/admin_cmd.py`, run as `python -m app.admin_cmd create|reset-password|list`. It follows `app/worker.py`: open the database through the existing deps, call a service, no HTTP route.
- The service uses `UserRepository` and `core.security`. `create` adds an admin or promotes an existing user. `reset-password` sets a new password that passes `password_problem`. A generated password is printed once. `list` prints e-mail and role, never a hash.
- `superstep admin create|reset-password|list` runs that module with `docker compose exec` in the API container of the instance.
- `superstep uninstall` runs `docker compose down` and keeps volumes and the instance directory's `.env`. `uninstall --purge` also removes the volumes and the instance directory, after the operator types the instance name (DEC-0068 decision 6). `--yes` works only with a matching `--name`.
- Backend tests for create, reset and list. CLI tests with a fake exec.
- `--help` and `--json`. New catalog keys in en and vi.

### Out Of Scope

- A studio Settings screen, a new HTTP route, or a confirm field on a DELETE.
- Personal access tokens (phase 2).
- Remote uninstall (the local command is enough; TASK-0155 may call it over the same Docker transport later).

## Inputs

- TASK-0150 instance directory and `superstep.cli.docker`.
- DEC-0068 decisions 6 and 10.
- `backend/app/worker.py`, `backend/app/services/seed.py`, `backend/app/repositories` user repository, `docs/backend-architecture.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0025-ui-only-delete-confirmation.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- An admin can be created from the host when the studio login is unusable.
- Uninstall without `--purge` leaves the volumes in place.

## Implementation Notes

- Put the rules in a service the process entry calls. Do not import FastAPI from that service.
- The CLI prints the password the process writes to stdout, once, and does not store it in `instance.json` or `cli.json`.
- `--json` for `create` and `reset-password` includes `password` once. `list` does not have a password field.

## Constraints

- DEC-0009: the router layer is not involved. No new error code in `core/errors.py`, because there is no HTTP call.
- `tests/test_layers.py` must pass.
- Confirmation matches decision 6.
- Messages on the CLI go through the catalogs. Both languages, same keys. The process entry's stdout is the password and the list; the CLI translates its own prompts.

## Dependencies

- TASK-0150 merged to `develop`.

## Acceptance Criteria

- `create` on an empty database inserts an admin and the password passes the policy. A second `create` for the same e-mail promotes and resets, and does not insert a duplicate.
- `reset-password` changes the hash. `list` returns e-mail and role and the output has no hash.
- The CLI command execs `python -m app.admin_cmd` in the API service. A fake exec's stdout password is shown once and is absent from `instance.json`.
- `uninstall` calls `compose down` without `-v` and leaves the instance directory. `uninstall --purge` without the typed name exits non-zero and removes nothing. `--yes` without `--name` exits non-zero. `--yes --name <instance>` removes the volumes and the directory.
- `--help` and `--json` exist. New en and vi keys match.
- `tests/test_layers.py` passes.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py`
- `cd sdk/python && python -m pytest -q`

## Assumptions

- The API container image already contains the server code, so exec of `app.admin_cmd` works once this module is in the image. The all-in-one image and `superstep-api` both install the backend package.
- One admin e-mail per invocation is enough. Bulk create is not required.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-28: task-start. Branch `factory/task-0154-cli-admin-uninstall` cut from `origin/develop` at `6c20a42` (merge of PR #209). No source edited.
- 2026-10-28: implemented `admin` and `uninstall` on this branch. Not committed.
- 2026-10-28: tool policy passed on the uncommitted tree. Backend pytest 790 passed, 57 skipped (339.14s). sdk/python pytest 88 passed, 2 skipped (4.44s). Frontend lint exit 0 with 5 existing warnings, frontend test 124 passed, frontend build exit 0. TypeScript SDK test 22 passed, build exit 0, typecheck exit 0.
- 2026-10-28: REV-0140 approved for QA. No blocking findings. QA-0140 pass with follow-up.
- 2026-10-28: owner asked to move the task to `done` and open the PR. Not merged.

## Handoff Notes

- The smoke test in TASK-0156 can call `admin list` against a started instance.
- `superstep admin create|reset-password|list` execs `python -m app.admin_cmd` (`superstep` on single, `api` on full). The password is printed once and is not stored. `uninstall` is `compose down` without `-v`. `uninstall --purge` needs the typed name, or `--yes` with a matching `--name`, then `down -v`, `docker volume rm` for recorded names, and removal of the instance directory.
- Review: `.factory-state/artifacts/REV-0140-task-0154.md`. QA: `.factory-state/artifacts/QA-0140-task-0154.md`.
- Not merged. Merge still needs an explicit owner request.
