# Task

## Metadata

- Project: superstep
- Task ID: TASK-0197
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080
- Design IDs: none
- Architecture IDs: DEC-0074

## Objective

Scheduled backups record the S3 bucket. A manual backup with the s3 attachment backend records the bucket and prefix in the manifest (TASK-0194); the scheduled backup.sh did not, so a restore of a scheduled archive could not say which bucket to restore. The owner asked for this before v0.10.1 ("Làm cả 4 việc rồi mới release").

## Scope

### In Scope

- backup.sh (local schedule and deploy --schedule) writes attachment_s3 {bucket, prefix} from .env when STUDIO_ATTACHMENT_STORAGE=s3, JSON-escaped
- handbook Operate: CLI backup table (en, vi)
- CHANGELOG

### Out Of Scope

- Other follow-ups of the v0.10.1 batch; each has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- A scheduled backup on s3 has attachment_s3 with the bucket and prefix of .env
- A scheduled backup on db has no attachment_s3
- Quotes and backslashes in the prefix stay valid JSON

## Validation

- Tests for each criterion; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's v0.10.1 follow-up list.
- 2026-10-31: implemented on `factory/task-0197-scheduled-backup-s3-manifest` from `develop`. The scheduled `backup.sh` writes `attachment_s3` like a manual backup; the handbook says so in en and vi. `factory verify run --profile full` passed. The owner asked for these follow-ups before v0.10.1 ('Làm cả 4 việc rồi mới release'). Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0185-task-0197.md`. QA: `.factory-state/artifacts/QA-0185-task-0197.md`.
