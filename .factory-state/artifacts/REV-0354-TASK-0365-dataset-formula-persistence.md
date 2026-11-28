# Review

## Metadata

- Project: superstep
- Review ID: REV-0354
- Task ID: TASK-0365
- Reviewer: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Approved for QA

## Review Scope

Reviewed Formula schema metadata, migration, all row writers, typed reads, CSV, connected and workflow projection, and rollback behavior.

## Reference Artifacts

- [Task](../tasks/done/TASK-0365-dataset-formula-persistence.md)
- [Architecture](ARCH-0004-dataset-formulas-and-relations.md)
- [Storage decision](../decisions/DEC-0102-dataset-formula-relation-storage.md)
- [Formula evaluator](../tasks/done/TASK-0364-dataset-formula-contract.md)

## Findings

### Blocking

- No blocking findings in the persistence slice.

### Non-Blocking

- The opt-in switch gates schema use while Studio and standalone export lack their Formula support. Release acceptance must still cover representative maximum expression mixes and all supported runtimes.

## Standards And Architecture Alignment

- The Alembic upgrade adds two nullable columns. The downgrade refuses active Formula schemas. The operator instructions give a backup and freeze path.
- Schema backfill and row mutations reuse the existing writer lock and formula plan. Sizing and revision checks protect stored updates, including a rollback after the first batch has flushed.
- Formula values reuse scalar predicates and summaries. Formula diagnostics are projected only for requested readable fields. Receipts and audit retain their existing identifier and outcome shapes.
- Schema configuration keeps manager authorization, revision checks, and dependency validation. Calculated values are rejected by write APIs, CSV mappings and workflow authoring.
- Client error strings are registered in the shared catalog, documentation and both locale files. The export guard keeps the unported standalone runtimes from receiving a Formula schema.

## Review Decision

Approved for QA on the stacked PR. The prior evaluator PR remains its integration dependency.
