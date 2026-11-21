# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0020
- Status: Accepted for implementation on 2026-11-21
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Related Requirements: REQ-0102
- Related Design: DES-0007
- Related Architecture: ARCH-0003
- Integration baseline: origin/develop at 16d67fb9, including Phase 3, Dataset grid interaction fixes and the demo dataset

## Objective

Deliver Formula and Relation as independently verifiable slices with Studio, workflow and export compatibility. Start with Formula because it uses the existing row writer and has no cross-dataset dependencies. Deliver Relation after validating target authorization and transaction behavior.

## Context Reviewed

- [Proposed requirement and owner decisions](REQ-0102-dataset-formulas-and-relations.md)
- [Earlier selections](REQ-0099-dataset-writes.md) and [Phase 3 scope](REQ-0101-datasets-phase-3.md)
- [Studio design](DES-0007-datasets.md), [Dataset architecture](ARCH-0003-datasets.md) and [grid/export decision](../decisions/DEC-0097-dataset-grid-and-export.md)
- [Current connected and standalone contracts](../../docs/dataset-export.md)

## Work Breakdown

The work items below sequence the approved scope. The first task delivers the contract and the Formula evaluator. Allocate later task IDs when their design and dependency gates are satisfied.

| Work item | Dependencies | Deliverable and exit check |
| --- | --- | --- |
| [Contract, UX, architecture and Formula evaluator](../tasks/done/TASK-0364-dataset-formula-contract.md) | Owner scope approval received | Record formula grammar, type and error semantics, relation wire shape, grants, dependency rules, standalone compatibility, additive migration and rollback strategy. Add the Schema and Rows design, including accessible preview, picker, and error states. Publish the bounded evaluator and reusable conformance fixtures. |
| [Formula storage and writes](../tasks/done/TASK-0365-dataset-formula-persistence.md) | Contract and owner review of the migration | Recompute results inside the row write transaction using the reviewed parser, evaluator and dependency graph. Cover edits, batch, undo, insert, upsert, CSV and schema backfill on SQLite and PostgreSQL. Compare old and new clients across migration. |
| [Formula Studio and queries](../tasks/done/TASK-0366-dataset-formula-studio.md) | Formula storage | Add a Schema editor with field insertion and preview. Show read-only results and accessible row errors in Rows. Validate server-side filter, sort, summary and CSV behavior with typed and null results. |
| Formula runtime and export parity | Formula storage and query contract | Cover read projection in Dataset nodes and Agent tools, connected schema checks, and Formula evaluation in Python and TypeScript standalone. Run shared fixtures against SQLite and PostgreSQL and check write-only behavior. |
| Relation storage and authorization | Contract, with shared storage migrations landed in sequence | Add target configuration, indexed reference integrity, scoped search and consistent link writes. Prove concurrent delete/link outcomes, scope changes, source deletion, revocation and unopened private targets against both engines. |
| Relation Studio, connected API and exports | Relation storage | Add keyboard-friendly target picker, relation display, filters, clear and blocked-deletion guidance. Wire authorized runtime paths and both standalone adapters. Verify relation import/export mapping, permission errors, and setup behavior for missing or incompatible dependencies. Split Studio and two export PRs once the contract is fixed. |
| Cross-surface acceptance and docs | All milestone work | Exercise tickets and companies through Studio, workflow and connected and standalone exports. Update EN/VI handbook, API and export docs. Capture SQLite/PostgreSQL QA, desktop/mobile evidence and performance results. |

## Sequence

1. With scope approved, review the design addendum, architecture and storage decision. Measure formula evaluation and persistence costs in a disposable database, then prepare the production migration for review. Prototype relation concurrency before enabling relation writes.
2. Deliver the Formula evaluator and write path, then Studio/query and runtime/export parity. Make Formula generally selectable after its parity checks pass.
3. In parallel with Formula work after the shared contract review, prototype Relation integrity and authorization. Serialize schema and migration PRs that touch the same files. Land Relation storage before enabling the picker and exports.
4. Gate general availability of each field on its compatibility and authorization checks. Record the rollout and rollback steps in the operator handoff.

## Technical Checks

- **Formula consistency.** Prefer writing typed results in the same transaction as their inputs so filter, sort and aggregate reuse existing server queries. Prototype backfill under the existing schema lock. Bound input size, expression depth, work and result sizes. Agree on nulls, comparison, Boolean coercion and numeric overflow before porting the evaluator. Reuse the same contract fixtures in Python and TypeScript.
- **Relation integrity.** Validate an indexed edge representation with the source and target dataset/row identity. Define one source of truth and a deterministic lock order. Use transactional existence and access checks and verify query plans. Batch label resolution for the visible page and keep target labels out of source outputs without independent target access.
- **Exports.** Use portable binding references, with deployment IDs in environment settings. Forward both required bindings explicitly. Standalone setup validates a shared database and compatible targets and remains idempotent. A selected source snapshot never opts in target data implicitly. Define the error and import behavior for unresolved or unmapped targets before release.
- **Performance and compatibility.** Benchmark 10,000 rows per dataset, then test schema backfill within the existing 25,000-row limit. Measure 50-row grid queries, batched label lookups and concurrent writes on both databases. Compare to Phase 3 and agree budgets before enabling the fields. Keep existing row and response limits. Check upgrades from a pre-change database, older scripts, CSV and rollback with the feature disabled.

## Risks And Recovery

- Lock contention during Formula backfill or overlapping Relation writes. Measure at realistic sizes, use consistent lock order, and prove all-or-nothing outcomes before exposing schema changes.
- Target label disclosure through search, errors, summaries or exports. Test soft and hard access loss, write-only callers, and redaction across output surfaces.
- Cross-runtime coercion and backend drift. Run identical fixtures against SQL engines and export runtimes, and reject unsupported binding combinations during setup.
- Older releases may not understand new field metadata. Use an additive migration, retain computed and relationship data, and document the pre-downgrade compatibility check and data export path.

## Approval Needs

- Owner scope approval received on 2026-11-21.
- Owner review of migration and compatibility strategy once the design spike has evidence. Follow normal per-PR approval for integration.

## Scenario

Create Companies and Support tickets in the same team. Add `[hours] * [hourly_rate]` to Tickets and link a ticket to a company. Change the hours, update the company name, filter and sum ticket costs, and verify the result and label. As Viewer, browse the records and export CSV. Run a permitted workflow and its Python and TypeScript exports. Attempt deletion of a referenced company and confirm it succeeds only after clearing the links.

## Completion Criteria

- REQ-0102 acceptance criteria pass against SQLite and PostgreSQL. The connected API and both export runtimes pass parity and migration checks. Permissions, keyboard and mobile flows are covered.
- Record restorable deployment and rollback instructions and update EN/VI handbook and API documentation.
