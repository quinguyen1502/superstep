# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0016
- Status: Planned
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Integration baseline: origin/develop at eca3c38c

## Objective

Deliver native operational datasets in Studio, deterministic workflow and Agent access, and configurable connected and standalone workflow exports with parity in Python and TypeScript.

## Context Reviewed

- [Requirement](REQ-0097-datasets.md)
- [Design](DES-0007-datasets.md)
- [Architecture](ARCH-0003-datasets.md)
- [Decision](../decisions/DEC-0097-dataset-grid-and-export.md)
- [Export adapter precedent](REQ-0089-export-parity-adapters.md)

## Work Breakdown

| Task | Phase | Outcome | Dependencies |
| --- | --- | --- | --- |
| [TASK-0310](../tasks/done/TASK-0310-dataset-schema.md) | Studio | Dataset schema and ownership API | — |
| [TASK-0311](../tasks/done/TASK-0311-dataset-rows.md) | Studio | Typed row CRUD, query and concurrency | TASK-0310 |
| [TASK-0312](../tasks/done/TASK-0312-dataset-studio-grid.md) | Studio | Dataset catalog, schema editor and grid | TASK-0310, TASK-0311 |
| [TASK-0313](../tasks/todo/TASK-0313-dataset-csv.md) | Studio | Dataset CSV preview, import and export | TASK-0311, TASK-0312 |
| [TASK-0314](../tasks/done/TASK-0314-dataset-access.md) | Runtime | Workflow grants and scoped Dataset API tokens | TASK-0310, TASK-0311, TASK-0312 |
| [TASK-0315](../tasks/done/TASK-0315-dataset-node-runtime.md) | Runtime | Dataset node runtime and atomic write receipts | TASK-0311, TASK-0314 |
| [TASK-0316](../tasks/done/TASK-0316-dataset-node-editor.md) | Runtime | Dataset node palette and mapping editor | TASK-0312, TASK-0314, TASK-0315 |
| [TASK-0317](../tasks/done/TASK-0317-dataset-agent-tool.md) | Runtime | Read-only Dataset tool for Agents | TASK-0315, TASK-0316 |
| [TASK-0318](../tasks/done/TASK-0318-dataset-export-api.md) | Export | Export binding contract and connected adapters | TASK-0315, TASK-0317 |
| [TASK-0319](../tasks/done/TASK-0319-dataset-export-python-standalone.md) | Export | Standalone SQLite and PostgreSQL for Python export | TASK-0318 |
| [TASK-0320](../tasks/todo/TASK-0320-dataset-export-typescript-standalone.md) | Export | Standalone SQLite and PostgreSQL for TypeScript export | TASK-0318 |
| [TASK-0321](../tasks/todo/TASK-0321-dataset-export-bindings-ui.md) | Export | Project export binding UI and optional snapshots | TASK-0316, TASK-0319, TASK-0320 |
| [TASK-0322](../tasks/todo/TASK-0322-dataset-end-to-end.md) | Acceptance | Dataset end-to-end acceptance and handbook | TASK-0313, TASK-0321 |

## Sequence And Checkpoints

1. **Studio** delivers schema creation, data management and CSV. After the grid lands, CSV and the access work can proceed independently.
2. **Runtime** delivers workflow grants, the Dataset node and the read-only Agent tool. Check write recovery and the denial matrix before proceeding to export.
3. **Export** establishes the shared binding contract and connected adapters. Python and TypeScript standalone adapters can proceed in parallel on that contract. The export UI and optional snapshots follow both.
4. **Acceptance** exercises the Studio and exported support workflow on both runtimes and every backend, then records operational limits, handbook coverage and screenshot evidence.

## Risks And Controls

- JSON query costs vary by backend. Measure both databases before advertising size limits and keep list and export paths bounded.
- Grants and tokens must survive all runtime entry points consistently. Use authorization matrices and simulate recovery after a committed write.
- Export parity can drift across languages and drivers. Reuse one binding contract and a shared fixture matrix.
- Schema evolution and snapshots can expose incompatible data or confidential values. Apply schema checks, authorization, explicit snapshot opt-in and bounded restore.
- Preserve data on application rollback and document how to disable access or export data before destructive operations.

## Approval And Delivery

- The owner approved recording the requirement and decomposition on 2026-11-12. This is the planning handoff.
- Implement on one task branch and PR per task. Use the normal review, QA, full Factory verification, required CI and explicit owner merge gates.
- Update task links as lifecycle paths change. Record the completion summary after all acceptance criteria pass.

## Completion Criteria

- All listed tasks meet their acceptance criteria and are integrated.
- The end-to-end support scenario passes in Studio and on both exported languages across Superstep API, SQLite and PostgreSQL.
- Final QA documents schema setup, permission boundaries, retry behavior, snapshot handling and operational limits.
