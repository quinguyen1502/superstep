# Task

## Metadata

- Project: superstep
- Task ID: TASK-0153
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-28
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

`superstep upgrade` moves an instance to a pinned version, with a backup first. When the new version never becomes healthy, the previous version and the backup come back, and the failed upgrade's logs are kept.

## Scope

### In Scope

- `superstep upgrade [--to <version>] [--images <tar>]` in the order of DEC-0068 decision 9:
  1. print the changelog range from the bundled `CHANGELOG.md`;
  2. call the backup function from TASK-0152;
  3. pull the pinned images, or load `--images`;
  4. restart so Alembic migrates;
  5. wait for `/api/health`;
  6. on failure, restore that backup, start the previous tag, and write `<dir>/upgrade-failed-<utc>.log`.
- `--check` reports whether the target differs and does not pull, back up, or restart.
- The default target is the CLI's own version.
- The v0.1 gate: volumes `langgraph-studio_pgdata`, `_redisdata` or `_apidata`, or Compose project `langgraph-studio`, are stopped without `-v` and brought up with those external names. The gate table has this one row.
- `--help` and `--json`. New catalog keys in en and vi.

### Out Of Scope

- Publishing the target images (TASK-0156).
- A second migration gate. Adding one is a new row later, not this task.
- Phase 2 commands.

## Inputs

- TASK-0152 backup and restore.
- TASK-0150 compose files and `instance.json`.
- DEC-0068 decision 9.
- Handbook section "Upgrade from v0.1.0" (`handbook/docs/en/operate/deploy.md`).
- `CHANGELOG.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: none
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- An upgrade that either lands on the target with a backup beside it, or returns to the previous tag with the data restored and a log file kept.

## Implementation Notes

- Bundle `CHANGELOG.md` in the package data so `--check` and the range print work offline. A missing range prints that the bundled log has no entry and continues.
- The health wait is the same helper as `install`. A failure is a timeout or `data.ok` not true.
- Rollback uses the archive this run just wrote. It does not look for an older archive.
- Update `instance.json` `version` only after health passes.

## Constraints

- Upgrade does not run without a backup from this command or a path the operator passed. This task always takes its own backup.
- Rollback does not try to reverse Alembic. It restores the backup and the previous image.
- Messages go through the catalogs. Both languages, same keys.

## Dependencies

- TASK-0152 merged to `develop`.

## Acceptance Criteria

- A fake upgrade to a newer tag calls backup, then pull, then restart, then health. On success, `instance.json` `version` is the target and the archive path is in the JSON output.
- When the fake health check fails, the previous tag is started, restore is called with the archive from this run, `instance.json` `version` is unchanged, and `upgrade-failed-*.log` exists with the fake logs.
- `--check` prints the difference and the fake records no pull, backup, or restart.
- `--images` loads and does not pull.
- An instance with volume `langgraph-studio_pgdata` is stopped without `-v` and the new compose file uses that external volume name.
- A target older than the running version exits non-zero before backup.
- `--help` and `--json` exist. New en and vi keys match.

## Validation Plan

- `cd sdk/python && python -m pytest -q`

## Assumptions

- The end-to-end proof from the previous published release to the current one, including a forced health failure, is the smoke test in TASK-0156. This task proves the sequence with a fake Docker.
- One bundled changelog is enough for the range text. Status's registry check stays in TASK-0151.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-28: owner asked to start the task. Branch `factory/task-0153-cli-upgrade` from `origin/develop` at `f3c2171` (PR #208). TASK-0152 is merged. Task moved to doing. No source edited.
- 2026-10-28: implemented `upgrade`. `upgrade_instance` calls `create_backup` before pull or load, and `restore_archive` on a failed health check. Tests were added with the task.
- 2026-10-28: validation passed on the uncommitted task tree. Tool policy: sdk/python pytest 80 passed, 2 skipped (3.08s, includes `test_upgrade`); backend pytest 787 passed, 57 skipped (333s); frontend lint exit 0 (5 existing warnings); frontend test 124 passed; frontend build exit 0; TypeScript SDK test 22 passed, build exit 0, typecheck exit 0.
- 2026-10-28: review REV-0139. No blocking findings. Approved for QA.
- 2026-10-28: QA QA-0139. Pass with follow-up. `test_upgrade.py` 10 passed inside the SDK run above.
- 2026-10-28: owner asked to finish the task through done, including validation, review, and QA. Not merged.

## Handoff Notes

- TASK-0155 calls `upgrade_instance` against a remote Docker host. A failed health check restores the archive from that run and writes `<dir>/upgrade-failed-<utc>.log`.
- `instance.json` `version` changes only after health passes. A target older than the running version exits before any backup.
- Review: `.factory-state/artifacts/REV-0139-task-0153.md`. QA: `.factory-state/artifacts/QA-0139-task-0153.md`.
- Not merged. Merge still needs an explicit owner request.
