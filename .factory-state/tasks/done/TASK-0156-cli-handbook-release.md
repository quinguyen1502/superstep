# Task

## Metadata

- Project: superstep
- Task ID: TASK-0156
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-28
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

An operator can install the CLI with one command, the `v*` release publishes it next to the server, and the handbook and the deploy docs start from the CLI. CI runs the CLI unit tests and an install-and-upgrade smoke test.

## Scope

### In Scope

- `scripts/install.sh`: installs uv when Python is missing, then `uv tool install 'superstep[cli]==<version>'`. It refuses native Windows and prints the WSL guidance. The one-liner is `curl` of this script.
- Publish `ghcr.io/quinguyen1502/superstep-api` from `backend/Dockerfile` and `ghcr.io/quinguyen1502/superstep-web` from `frontend/Dockerfile` in `.github/workflows/image.yml`, with the same tag rules as the existing images.
- Publish the `superstep` Python package on `v*` tags at the server version (DEC-0068 decision 1). The workflow checks that the tag, `sdk/python/src/superstep/_version.py` and `backend/pyproject.toml` are the same number. `sdk-py-v*` stays. Release notes say the package version moves from the `0.1.0` line to the server version.
- Set `_version.py` to the current server version as part of that wiring.
- `scripts/cli_smoke.py`, run from CI against the locally built all-in-one image:
  - `install --yes` for `single` reaches `/api/health`;
  - a second install refuses;
  - `backup`, then `restore` onto a fresh directory, and a stored credential still decrypts;
  - `upgrade` to the same image with a forced health failure restores the previous tag and the data;
  - `doctor` reports a fixture with `STUDIO_ENV` unset, the placeholder `JWT_SECRET`, and a missing Docker socket.
- Unit tests of `sdk/python` run in a new `.github/workflows/cli.yml` job on pull requests.
- Handbook en and vi: an operate page for the CLI (install, upgrade, backup, the smoke-test shape of a CI recipe) and the deploy page starts from the CLI. The same nav entry in `mkdocs.yml` and `mkdocs.vi.yml`.
- `docs/deploy/README.md` and `README.vi.md` gain a short pointer to the CLI for a Docker host. The platform buttons stay.
- CHANGELOG `## Unreleased` › Added. The decision record is DEC-0068; do not write a second one.

### Out Of Scope

- Phase 2 commands, tokens and browser sign-in.
- A smoke test that SSHes to a second machine.
- Changing Fly.io, Render, Railway, Zeabur or Heroku configs.

## Inputs

- TASK-0149 through TASK-0155.
- DEC-0068 decisions 1 and 4.
- `.github/workflows/image.yml`, `.github/workflows/sdk-publish.yml`, `scripts/image_smoke.sh`, `handbook/mkdocs.yml`, `handbook/mkdocs.vi.yml`, `CHANGELOG.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0003-factory-link-copy.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- A one-line install, two new image names, a CLI smoke job, and handbook pages in en and vi.

## Implementation Notes

- The smoke test forces the health failure through a flag the upgrade command already accepts for tests, or by pointing the target at an image that exits. It does not publish that flag as an operator feature beyond `--images` and the documented test hook.
- The credential check creates a credential through the studio API after install, restores onto a fresh directory, and reads it back. That proves the secret key travelled with the archive.
- Handbook Vietnamese follows the existing glossary (REQ-0045). The page tree matches across the two nav files.

## Constraints

- The handbook build is strict.
- Do not publish from a pull request. The `v*` job publishes; the pull-request job tests.
- Platform one-click configs stay as they are.

## Dependencies

- TASK-0149, TASK-0150, TASK-0151, TASK-0152, TASK-0153, TASK-0154 and TASK-0155 merged to `develop`.

## Acceptance Criteria

- `scripts/install.sh` on a machine with uv installs the extra and leaves a `superstep` on `PATH`. With neither Python nor uv, the script installs uv. On a fake native Windows it exits non-zero and mentions WSL.
- `image.yml` builds `superstep-api` and `superstep-web`. The tag rules match the existing matrix.
- The `v*` publish job refuses a tag that differs from `_version.py` or `backend/pyproject.toml`.
- `scripts/cli_smoke.py` passes against a local all-in-one image: healthy install, second install refused, restore that still decrypts a credential, forced upgrade failure that returns the previous tag and keeps the data, and the three doctor findings.
- `cli.yml` runs `sdk/python` unit tests on a pull request.
- The handbook strict build passes. The en and vi CLI pages have the same headings. CHANGELOG lists the CLI. The deploy docs point a Docker-host reader at `superstep install` and still document the platform buttons.

## Validation Plan

- `cd sdk/python && python -m pytest -q`
- `cd handbook && .venv/bin/zensical build && .venv/bin/zensical build -f mkdocs.vi.yml`
- `python scripts/cli_smoke.py` against the local image

## Assumptions

- GHCR credentials and PyPI trusted publishing already used by `image.yml` and `sdk-publish.yml` cover the new jobs. This task does not create new secrets.
- The smoke test uses the all-in-one image for the healthy path. The full topology is covered by the unit tests in TASK-0150 until the new images are pulled in a later run of `image.yml`.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-28: task-start. Branch `factory/task-0156-cli-handbook-release` cut from `origin/develop` at `0a02a88` (merge of PR #211). TASK-0149 through TASK-0155 are on that commit. No source edited.
- 2026-10-28: implemented. Tool-policy checks passed (backend pytest 793 passed / 54 skipped; SDK pytest 105 passed / 2 skipped; frontend lint, test, and build; TypeScript SDK test, build, and typecheck). Handbook strict build passed for en and vi. `scripts/cli_smoke.py` passed against the local all-in-one image `superstep:ci`.
- 2026-10-28: REV-0142 no blocking findings. QA-0142 pass with follow-up. Owner asked to move the task to done and open the PR. Not merged.

## Handoff Notes

- After this task, phase 1 of REQ-0079 is complete. Phase 2 is still not planned.
- `scripts/install.sh` pins `superstep[cli]==0.9.0` unless `SUPERSTEP_VERSION` is set. It refuses native Windows and installs uv when `uv` is missing.
- `sdk/python` version is `0.9.0`, the same number as `backend/pyproject.toml`. The `v*` job in `sdk-publish.yml` refuses a tag that differs from either file. `sdk-py-v*` is unchanged. Nothing publishes from a pull request.
- `image.yml` adds `superstep-api` and `superstep-web` to the publish matrix with the same tag rules. The pull-request job does not push.
- `SUPERSTEP_UPGRADE_HEALTH_FAIL=1` forces upgrade rollback. It is not an operator flag.
- Generated Compose mounts the alias (`data`, `pgdata`, `redisdata`, `apidata`) and keeps the Docker volume name on `name:`. Restore `chown`s copied files to `studio` because `docker compose cp` writes them as root.
- Smoke evidence: install, `INSTALLED` on the second run, backup, purge, install into a new directory with the same name, restore, credential decrypt, forced rollback to `0.9.0`, and the three doctor findings.
- Not merged. Merge still needs an explicit owner request.
- Local `develop` stays checked out in `/Users/quinguyen/workspace/superstep-req-0075`. Do not fast-forward that worktree. REQ-0076 stays on `factory/task-0157-parallel-tool-waves`.
