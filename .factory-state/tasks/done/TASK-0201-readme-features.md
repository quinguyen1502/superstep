# Task

## Metadata

- Project: superstep
- Task ID: TASK-0201
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080, REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0033

## Objective

Bring the README feature list up to date. The README (en) and handbook home pages describe the CLI, chat attachments and storage, Agent hand-offs and AI review, with no stale claims. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- README Quick start, Features, Deploy and docs table
- handbook en/vi home cards
- CHANGELOG

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- README mentions install.sh and the superstep/sstep commands
- README covers attachments, storage backends and migrate, hand-offs, Help desk and AI review
- Node count and list checked
- handbook home en/vi in sync

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: implemented on `factory/task-0201-readme-features` from `develop`. README (en) now covers the CLI install and commands, chat attachments and db/fs/s3 storage with migrate, Agent hand-offs and the Help desk template, and AI review; handbook home en/vi link those pages. Node count (14 + read-only Code) verified against frontend META. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0189-task-0201.md`. QA: `.factory-state/artifacts/QA-0189-task-0201.md`.
