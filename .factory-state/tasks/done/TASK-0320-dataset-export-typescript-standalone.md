# Task

## Metadata

- Project: superstep
- Task ID: TASK-0320
- Title: Standalone SQLite and PostgreSQL for TypeScript export
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

Run a TypeScript export against its own SQLite or PostgreSQL data.

## Scope

TypeScript adapters, explicit idempotent setup, schema compatibility checks and transactional receipts.

## Inputs

Shared export binding and data semantics, TypeScript exporter and supported project runtimes.

## Expected Outputs

Runnable TypeScript project with per-binding SQLite or PostgreSQL configuration and deterministic setup.

## Dependencies

[TASK-0318](TASK-0318-dataset-export-api.md)

## Acceptance Criteria

- SQLite and PostgreSQL fixtures match the connected API contract.
- Repeated setup preserves data.
- Incorrect types and missing config fail clearly.
- Retry after commit yields the stored outcome and mixed bindings work.
- Runtime support and dependencies are documented for each existing TypeScript export surface affected.

## Validation Plan

Type-check and execute generated TypeScript projects on the supported runtime against SQLite and live PostgreSQL, including Agent lookup, concurrency and the same fixtures as Python.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0305-TASK-0320-dataset-export-typescript-standalone.md)
- [QA](../../artifacts/QA-0305-TASK-0320-dataset-export-typescript-standalone.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0305. QA QA-0305.
- 2026-11-12: Created during owner-approved requirements planning.
- 2026-11-13: Implemented the TypeScript standalone runtime on `factory/task-0320-dataset-export-typescript-standalone`, stacked on `factory/task-0319-dataset-export-python-standalone` at `222f8420` because that branch already owns the shared export contract and `docs/dataset-export.md`. SQLite uses `node:sqlite`. PostgreSQL uses `pg`. `datasetCall` dispatches any backend other than `superstep`.
- 2026-11-13: `tests/test_dataset_typescript_standalone.py`, `tests/test_dataset_project_export.py`, and `tests/test_project_export.py` passed on SQLite with Deno 2.9.8. The PostgreSQL parameter skipped locally because no database was listening. Moved to review. CI `backend-postgres` still needs to run the same tests with `TEST_DATABASE_URL`.

## Handoff Notes

The branch is stacked on the Python standalone tip, not on develop. A pull request for this task should target `factory/task-0319-dataset-export-python-standalone`. PostgreSQL behavior is the same pytest parameter and has not been executed on this machine.
