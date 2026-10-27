# Task

## Metadata

- Project: superstep
- Task ID: TASK-0150
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

`superstep install` brings up one instance on a Docker host, and `start`, `stop`, `restart` and `logs` operate that instance. A second install refuses. An existing hand-written compose directory can be adopted without moving its data.

## Scope

### In Scope

- `superstep.cli.docker`, a subprocess wrapper for `docker` and `docker compose`. Tests use a fake. No Docker SDK.
- `install` for topologies `single` (default) and `full`, and `--sandbox` only with `full` (DEC-0068 decision 4). Flags: `--yes`, `--answers <file>`, `--name`, `--dir`, `--url`, `--admin-email`, `--port`, `--images <tar>`.
- Host checks (decision 5): Docker and Compose v2 are required. Memory under 1 GiB or free disk under 2 GiB warns and does not block. A taken port is named, and another port is offered. With `--yes`, a taken default port requires `--port`.
- Generated secrets and `.env` mode `0600`, instance directory mode `0700`, `instance.json` as decision 3. `STUDIO_ENV=production`. The one-time admin password is printed once and stored only in `.env` (decision 6).
- The compose file pins the images from decision 4. No `build:` path. `--images` loads a tar and does not pull. New full-stack volumes are `<name>_pgdata`, `<name>_redisdata`, `<name>_apidata`.
- After start, wait for `/api/health` and print the URL. `--json` includes `url` and, on a fresh admin, `admin_password` once.
- A second install against an existing `instance.json` refuses and does not overwrite `.env`.
- `adopt <compose dir>` (and `install --adopt`) writes `instance.json` and does not recreate volumes or rotate secrets.
- `start`, `stop`, `restart`, and `logs [service] [--follow]`.

### Out Of Scope

- status, config, doctor (TASK-0151).
- backup, restore, upgrade (TASK-0152, TASK-0153).
- Publishing `superstep-api` and `superstep-web` (TASK-0156). This task's tests load local tags.
- SSH deploy (TASK-0155). `remote` stays `null`.

## Inputs

- TASK-0149 parser, catalogs and output helpers.
- DEC-0068 decisions 3, 4, 5 and 6.
- `deploy/compose/docker-compose.single.yml`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0033-integration-branch-develop.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- An instance directory a later task can read: `compose.yml`, `.env` mode `0600`, `instance.json`.
- Compose wrappers for the installed project.

## Implementation Notes

- Interactive questions are topology, public URL and admin e-mail. `--yes` requires those as flags or in the answers file.
- Do not write `~/.superstep/secret.key` or the import directory. Server data stays in the Docker volume.
- `JWT_SECRET` and `STUDIO_SECRET_KEY` are never printed, including in `--json`.
- The admin password is the one exception in decision 6.

## Constraints

- Secrets come from `secrets.token_hex(32)` and are written only to files mode `0600`.
- The CLI does not read the database. Health is an HTTP GET.
- Python >= 3.9. Messages go through the catalogs from TASK-0149, both languages, same keys.

## Dependencies

- TASK-0149 merged to `develop`.

## Acceptance Criteria

- With a fake Docker, `install --yes` for `single` and for `full` (with and without `--sandbox`) writes a compose file pinned to the version, an `.env` of mode `0600`, and an `instance.json`. The directory mode is `0700`.
- The same command a second time exits non-zero and leaves `.env` unchanged.
- `--images` records a load and no pull. A missing Docker or Compose v2 exits non-zero before any file is written.
- A taken port is reported with the process name the fake supplies. `--yes` without `--port` exits non-zero in that case. A free `--port` is written into the compose file.
- Memory and disk warnings are printed and the install still succeeds.
- `adopt` writes `instance.json` and does not call volume create, secret rotation, or compose up.
- `start` waits until the fake health check passes and the URL is printed. `stop`, `restart` and `logs --follow` call compose with the instance project. `--json` and `--help` exist on each new command, and the new catalog keys match in en and vi.
- No output contains `JWT_SECRET` or `STUDIO_SECRET_KEY`. The admin password appears once.

## Validation Plan

- `cd sdk/python && python -m pytest -q`

## Assumptions

- Image names that are not published yet are still written as in decision 4. Pulling them is TASK-0156. Tests inject local tags.
- The operator has Docker Compose v2 on the host where this command runs. This task does not SSH.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).

## Handoff Notes

- TASK-0151, TASK-0152 and TASK-0154 can start once this is merged. They share `instance.json` and `superstep.cli.docker`.
- Do not start a branch until the owner confirms this set. The next skill is `task-start`.
