# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0097
- Status: Accepted for planning 2026-11-12
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Source: Owner discussion on native datasets, the interactive prototype, configurable connected and standalone exports, and approval to record and decompose the recommended scope.

## Summary

Studio users can manage typed, persistent tabular data and reuse it across workflows. A workflow can look up and persist records deterministically. Exported Python and TypeScript workflows can use the same live tables through Superstep or their own SQLite or PostgreSQL data, configured per dataset.

## Scope

- Personal and team datasets in a dedicated Studio area. Create a schema manually or from a CSV preview. View and evolve compatible columns, edit rows, search, filter, sort, paginate, import CSV and export CSV.
- A Dataset node with Find rows, Get row, Insert row and Upsert row. Map workflow state into typed fields and choose bounded output fields. An Agent tool can query a dataset with a configured read-only binding.
- Explicit grants for workflows and dataset-scoped external credentials. Track mutations and grant changes with audit metadata. Apply the same policy when a run resumes or a worker recovers.
- Python and TypeScript project export. Select Superstep API, standalone SQLite or standalone PostgreSQL independently for each binding. The project includes schema definitions and an explicit database setup command for standalone targets. An optional snapshot supplies starting rows.

## Out Of Scope

- Arbitrary SQL, administration of external databases from Studio, editing arbitrary existing external tables, automatic synchronization, formula columns, cross-table relations, multi-cell clipboard and fill handles.
- Dataset change triggers, saved views, calendar and map views, external MCP exposure, embeddings and evaluation datasets.
- Dataset execution from public chat or other public workflow entry points in v1. Agent write tools and workflow-driven deletes are deferred.

## Desired Behavior And Business Rules

- A Support team imports Customers from CSV, creates Tickets, sets `ticket_id` as a unique key, and grants a workflow read access to Customers and write access to Tickets. The workflow finds a customer by email and upserts a ticket visible in Studio.
- Column labels are editable. Stable identifiers preserve workflow mappings after renames. Schema changes that would invalidate stored rows or bindings fail with actionable feedback. Dataset, row, column and grant removals use the shared typed-confirmation dialog when exposed in Studio.
- Data access checks the applicable user, workflow grant or external token. Sharing or editing a workflow does not implicitly grant access to the dataset. Revocation takes effect on subsequent operations, including recovered runs. Audit and operational telemetry carry IDs, operation metadata and outcomes, with no row values or secrets.
- Upsert requires a declared unique key enforced by the database. Retries of a write reuse the original result and cannot create duplicate side effects. Workflow tests and debug runs use an explicit dry-run path for writes.
- Both exported languages use the same field and error contract. Destination IDs, file paths, connection strings and credentials are supplied at deployment. The default package contains no data rows or secrets. Snapshot inclusion is explicit and permission checked. Live runs fail at the affected node if a binding is missing, unauthorized or incompatible.

## Acceptance Criteria

- Studio users can create a typed schema, preview a CSV with actionable per-row errors, import valid rows, filter and edit them, and export the authorized data. Keyboard interaction, responsive layout, both themes and en/vi are covered.
- A personal or team dataset is visible only to authorized actors. Tests cover cross-team denial, insufficient operation grants, revoked credentials and denied public paths. Trace and audit output respect the documented row-data boundary.
- An authenticated workflow performs lookup and upsert and shows the expected row in Studio. Automated tests cover concurrent writers, stale cell edits, worker recovery after commit and test-mode writes.
- Python and TypeScript generated projects execute the same lookup and upsert cases against a live local Superstep API, SQLite and PostgreSQL, including mixed per-dataset bindings, schema drift, invalid config and write retries. Snapshot export is off by default and restore behavior is verified.

## Assumptions And Open Questions

- Datasets are operational tables managed by Superstep. Knowledge Base remains the document retrieval surface.
- Scope covers bounded operational datasets. Row, byte and query budgets are implementation decisions to verify on SQLite and PostgreSQL before documenting supported limits. No product decision blocks planning.

## Related Artifacts

- [Dataset design](DES-0007-datasets.md)
- [Dataset architecture](ARCH-0003-datasets.md)
- [Dataset decision](../decisions/DEC-0097-dataset-grid-and-export.md)
- [Implementation plan](PLAN-0016-datasets.md)
- [Export adapter precedent](REQ-0089-export-parity-adapters.md)
