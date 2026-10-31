# Task

## Metadata

- Project: superstep
- Task ID: TASK-0211
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0048, REQ-0065, REQ-0078, REQ-0079, REQ-0080, REQ-0081 (TASK-0203 to TASK-0210)
- Design IDs: none
- Architecture IDs: DEC-0033, DEC-0073, DEC-0076

## Objective

Version 0.10.2. Release 0.10.2 as asked by the owner: bump version files and the install.sh pin to 0.10.2, CHANGELOG heading, release PR to main, tag v0.10.2 and a GitHub Release. SDKs stay 0.1.0: the run API they wrap is unchanged (no change to the run or trigger routes or to sdk/typescript since v0.10.1; the Python package change is in the CLI only).

## Scope

### In Scope

- version files and install pin
- CHANGELOG 0.10.2 heading
- roadmap
- release PR, tag, GitHub Release

### Out Of Scope

- Product changes; the release contains PRs #258 to #265 (TASK-0203 to TASK-0210) only.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Version files and the install pin say 0.10.2 and CHANGELOG has ## 0.10.2 (2026-10-31)
- Full verify and the full e2e suite pass
- CI on the bump PR is green

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to release v0.10.2.
- 2026-10-31: released: #266 into develop (e92f6761), release PR #267 into main (13e15b19), tag `v0.10.2` and the
  GitHub Release. GHCR 0.10.2: superstep, -api, -web, -sandbox all present and publicly pullable. Render demo deploy
  dep-dbirhi3ncjis73ctpv70 live on 13e15b19, /api/health version 0.10.2 ok. The Publish SDKs run 41190025511 on the
  tag waits for the `pypi` environment approval (owner).
- Review: `.factory-state/artifacts/REV-0199-task-0211.md`. QA: `.factory-state/artifacts/QA-0199-task-0211.md`.
