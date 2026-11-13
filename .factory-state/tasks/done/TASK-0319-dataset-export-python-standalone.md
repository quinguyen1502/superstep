# Task

## Metadata

- Project: superstep
- Task ID: TASK-0319
- Title: Standalone SQLite and PostgreSQL for Python export
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Export

## Objective

Run a Python export against its own SQLite or PostgreSQL data.

## Scope

Python adapters, explicit idempotent setup, schema compatibility checks and transactional receipts.

## Inputs

Shared export binding and data semantics, Python exporter and project dependency generation.

## Expected Outputs

Runnable Python project with per-binding SQLite or PostgreSQL configuration and deterministic setup.

## Dependencies

[TASK-0318](../done/TASK-0318-dataset-export-api.md)

## Acceptance Criteria

- SQLite and PostgreSQL fixtures match connected API lookup and upsert results.
- Repeated setup preserves data, malformed binding fails clearly, and retry after commit yields the stored outcome.
- Mixed API and standalone bindings work from the same artifact.

## Validation Plan

Execute generated Python projects on SQLite and live PostgreSQL. Compare against shared connected fixtures, including nested Agent lookup and concurrent upsert.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0304-TASK-0319-dataset-export-python-standalone.md)
- [QA](../../artifacts/QA-0304-TASK-0319-dataset-export-python-standalone.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0304. QA QA-0304.
- 2026-11-12: Created during owner-approved requirements planning.

- 2026-11-13: Started on the connected export stack at PR #374.

- 2026-11-13: Ran the generated projects against SQLite and PostgreSQL 17.11 and moved to review.

## Handoff Notes

Start from integrated develop on `factory/task-0319-dataset-export-python-standalone` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
