# Task

## Metadata

- Project: superstep
- Task ID: TASK-0365
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Persist Formula definitions, result values and cell diagnostics in the existing Dataset write transaction and expose the scalar results to existing typed readers.

## Scope

- Add nullable column formula metadata and row diagnostics in an additive migration.
- Reuse the verified typed evaluator and dependency graph. Recompute once after normalized mutations and auto-number assignment. Keep schema backfill, row revisions, optimistic concurrency and row budgets coherent.
- Keep formulas read-only in create/update row inputs, batch, CSV, connected contracts and workflow write bindings. Project typed results and authorized diagnostics while preserving write-only and receipt shapes.
- Keep Formula schema creation unavailable for general use until Studio and the export runtimes are compatible.

## Dependencies

- [Contract and evaluator](../done/TASK-0364-dataset-formula-contract.md). Integration follows the evaluator in PR #423.
- Owner approval to proceed following review of the [storage and rollback decision](../../decisions/DEC-0102-dataset-formula-relation-storage.md) per the [approved plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md).

## Related Artifacts

- [Requirement](../../artifacts/REQ-0102-dataset-formulas-and-relations.md)
- [Design](../../artifacts/DES-0008-dataset-formulas-and-relations.md)
- [Architecture](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md)

## Acceptance Criteria

- Existing SQLite and PostgreSQL datasets migrate additively and can be read, written and exported by existing clients under the compatible schema.
- Formula creation and edits backfill under the schema revision lock. Existing operations update derived values and diagnostics atomically and keep stale revisions, rollback, write-only rules and receipts safe.
- Formula outputs sort, filter and aggregate using their declared scalar type. Input changes remain valid when a formula result is null with a diagnostic. Direct computed writes and incompatible source-column removal are rejected.
- Validate typical and upper-limit backfills on both databases. Demonstrate the documented downgrade or affected-write freeze procedure in a disposable database.

## Validation Plan

- Extend Dataset integration tests across column edits, insert, patch, upsert, batch, undo, CSV, permissions, runtime and receipts on both databases.
- Measure current and proposed writer lock duration and verify old-to-new migration with a populated pre-change schema.

## Activity Log

- 2026-11-21: Prepared after local backfill and transaction feasibility measurements. Awaiting storage design review.
- 2026-11-21: Owner replied with approval after the storage proposal and Relation layout review. Proceed with the additive Formula migration and retain the planned rollout gate. This approval did not authorize merging either pull request.
- 2026-11-21: Implemented the additive migration and transactional Formula writes. Validated both database engines, benchmarked real backfills and moved to review.

- 2026-11-21: The owner approved merging PR #424 into develop. Review and QA passed. Final-head CI gates integration.

## Review And QA

- [Review](../../artifacts/REV-0354-TASK-0365-dataset-formula-persistence.md)
- [QA and backfill measurements](../../artifacts/QA-0354-TASK-0365-dataset-formula-persistence.md)
