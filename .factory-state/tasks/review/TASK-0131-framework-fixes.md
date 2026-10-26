# Task

## Metadata

- Project: superstep
- Task ID: TASK-0131
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0066 (clean `factory validate`)
- Design IDs: none
- Architecture IDs: DEC-0064 (point 4 now uses `gc --no-runs`)

## Objective

Fix the four small framework issues found in TASK-0129 and TASK-0130 (owner request in chat on 2026-10-26: "Bạn sửa
luôn đi").

## Changes

- Upstream sw-ai-factory 513545e (pushed to its `main`):
  - `skills apply` records the hash of each file it writes in `.factory-state/skills/generated.yaml`. A file that still
    has that hash is updated when its template changes. Before, it was a conflict that needed `--force` (seen in #162).
    Hand-edited files are still preserved, and `skills validate` lists the files to update.
  - `gc --no-tasks` only deletes verification runs; `gc --no-runs` only archives tasks.
  - `deps` no longer looks for manifests in build output (`dist/`, `build/`, `coverage/`, `.next/`, `.svelte-kit/`).
    The SDK build's `sdk/typescript/dist/cjs/package.json` caused a drift warning before.
  - `deps` records an absolute executable by its name in `installed.yaml`.
- `.factory` vendored at 513545e.
- `.factory-state/skills/generated.yaml`: the 70 skill files, recorded by `factory skills apply` (all in sync).
- `.factory-state/dependencies/installed.yaml`: refreshed by `factory deps apply`, now with no absolute paths.
- DEC-0064 point 4: keep `verification/runs/` with `factory gc --no-runs`.

## Acceptance Criteria

- `factory validate` has no dependency drift warning after a local SDK build.
- `installed.yaml` holds no absolute path.
- A changed skill template updates unedited copies without `--force`.
- `factory gc --no-tasks` plans only the run deletions.

## Validation Results

- Upstream: `python -m unittest discover -s tests`, 144 tests OK. The four new tests fail without the change.
- `factory validate`: passed. The only warning is "no todo task".
- `deps validate`, `verify validate`, `tools validate`, `skills validate` (70 in sync), `ids check --all-refs`: passed.
- `factory gc --no-tasks` (dry run): tasks left in place; 28 verification runs to delete. Not applied (DEC-0064).
- `grep` for `/Users`, `/private` and `/usr/` in `installed.yaml`: no match.

## Review And QA

- Review: the owner reviews the PR. No separate REV artifact (framework update, no source change).
- QA: the validation above and CI on the PR.
