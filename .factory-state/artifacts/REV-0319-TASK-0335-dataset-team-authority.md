# Review

## Metadata

- Project: superstep
- Review ID: REV-0319
- Task ID: TASK-0335
- Reviewer: implementation review
- Created: 2026-11-14
- Updated: 2026-11-14
- Outcome: approved for QA

## Review Scope

Diff for team dataset management authority against REQ-0100, DEC-0100, PLAN-0018, and the TASK-0335 acceptance criteria. Reviewed the migration, the Dataset service and access service checks, the ownership transfer route, error codes, Studio actions and the transfer dialog, handbook, and changelog.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- DEC-0100 (accepted, Option A)
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md
- docs/backend-architecture.md

## Findings

### Blocking

- None.

### Non-Blocking

- The owner of an existing team dataset is backfilled from its earliest `dataset.create` audit event. A team dataset without that event, or whose creator was deleted, has no owner, so only admins manage it until an admin transfers it. The Studio transfer dialog shows "No owner" for that case.
- The owner column uses `ON DELETE SET NULL`, so deleting a user leaves their team datasets to admins.
- The Studio decides whether to disable management actions with `canManageDataset`, which mirrors the backend check. The backend stays the authority and returns `DATASET_MANAGE_DENIED`.

## Standards And Architecture Alignment

- `DatasetService.managed_definition` is the one management check. Schema changes, dataset deletion, grant list, grant, revoke, and token issue, rotate, and revoke all go through it. Row reads and writes keep `editable_definition`.
- Rotation no longer passes an issuer, so the original issuer is kept and the rotated token still authorizes through the issuer's access.
- Ownership transfer needs `org.manage`, checks the dataset revision, requires a team member who can manage resources, and records `dataset.transfer` with the previous and new owner.
- Migration `0068_dataset_team_owner` follows `0067_dataset_delete_capability` on `develop`; no open stream adds another migration. It uses `batch_alter_table` for SQLite.
- New error codes are documented in `docs/api-errors.md`.

## Design Alignment

- Members who cannot manage see management actions disabled with one line that explains who can use them, in English and Vietnamese.
- Admins see a transfer action on team datasets with a dialog that names the current owner and lists eligible members.

## Test Coverage Review

- `tests/test_dataset_team_authority.py` runs every management route as a team editor who is not the owner (403 `DATASET_MANAGE_DENIED`), a viewer (403 `PERMISSION_DENIED`), and a non-member (404), and checks the revision did not change.
- The same file covers rows edited by a team editor, the owner and an admin managing, rotation keeping the issuer with the rotated token still working, admin-only audited transfer with invalid targets, and the migration backfill.
- `src/lib/__tests__/dataset-manage.test.ts` covers `canManageDataset`. Playwright `e2e/dataset-team-authority.spec.ts` covers the disabled actions and explanation for a non-manager member and the enabled actions for an admin.

## Risk Review

- Team editors who used to change the schema, grants, or tokens of team datasets they did not create lose that ability. The changelog and handbook state it.

## Required Fixes

- None.

## Approval Decision

Approved for QA.
