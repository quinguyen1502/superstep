# Task

## Metadata

- Project: superstep
- Task ID: TASK-0152
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

`superstep backup` writes one archive that is enough to rebuild the instance, including the secret key. `restore` loads that archive back. A schedule keeps the last N archives.

## Scope

### In Scope

- `superstep backup [--to <dir>]` producing the archive in DEC-0068 decision 8: `manifest.json` format `1`, the database, the secret key, `.env` and `compose.yml`. File mode `0600`.
- SQLite via the engine's online backup inside the API container. Postgres via `pg_dump` custom format inside the Postgres container. The stack is not stopped for a successful dump.
- Free-space check before any stop or write. A short disk exits non-zero and leaves the stack running.
- `superstep restore <archive>` replaces the instance data from the archive, then starts the stack and waits for health. It refuses a newer manifest format or a server version newer than the CLI. It asks for the instance name (decision 6). `--yes` works only together with a matching `--name`.
- `--schedule daily|weekly --keep <n>` writes a shell script and a systemd user timer, or a cron entry when systemd is missing, and prunes archives beyond `<n>`. The script calls `docker` only.
- `--help` and `--json`. New catalog keys in en and vi.

### Out Of Scope

- Upgrade's use of this backup (TASK-0153). This task exposes a function upgrade can call.
- Installing the timer on a remote host (TASK-0155). This task installs it on the local host.
- Decrypting credentials to prove them. The archive carries the key; a later smoke test decrypts.

## Inputs

- TASK-0150 instance directory and `superstep.cli.docker`.
- DEC-0068 decisions 6 and 8.
- `backend/app/services/seed.py` and the volume layout in `docker-compose.yml` (what has to be in the archive).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0025-ui-only-delete-confirmation.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- A backup function TASK-0153 can call, and a restore that refuses a newer archive.
- A timer unit the deploy task can copy to a remote host.

## Implementation Notes

- The manifest records the server version from `instance.json`.
- Restore of a SQLite archive copies the file into the volume. Restore of a Postgres archive loads the dump. Both restore `.env` and the secret key before start.
- Prune runs after a successful scheduled backup, not before.

## Constraints

- A short disk fails before a container is stopped.
- The archive mode is `0600`. The secret key is a member, not a printed value.
- Confirmation matches decision 6. There is no confirm field on an HTTP API; restore does not call one.
- Messages go through the catalogs. Both languages, same keys.

## Dependencies

- TASK-0150 merged to `develop`.

## Acceptance Criteria

- A fake SQLite instance and a fake Postgres instance each produce an archive with `manifest.json`, the database member, the secret key, `.env` and `compose.yml`. The archive mode is `0600`.
- When the fake disk is smaller than the estimate, backup exits non-zero and the fake records no stop and no file.
- Restore of a manifest format `2`, or a server version newer than the CLI, exits non-zero and does not write.
- Restore without the typed name exits non-zero. `--yes` without `--name` exits non-zero. `--yes --name <instance>` proceeds.
- After a fake restore, the written `.env` secret key equals the archive's key.
- `--schedule daily --keep 2` writes a timer (systemd in the fake, cron when the fake has no systemd) and the prune keeps two archives.
- `--help` and `--json` exist. New en and vi keys match.

## Validation Plan

- `cd sdk/python && python -m pytest -q`

## Assumptions

- Online `pg_dump` and the SQLite backup API are consistent enough for phase 1. A dump that fails falls back to stopping, copying, and starting, and that fallback still happens only after the free-space check.
- The fresh-VM proof that workflows and credentials survive is the smoke test in TASK-0156. This task proves the archive contents and the restore rules.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-27: owner asked to start the task. Branch `factory/task-0152-cli-backup` from `origin/develop` at `d836e8f` (PR #206; TASK-0151 is in `6f8351e`). Task moved to doing. No source edited.
- 2026-10-27: implemented `backup`, `restore`, and `--schedule`. `create_backup` and `restore_archive` are the functions TASK-0153 calls. Tests were added with the task and were not run.
- 2026-10-28: validation passed on the uncommitted task tree. Tool policy: sdk/python pytest 70 passed, 2 skipped (2.05s, includes `test_backup`); backend pytest 787 passed, 57 skipped (335s); frontend lint exit 0 (5 existing warnings); frontend test 124 passed; frontend build exit 0; TypeScript SDK test 22 passed, build exit 0, typecheck exit 0.
- 2026-10-28: review REV-0138. No blocking findings. Approved for QA. Task stays in doing.
- 2026-10-28: QA QA-0138. Pass with follow-up. `test_backup.py` and `test_cli.py` 28 passed. Task stays in doing.
- 2026-10-28: owner asked to move the task to done. Review REV-0138 has no blocking findings. QA-0138 passed with the documented restore, shell-disk, and real-Docker risks. Not merged.

## Handoff Notes

- TASK-0153 calls `superstep.cli.backup.create_backup` before it pulls, and `restore_archive` on a failed health check. Both raise `BackupError` for policy failures and `DockerError` for Docker failures.
- A successful backup sets `instance.json` `secret_backed_up`, which `doctor` already treats as a backup record.
- Review: `.factory-state/artifacts/REV-0138-task-0152.md`. QA: `.factory-state/artifacts/QA-0138-task-0152.md`.
- Not merged. Merge still needs an explicit owner request.
