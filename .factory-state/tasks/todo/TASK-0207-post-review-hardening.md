# Task

## Metadata

- Project: superstep
- Task ID: TASK-0207
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080, REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0074, DEC-0076, DEC-0009

## Objective

Fix the three points of the re-review of #258 to #261: nginx let every /api/ request carry 110 MB including unauthenticated callbacks, an approved CLI sign-in that was never collected kept a plaintext token forever, and old S3 attachments could not be read once the s3 settings were removed.

## Scope

### In Scope

- nginx back to 10m with WEB_MAX_BODY_SIZE on the upload routes only
- app-side body ceilings (BodyLimit middleware, STUDIO_MAX_BODY_MB, 1 MB for callbacks)
- CLI token minted on collection; legacy secrets revoked and cleared at expiry
- a row's S3 location is enough to read it; missing credentials named
- DEC-0076 amended; docs en/vi

### Out Of Scope

- The other findings of the v0.10.0/v0.10.1 review; each group has its own task.

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.
- No secret is logged or printed.

## Acceptance Criteria

- Callbacks refuse bodies above 1 MB, other routes above STUDIO_MAX_BODY_MB, upload routes keep their ceilings, with or without a length
- nginx allows 10 MB except on the upload routes
- No token is stored for an approved sign-in, and an expired one cannot be collected; legacy secrets are revoked
- Old S3 files are readable without the bucket setting; missing credentials are named

## Validation

- A regression test for each finding that fails before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the external review of v0.10.0 and v0.10.1.
