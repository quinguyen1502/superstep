# Task

## Metadata

- Project: superstep
- Task ID: TASK-0208
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0080, REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0076, DEC-0010, DEC-0009

## Objective

Fix the two minor points of the review of #262 (TASK-0207): a chunked body past the ceiling on a route that parses JSON or a file answered 400 BAD_REQUEST instead of 413, and a CLI sign-in whose token name was taken between approval and collection was consumed with PAT_NAME_TAKEN.

## Scope

### In Scope

- BodyLimit answers 413 PAYLOAD_TOO_LARGE in the envelope once a body without a length passes the ceiling, whatever the route parses
- the token minted on collection gets a free name (`name (2)`...) when the approved name is taken; DEC-0076 amended
- docs/api-errors.md, handbook CLI page en/vi, CHANGELOG

### Out Of Scope

- The pending python-release approvals of v0.10.0 and v0.10.1 (owner action).

## Constraints

- Layers of DEC-0009, the error envelope of DEC-0010, en and vi docs where users see a change.

## Acceptance Criteria

- A chunked body past the ceiling on /api/auth/login answers 413 PAYLOAD_TOO_LARGE in the envelope; callbacks still answer 413
- A poll after the approved name was taken delivers a token with a free name of at most 80 characters

## Validation

- Regression tests that fail before the fix; `factory verify run --profile full`; `factory validate`; CI green before the merge.

## Activity Log

- 2026-10-31: created from the owner's request to verify and fix the two minor points of the review of #262.
- 2026-10-31: implemented on `factory/task-0208-body-limit-413-pat-name` from `develop`. Both points reproduced on develop (400 BAD_REQUEST; PAT_NAME_TAKEN after the device moved to delivered). BodyLimit now replaces the response with the 413 envelope once the counted body tripped the ceiling; PatService._free_name picks `name (2)`, `name (3)`... at collection. Moved to done on this PR before the merge (TASK-0148).
- Review: `.factory-state/artifacts/REV-0196-task-0208.md`. QA: `.factory-state/artifacts/QA-0196-task-0208.md`.
