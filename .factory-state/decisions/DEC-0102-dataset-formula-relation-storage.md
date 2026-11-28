# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0102
- Status: Accepted for Formula storage implementation
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Related: [Requirement](../artifacts/REQ-0102-dataset-formulas-and-relations.md), [Architecture](../artifacts/ARCH-0004-dataset-formulas-and-relations.md), [Plan](../artifacts/PLAN-0020-dataset-formulas-and-relations.md)

## Decision And Rationale

- Keep each Formula result in the existing typed row and update it under the same writer lock as the input. Reuse the grid and query contract by adding versioned expression metadata to the column. Keep cell diagnostics separate from values so projections and summaries preserve null semantics.
- Use a bounded interpreter for deterministic same-row calculations. The Dataset language has a fixed grammar and name scope, and can use common fixtures across Python and TypeScript.
- Store each Relation as one indexed edge scoped to the source field. Treat target deletion as a conflict while a link exists. Dataset locks and permission rechecks make link creation and deletion serializable at the relevant target. Schema changes and cleanup paths participate in the same integrity contract.
- Add nullable Formula metadata and a separate Relation edge table with additive migrations. Restrict links to the same ownership scope and initially require a shared connected instance or standalone database. This gives the transaction one authority for link existence and prevents hidden cross-scope lookups.

## Alternatives Considered

- Evaluate Formula results during reads. This avoids a backfill but introduces calculated filters, sorting and summaries across two SQL engines and two export runtimes. Materializing once on write preserves typed query behavior and requires a bounded backfill.
- Use database expressions or allow general executable functions. A fixed interpreter makes results portable, narrows execution to typed values and supports reproducible diagnostics.
- Store relation identifiers in source JSON alone. Reverse-delete checks would need an additional reliable index and authorization logic. A normalized edge can enforce a row identity and support direct reverse lookups without a second stored copy.
- Cascade target deletion into source rows. Restricting deletion keeps a linked record available until its references are explicitly addressed.

## Approval And Review

- Review actual backfill timings, concurrent link/delete outcomes and rollback behavior before the first migration.
- Scope approval was received on 2026-11-21. The owner approved proceeding after the storage and layout review. The Formula persistence task uses the proposed additive migration and retains the rollout and rollback checks.
