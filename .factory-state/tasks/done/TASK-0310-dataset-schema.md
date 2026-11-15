# Task

## Metadata

- Project: superstep
- Task ID: TASK-0310
- Title: Dataset schema and ownership API
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Studio

## Objective

Create and manage typed, personal and team dataset definitions through the Studio API.

## Scope

Dataset and column models, additive Alembic migration, ownership checks, schema revisions, supported types and compatibility rules.

## Inputs

docs/backend-architecture.md, backend/app/services/access.py and existing team repositories.

## Expected Outputs

Authorized dataset and schema CRUD services and routes, with a portable type and field contract for rows and exporters.

## Dependencies

None. This is the first implementation task.

## Acceptance Criteria

- Authorized owners can create and rename datasets and columns while stable field keys persist.
- Other users cannot enumerate private datasets.
- Duplicate keys and incompatible schema changes receive stable domain errors.
- Types include text, number, boolean, date/time, email and select.

## Validation Plan

Run layer, API envelope, migration upgrade and scope tests on SQLite and PostgreSQL.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)
- [Review](../../artifacts/REV-0295-TASK-0310-dataset-schema.md)
- [QA](../../artifacts/QA-0295-TASK-0310-dataset-schema.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0295. QA QA-0295.
- 2026-11-12: Created during owner-approved requirements planning.
- 2026-11-12: Owner requested implementation. Added the additive migration, typed schema API, scoped reads and writes, and deletion cleanup. Targeted SQLite, PostgreSQL, layer and envelope checks passed. Moved to review for the draft PR.

## Handoff Notes

Start from integrated develop on `factory/task-0310-dataset-schema` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
