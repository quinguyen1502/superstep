# Task

## Metadata

- Project: superstep
- Task ID: TASK-0155
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-28
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

`superstep deploy ssh://user@host` installs or upgrades an instance on a remote Docker host. The remote host runs Docker and nothing else from this project.

## Scope

### In Scope

- `superstep deploy ssh://user@host` with the same topology, `--yes`, `--answers`, `--images` and `--upgrade` flags as install and upgrade.
- The instance directory is created on the remote host at `~/.superstep/instances/<name>/` (DEC-0068 decision 5). `instance.json` `remote` is the `ssh://` URL.
- Engine calls use `DOCKER_HOST=ssh://user@host`. The CLI does not install Python or itself on the remote host.
- When the remote `instance.json` is absent, deploy runs install. When it is present, deploy runs upgrade. `--upgrade` forces upgrade and fails if the instance is absent.
- A scheduled backup requested in the same command installs the shell timer from TASK-0152 on the remote host over SSH. The script calls `docker` on that host and checks the volume names.
- `--images` is loaded through the SSH transport, with no pull.
- `--help` and `--json`. New catalog keys in en and vi.

### Out Of Scope

- Fly.io, Render, Railway, Zeabur, Heroku and Kubernetes (REQ-0079).
- Installing the CLI on the remote host.
- Copying a git checkout to the remote host.

## Inputs

- TASK-0150 install and TASK-0153 upgrade.
- The timer script from TASK-0152.
- DEC-0068 decision 5.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: none
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- One command that turns a fresh remote Docker host into an instance, and the same command later upgrades it.

## Implementation Notes

- Tests use a fake SSH and a fake Docker. They assert `DOCKER_HOST`, the remote directory, and that no command installs a package on the remote.
- The remote directory is written over SSH (`mkdir` and file copy). Compose then runs with `DOCKER_HOST` set, using that remote directory only when the transport requires the files beside the daemon. Keep one writer: the CLI writes the remote directory first, then calls Docker.
- A failed SSH connection exits non-zero before any remote file is written.

## Constraints

- Nothing besides Docker and Compose v2 is required on the remote host.
- Secrets stay in the remote `.env` mode `0600`. They are not printed.
- Messages go through the catalogs. Both languages, same keys.

## Dependencies

- TASK-0150 and TASK-0153 merged to `develop`.
- The timer script exists from TASK-0152, which TASK-0153 already depends on.

## Acceptance Criteria

- Deploy to a fake host with no instance sets `DOCKER_HOST=ssh://user@host`, writes the remote instance directory, and runs the install sequence. `remote` in `instance.json` is that URL. No fake command installs Python or the CLI.
- A second deploy runs the upgrade sequence and does not generate new secrets.
- `--upgrade` with no remote instance exits non-zero.
- `--images` is loaded through the fake transport and no pull is recorded.
- `--schedule daily --keep 7` writes the timer on the remote host, and the script contains the volume names and no `pip` or `uv`.
- An SSH failure before the first write leaves the fake host empty.
- `--help` and `--json` exist. New en and vi keys match.

## Validation Plan

- `cd sdk/python && python -m pytest -q`

## Assumptions

- Docker's SSH transport can load an image and run Compose against the remote daemon. The smoke test in TASK-0156 covers a local daemon. An end-to-end two-machine SSH test is not part of CI.
- The remote home is the one `ssh` reports. `--dir` overrides it.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-28: task-start. Branch `factory/task-0155-cli-deploy-ssh` cut from `origin/develop` at `8a6b91d` (merge of PR #210). No source edited.
- 2026-10-28: implemented `deploy` on this branch.
- 2026-10-28: tool policy passed on the uncommitted tree. Backend pytest 790 passed, 57 skipped (335.63s). sdk/python pytest 99 passed, 2 skipped (4.24s). Frontend lint exit 0 with 5 existing warnings, frontend test 124 passed, frontend build exit 0. TypeScript SDK test 22 passed, build exit 0, typecheck exit 0.
- 2026-10-28: REV-0141 approved for QA. No blocking findings. QA-0141 pass with follow-up.
- 2026-10-28: owner asked to take the task through done and open the PR. Not merged.

## Handoff Notes

- TASK-0156 documents this command and does not change its transport.
- `superstep deploy ssh://user@host` probes SSH before any write. An absent remote `instance.json` runs install. A present one runs upgrade. `--upgrade` fails when the instance is absent. `DOCKER_HOST` is the SSH URL. The remote directory is `~/.superstep/instances/<name>/` unless `--dir` is set. `instance.json` `remote` is that URL. `.env` is mode `0600`. The admin password is printed once and is not stored in `instance.json`.
- Compose reads a temporary local cache because the compose client is local. The cache is deleted at the end. The timer script from TASK-0152 is written on the remote host and calls `docker` there.
- Review: `.factory-state/artifacts/REV-0141-task-0155.md`. QA: `.factory-state/artifacts/QA-0141-task-0155.md`.
- Not merged. Merge still needs an explicit owner request.
