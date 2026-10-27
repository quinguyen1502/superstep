# Task

## Metadata

- Project: superstep
- Task ID: TASK-0151
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

An operator can see whether the instance is healthy, change its settings, and get a list of concrete installation problems.

## Scope

### In Scope

- `superstep status`: version, health of each service, database and queue kind, disk used by the volumes, and whether a newer release exists.
- `superstep config get|set|list`. A setting that the running stack reads only at start is followed by a restart. Secrets are masked (DEC-0068 decision 6). `--show-secrets` shows them, including under `--json`.
- `superstep doctor`, reporting:
  - `JWT_SECRET` equal to `dev-secret-change-me`, empty, or missing;
  - `STUDIO_SECRET_KEY` missing from `.env` and no `secret.key` recorded in the last backup;
  - `STUDIO_ENV` not `production`;
  - a public URL that is not `https`, except `localhost`;
  - `STUDIO_TRUSTED_PROXIES` missing on a `full` topology;
  - the Docker socket missing when the topology is `full` with `sandbox`, or when the compose file mounts the socket for Code nodes;
  - clock skew over 30 seconds between the host and the API container;
  - a configured provider base URL that does not answer. The check skips, with a note, when the host is offline. It does not print the credential.
- Newer-release check uses the bundled changelog when present, and the registry when the network works. Offline, status says it could not check and still exits 0.
- `--help` and `--json` on each command. New catalog keys in en and vi.

### Out Of Scope

- Changing the topology or upgrading (TASK-0153).
- Creating admins (TASK-0154).
- Scheduled backups (TASK-0152). Doctor only reads whether a backup has recorded the secret key.

## Inputs

- TASK-0150 instance directory and `superstep.cli.docker`.
- DEC-0068 decisions 2, 3 and 6.
- `docs/deploy/env-vars.md`, `backend/app/core/config.py` (`PLACEHOLDER_SECRET`).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0010-api-envelope-error-codes-i18n.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- `status`, `config` and `doctor` against an instance directory from TASK-0150.

## Implementation Notes

- `config set` writes `.env` and keeps mode `0600`. It restarts only when the changed key is one the process reads at start (`JWT_SECRET`, `STUDIO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `STUDIO_ENV`, `STUDIO_TRUSTED_PROXIES`). Other keys are written and the command says a restart was not required.
- Provider checks call the base URL already stored for the instance (env `OPENAI_BASE_URL` or the default OpenAI host when `OPENAI_API_KEY` is set). They do not decrypt the studio credential store.

## Constraints

- Masked secrets stay masked without `--show-secrets`.
- The CLI does not read the database.
- Messages go through the catalogs. Both languages, same keys.

## Dependencies

- TASK-0150 merged to `develop`.

## Acceptance Criteria

- `status --json` includes the version, each service, `database`, `run_bus`, volume disk, and a release check that is either a version or `unknown` when the fake network fails. Exit 0 in both cases.
- `doctor` reports three fixtures: `STUDIO_ENV` unset, `JWT_SECRET=dev-secret-change-me`, and a sandbox topology whose compose file has no Docker socket. A clean fixture exits 0.
- Clock skew of 31 seconds is reported. 30 seconds is not.
- An unreachable provider is reported. A fake offline network skips that check and says so.
- `config list` masks `JWT_SECRET` and `STUDIO_ADMIN_PASSWORD`. `config get JWT_SECRET --show-secrets` prints the value. `config set STUDIO_PUBLIC_URL` updates `.env`, keeps mode `0600`, and does not restart. `config set JWT_SECRET` restarts.
- `--help` and `--json` exist on each command. New en and vi keys match.

## Validation Plan

- `cd sdk/python && python -m pytest -q`

## Assumptions

- "A newer release" compared with no network is `unknown`, not a failure. TASK-0156 is what publishes the release the check looks for.
- Doctor's provider check is the env base URL, not every credential row in the database.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).

## Handoff Notes

- TASK-0153 `--check` can reuse the release comparison this task adds.
- Do not start a branch until the owner confirms this set. The next skill is `task-start`.
