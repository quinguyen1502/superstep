# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0319
- Task ID: TASK-0335
- QA Owner: implementation QA
- Created: 2026-11-14
- Updated: 2026-11-14
- Outcome: pass

## Validation Scope

TASK-0335 on `factory/task-0335-dataset-team-authority` after merging `origin/develop` with PR #390. Backend tests ran on SQLite and on a local PostgreSQL 16 server. Playwright ran with system Chrome.

## Acceptance Criteria Coverage

- Criterion: A team member who is not owner or admin can edit rows but gets `403` on schema change, dataset delete, grant, revoke, and token actions.
  - Result: pass
  - Evidence: `tests/test_dataset_team_authority.py::test_members_without_management_cannot_change_a_team_dataset` and `::test_team_editors_edit_rows_and_managers_manage`.
- Criterion: The owner and an admin can do all of them; rotation keeps the original issuer.
  - Result: pass
  - Evidence: `::test_team_editors_edit_rows_and_managers_manage` and `::test_rotation_keeps_the_issuer_and_the_token_still_authorizes`.
- Criterion: Ownership transfer is admin-only and audited.
  - Result: pass
  - Evidence: `::test_admins_transfer_team_dataset_ownership` checks the owner and editor are refused, invalid targets return `DATASET_OWNER_INVALID`, and a `dataset.transfer` audit event is recorded. `::test_existing_team_datasets_take_the_creator_as_owner` checks the migration backfill.

## UX And Accessibility Coverage

- Criterion: Management actions are disabled with an explanation for a non-manager member.
  - Result: pass
  - Evidence: `e2e/dataset-team-authority.spec.ts`. Locale parity passes.

## Checks Performed

- `pytest -q tests -k "dataset or layers or envelope"` on SQLite and with `TEST_DATABASE_URL` set to the local PostgreSQL — passed.
- `npx vitest run src/lib/__tests__/dataset-manage.test.ts` — passed. `npm run lint` — passed.
- `npx playwright test e2e/dataset-team-authority.spec.ts e2e/datasets.spec.ts e2e/dataset-write-only.spec.ts` — 4 passed.
- `factory verify run --profile full`, `factory validate`, and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- Team datasets with no create audit event are covered only by the null-owner path in unit tests, not by production data.

## Residual Risk

- Team editors lose management of team datasets they did not create.

## Assumptions

- A dataset owner must keep `resources.manage` to manage; an owner downgraded to viewer cannot.

## Required Follow-Up

- None.

## QA Decision

Passed to done.
