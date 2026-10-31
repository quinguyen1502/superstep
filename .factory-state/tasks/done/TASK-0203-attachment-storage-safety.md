# Task

## Metadata

- Project: superstep
- Task ID: TASK-0203
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074, DEC-0009

## Objective

Fix the storage findings 1, 3, 7 and 9 of the external review of v0.10.0 and v0.10.1: the orphan sweep could delete files that are not attachments, a visitor upload wrote on the event loop, nginx refused bodies above 10 MB with its own page, and changing the folder, bucket or prefix made older files unreadable.

## Scope

### In Scope

- orphan sweep limited to service-made keys at the configured location
- refuse an fs folder that is or contains the data folder; warn on an empty S3 prefix
- location recorded per file with a migration and start-up backfill; migrate between locations of one backend
- public upload offloaded with asyncio.to_thread
- nginx body limit above every API ceiling with a JSON 413
- docs en/vi

### Out Of Scope

- The other findings of the v0.10.0/v0.10.1 review; each group has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- The sweep deletes only keys of the service's form, under the configured location, with no row
- A data-holding folder is refused by probe, put and sweep
- Files stay readable after the folder, bucket or prefix changes, and migrate moves them
- A visitor upload writes off the event loop
- nginx lets every allowed upload reach the API

## Validation

- A regression test for each finding that fails before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the external review of v0.10.0 and v0.10.1.
- 2026-10-31: implemented on `factory/task-0203-attachment-storage-safety` from `develop`. The orphan sweep deletes only service-made keys at the configured location, refuses a data-holding folder and warns on an empty S3 prefix; each file records its location (migration 0048, start-up backfill) and migrate moves files between locations of a backend; visitor uploads are stored with asyncio.to_thread; nginx allows WEB_MAX_BODY_SIZE (110m) with a JSON 413. `factory verify run --profile full` passed. The owner asked to fix the confirmed review findings and merge each task when CI is green. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0191-task-0203.md`. QA: `.factory-state/artifacts/QA-0191-task-0203.md`.
