# Task

## Metadata

- Project: superstep
- Task ID: TASK-0202
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080, REQ-0081 (TASK-0191 to TASK-0201)
- Design IDs: none
- Architecture IDs: DEC-0033, DEC-0074

## Objective

Version 0.10.1. Release 0.10.1 as asked in chat (Nhưng lên v0.10.1): bump version files and the install.sh pin to 0.10.1, CHANGELOG heading, release PR to main, tag v0.10.1 and a GitHub Release. SDKs stay 0.1.0: the run API they wrap is unchanged. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- version files and install pin
- CHANGELOG 0.10.1 heading
- roadmap
- release PR, tag, GitHub Release

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Version files and the install pin say 0.10.1 and CHANGELOG has ## 0.10.1 (2026-10-31)
- Full verify and the full e2e suite pass
- CI on the bump PR is green

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: released: #255 into develop (3d388a87), release PR #256 into main (b27e266e), tag `v0.10.1` and the
- 2026-10-31: implemented on `factory/task-0202-post-release` from `develop`. Version 0.10.1 released: bump #255, release #256 to main, tag v0.10.1, GitHub Release; GHCR and Render checked; PyPI publish awaits owner approval. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
  GitHub Release. The Publish SDKs run on the tag waits for the `pypi` environment approval (owner).
- Review: `.factory-state/artifacts/REV-0190-task-0202.md`. QA: `.factory-state/artifacts/QA-0190-task-0202.md`.
