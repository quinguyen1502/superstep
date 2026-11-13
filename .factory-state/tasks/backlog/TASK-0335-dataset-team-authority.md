# Task

## Metadata

- Project: superstep
- Task ID: TASK-0335
- Title: Enforce team dataset management authority
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0100
- Plan: PLAN-0018
- Phase: Fix
- Priority: P1
- Size: M

## Objective

Only the people DEC-0100 names can change schema, delete a team dataset, manage grants, and manage tokens, and token rotation keeps the issuer.

## Scope

### In Scope

- Split `editable_definition` into row editing and dataset management checks; apply the management check to schema, delete, grants, and token routes.
- `rotate` keeps `issuer_id`; only managers rotate or revoke tokens.
- Admin-only ownership transfer of a team dataset to another team member, with audit.
- Studio: management actions shown disabled with an explanation for members who cannot use them (pairs with TASK-0340).

### Out Of Scope

- Team roles for workflows or other resources (DEC-0100 Option B).
- Rewriting the issuer of tokens already rotated.

## Inputs

- `services/dataset_service.py` `editable_definition`; `services/dataset_access.py` `list`, `grant`, `issue`, `rotate`, `revoke_token`; `models/team.py`.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- Owner accepts DEC-0100. Branch from `develop`.

## Acceptance Criteria

- A team member who is not owner or admin can edit rows but gets `403` on schema change, dataset delete, grant, revoke, and token actions.
- The owner and an admin can do all of them; rotation keeps the original issuer.
- Ownership transfer is admin-only and audited.

## Tests

- Role matrix tests (owner, admin, other editor, viewer, non-member) for every management route.
- Token rotate keeps issuer; a rotated token still authorizes via its issuer.
- Playwright: disabled actions with an explanation for a non-manager member.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- Confirm DEC-0100 Option A, and whether a team member other than the owner should be able to issue tokens.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0335-dataset-team-authority` from `develop` when implementation begins.
