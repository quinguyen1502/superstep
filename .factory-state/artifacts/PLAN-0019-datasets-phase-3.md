# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0019
- Status: Accepted 2026-11-13 (Asia/Saigon) by the owner (owner chat, "accept"), with REQ-0101. DEC-0101 accepted (pt287u). All tasks stay in backlog until the start condition in Sequence step 1 holds.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0101
- Related Design: DES-0007
- Related Architecture: ARCH-0003
- Related Decisions: DEC-0097, DEC-0101
- Integration baseline: origin/develop at b12fa14f

## Objective

Deliver Datasets phase 3 (REQ-0101) after the phase 2 chain and the REQ-0100 fixes it depends on.

## Context Reviewed

- [Phase 3 requirement](REQ-0101-datasets-phase-3.md), [Fix plan](PLAN-0018-dataset-phase1-fixes.md), [Write plan](PLAN-0017-dataset-writes.md)
- [Design](DES-0007-datasets.md), [Architecture](ARCH-0003-datasets.md), [DEC-0097](../decisions/DEC-0097-dataset-grid-and-export.md), [DEC-0101](../decisions/DEC-0101-dataset-grid-range-editing.md)
- PolarBase reference clone (commit `5a717f4`): filter models and schema, spreadsheet column, group, and calculation services, database MCP server.
- DES-0007 governs layout. The filter builder, summary row, and range selection follow it; if a task needs new layout rules it adds a DES addendum on its own PR.

## Work Breakdown

| Task | Priority | Outcome | Dependencies |
| --- | --- | --- | --- |
| [TASK-0345](../tasks/done/TASK-0345-dataset-filter-groups.md) | P1 | Filter tree and `in`, `not_in`, `not_contains` | TASK-0334 |
| [TASK-0346](../tasks/done/TASK-0346-dataset-filter-builder.md) | P1 | Nested filter builder in grid and node editor | TASK-0345 |
| [TASK-0347](../tasks/done/TASK-0347-dataset-column-summaries.md) | P1 | Server-side column summaries and the summary row | TASK-0345 |
| [TASK-0348](../tasks/done/TASK-0348-dataset-aggregate-operation.md) | P1 | `aggregate_rows` for the Agent tool and Dataset node | TASK-0347, TASK-0331 |
| [TASK-0349](../tasks/done/TASK-0349-dataset-group-by.md) | P2 | Group by one column | TASK-0347 |
| [TASK-0350](../tasks/done/TASK-0350-dataset-grid-layout.md) | P2 | TanStack Table 9 upgrade; column pinning, row height, TanStack Virtual | TASK-0341 |
| [TASK-0351](../tasks/done/TASK-0351-dataset-scalar-field-types.md) | P1 | Long text, URL, created and updated time | TASK-0338, TASK-0339 |
| [TASK-0352](../tasks/done/TASK-0352-dataset-structured-field-types.md) | P2 | Multi-select and auto-number | TASK-0351 |
| [TASK-0353](../tasks/done/TASK-0353-dataset-validation-formats.md) | P2 | Per-column validation and display formats | TASK-0338, TASK-0340, TASK-0351 |
| [TASK-0354](../tasks/done/TASK-0354-dataset-batch-cell-update.md) | P2 | Atomic batch cell update | DEC-0101, TASK-0353 |
| [TASK-0355](../tasks/done/TASK-0355-dataset-clipboard-fill.md) | P2 | TanStack cell selection and copy; typed paste, fill down and right, one-step undo | DEC-0101, TASK-0354, TASK-0350 |
| [TASK-0356](../tasks/review/TASK-0356-dataset-export-python-phase3.md) | P1 | Python export parity | TASK-0345, TASK-0348, TASK-0351, TASK-0352, TASK-0353, TASK-0343 |
| [TASK-0357](../tasks/review/TASK-0357-dataset-export-typescript-phase3.md) | P1 | TypeScript export parity | Same as TASK-0356 |
| [TASK-0358](../tasks/review/TASK-0358-datasets-phase3-acceptance.md) | P1 | Acceptance scenario and handbook | All PLAN-0019 tasks |

## Sequence

1. Start after PLAN-0017 (TASK-0331) and the REQ-0100 P0 and P1 tasks have merged. P2 fixes may still be open if they are not a listed dependency.
2. Query track: TASK-0345, then TASK-0346 and TASK-0347 in parallel, then TASK-0348 and TASK-0349.
3. Fields track (parallel to the query track): TASK-0351, then TASK-0352 and TASK-0353.
4. Grid track: TASK-0350 after TASK-0341.
5. Editing track (DEC-0101 accepted): TASK-0354, then TASK-0355 after the TanStack Table 9 upgrade in TASK-0350.
6. TASK-0356 and TASK-0357 in parallel, each editing only its own language section of `docs/dataset-export.md`. TASK-0358 last.

## Risks

- The filter tree and new kinds touch both export runtimes; parity tasks are P1 so exports never document an operator they cannot run.
- Summaries and grouping on large datasets may exceed the query budget; each task measures on 10,000 rows on both databases and records the numbers in QA.
- Range editing (TASK-0355) is the largest UI task; it can be deferred without blocking the rest of phase 3.

## Library-First Rule (DEC-0101)

- Grid tasks use TanStack Table features (ordering, sizing, visibility, pinning, manual pagination, grouping and expanding state, footers, cell selection in 9.x), `@tanstack/react-virtual`, and shadcn/ui. Custom code is limited to the gaps DEC-0101 lists, and each PR names any custom module and why.

## Approval Needs

- Done: the owner accepted REQ-0101 and this plan, DEC-0101, browser layout storage, the `;` multi-select delimiter, and no regular expression rules on 2026-11-13.
- Each task uses its own branch and Draft PR into `develop`; merge only after the owner asks and required CI is green.

## Completion Criteria

- REQ-0101 acceptance criteria pass, both exports pass the parity suites, and the handbook covers phase 3 in English and Vietnamese.
