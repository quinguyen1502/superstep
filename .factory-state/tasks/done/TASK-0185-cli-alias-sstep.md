# Task

## Metadata

- Project: superstep
- Task ID: TASK-0185
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079 (CLI)
- Design IDs:
- Architecture IDs: DEC-0068, DEC-0071

## Objective

Add `sstep`, a short alias of the `superstep` command (owner request on 2026-10-30, "Ok, thêm đi").

## Scope

### In Scope

- `[project.scripts]` in `sdk/python/pyproject.toml`: `sstep` runs `superstep.cli:main`.
- `scripts/install.sh` says the alias is installed.
- Handbook CLI page en and vi (same heading structure), CHANGELOG Unreleased.
- A test that both commands point to the same entry point.

### Out Of Scope

- Renaming the package or the `superstep` command.

## Inputs

- `sdk/python/pyproject.toml`, `scripts/install.sh`, `handbook/docs/*/operate/cli.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`

## Expected Outputs

- After install, `sstep --help` and `superstep --help` run the same CLI.

## Constraints

- No new dependency. en and vi pages keep the same headings.

## Dependencies

- None.

## Acceptance Criteria

- `sstep` is listed in `[project.scripts]` with the same entry point as `superstep`; the test passes.
- The handbook CLI pages in en and vi mention it and keep identical heading levels.

## Validation Plan

- `cd sdk/python && .venv/bin/python -m pytest -q tests/test_release.py`

## Activity Log

- 2026-10-30: created from the owner's request.
- 2026-10-30: implemented on `factory/task-0185-cli-sstep-alias` from `develop`. Adds the sstep console script with the same entry point as superstep; installer message, handbook CLI page en and vi, CHANGELOG. `factory verify run --profile full` passed. The owner asked for the alias on 2026-10-30 and authorized its merge. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0154-task-0185.md`. QA: `.factory-state/artifacts/QA-0154-task-0185.md`.
