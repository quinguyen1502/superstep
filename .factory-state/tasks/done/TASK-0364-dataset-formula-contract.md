# Task

## Metadata

- Project: superstep
- Task ID: TASK-0364
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Implement and measure the first Formula slice. Establish shared Formula semantics and Relation design constraints before altering Dataset storage and application surfaces.

## Scope

- Specify the Dataset Schema and Rows flows, portable formula semantics and relation permission boundaries.
- Implement a deterministic typed Formula compiler, dependency ordering, and evaluator in the reusable backend core.
- Add conformance fixtures for API and export work and test the evaluation and persistence costs of a 25,000-row backfill in disposable local SQLite and PostgreSQL databases. Exercise both commit orders of the Relation link and target-delete race.
- Prepare the reviewed storage design and identify the first migration and compatibility gates.

## Inputs

- [Approved requirement](../../artifacts/REQ-0102-dataset-formulas-and-relations.md)
- [Approved plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md)
- [Dataset storage architecture](../../artifacts/ARCH-0003-datasets.md)
- [Design addendum](../../artifacts/DES-0008-dataset-formulas-and-relations.md)
- [Architecture addendum](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md)
- [Storage decision](../../decisions/DEC-0102-dataset-formula-relation-storage.md)

## Acceptance Criteria

- Compile arithmetic, comparisons, text concatenation and lazy IF, with typed same-row references and bounded inputs, outputs and evaluation.
- Evaluate independent and dependent Formula columns in a deterministic order. Return null with a structured cell error for row-specific failures, null for missing values, and a schema diagnostic for invalid references, types and cycles.
- Publish shared fixture cases for successful results, nulls, runtime error states and invalid schema. Measure backfill cost on realistic row counts with the current SQLite and PostgreSQL repository shape. Verify the relation race in both orders.
- The design and architecture define how later slices preserve Dataset visibility, locks, API and export compatibility, and user-facing error states.

## Validation Plan

- Run Formula contract fixtures, Dataset schema and row regression tests, backend layer checks, and Factory hygiene.
- Record evaluator and persistence performance at 10,000 and 25,000 rows on SQLite and PostgreSQL. Document full migration verification remaining for the storage change.

## Activity Log

- 2026-11-21: The owner authorized implementation of the proposed Formula and Relation scope. Prepared the contract and evaluator task from develop.
- 2026-11-21: Delivered the Python compiler, shared contract fixtures, and design addenda. Measured backfill and both Relation race outcomes on SQLite and PostgreSQL. Regression tests passed. Moved to review.

- 2026-11-21: The owner approved merging PR #423 into develop. Review and QA passed. Final-head CI gates integration.

## Review And QA

- [Review](../../artifacts/REV-0353-TASK-0364-dataset-formula-contract.md)
- [QA and benchmark](../../artifacts/QA-0353-TASK-0364-dataset-formula-contract.md)
- [Next storage task](../backlog/TASK-0365-dataset-formula-persistence.md) awaits the storage decision review.
