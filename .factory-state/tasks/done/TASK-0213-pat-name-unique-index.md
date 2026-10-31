# Task

## Metadata

- Project: superstep
- Task ID: TASK-0213
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071, DEC-0076, DEC-0009, DEC-0010

## Objective

Make active personal access token names unique per user in the database. The check before the insert (PatService._issue, `_free_name` of TASK-0208) is not atomic and there was no unique index, so two creates with one name at the same moment could both succeed (REV-0196, non-blocking finding).

## Scope

### In Scope

- Alembic migration 0050: a partial unique index on `personal_access_tokens (user_id, name)` where `revoked IS NULL`, on SQLite and Postgres. Revoked rows stay out because a revoked token's name can be used again (DEC-0071).
- Active duplicates already in the table are renamed before the index is created: the oldest (by `created`, then `id`) keeps the name, later ones get `name (2)`, `name (3)`... skipping names already used, cut to 80 characters (the `_free_name` scheme).
- The repository maps the IntegrityError of that index to `PatNameTaken`; the service answers `PAT_NAME_TAKEN` (409) on create, and at CLI collection moves on to the next free name.
- Regression tests on SQLite, a Postgres migration test, CHANGELOG.

### Out Of Scope

- Changing the name rules, the error message or the approve step (it still checks before the device is approved; the token is minted at collection).

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010; works on SQLite and Postgres.

## Acceptance Criteria

- A create whose check missed a token created at the same moment answers 409 PAT_NAME_TAKEN and leaves one active token with the name.
- Parallel creates with one name make exactly one token.
- A CLI collection that loses the race delivers a token named `name (2)`.
- The migration renames active duplicates, leaves revoked rows alone, and the index refuses a second active name on SQLite and Postgres; names stay reusable after revoke and across users.

## Validation

- Regression tests that fail before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to make token names unique in the database (REV-0196).
- 2026-10-31: implemented on `factory/task-0213-pat-name-unique` from `develop`. Revoked rows do not block a name today (DEC-0071, test_an_active_name_cannot_be_reused), so the index is partial on `revoked IS NULL`. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0201-task-0213.md`. QA: `.factory-state/artifacts/QA-0201-task-0213.md`.
