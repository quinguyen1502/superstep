# Task

## Metadata

- Project: superstep
- Task ID: TASK-0200
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074, DEC-0009, DEC-0033

## Objective

Stream S3 attachment uploads in parts. Uploads are read in pieces with the size check kept, and the s3 backend uploads large files as multipart, aborting on failure. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- chunked read_upload into a spooled file
- stream-capable put on db/fs/s3
- explicit multipart with abort in S3Store
- STUDIO_ATTACHMENT_S3_MULTIPART_MB
- archive restore streams
- MinIO tests incl. abort
- docs en/vi

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Files above the threshold go up in parts and read back intact
- A failure mid-upload aborts and leaves no incomplete upload
- The size check runs before and during reading

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: implemented on `factory/task-0200-s3-multipart` from `develop`. S3 uploads above STUDIO_ATTACHMENT_S3_MULTIPART_MB (default 8) use explicit multipart with abort on failure; uploads are read in 1 MB pieces into a spooled file with the ceiling enforced while reading. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0188-task-0200.md`. QA: `.factory-state/artifacts/QA-0188-task-0200.md`.
