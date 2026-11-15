# Architecture

## Metadata

- Project: superstep
- Architecture ID: ARCH-0003
- Status: Planned
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Related: [Requirement](REQ-0097-datasets.md), [Design](DES-0007-datasets.md), [Decision](../decisions/DEC-0097-dataset-grid-and-export.md), [Plan](PLAN-0016-datasets.md)

## Context And Rationale

Superstep ships with SQLite and supports PostgreSQL. RunService binds service ports to the engine and supports queued jobs and recovery. Saved workflows can use their owner's resources today. Dataset policy needs its own principal and grant checks. Project export already generates Python and TypeScript LangGraph projects, README files and environment templates. The existing Retriever adapter is the precedent for connected export.

## Boundaries And Interfaces

- Use layered routers, services and SQLAlchemy repositories with Alembic migrations for the Studio database. Store dataset ownership and schema revision, stable typed column definitions and versioned JSON row values. Add database-enforced unique keys with canonical typed values scoped to dataset and column. Document casing, null handling, date/time normalization and sort/filter semantics in a shared portable contract.
- Dataset storage is distinct from Knowledge Base. Resolve column references against the dataset schema and use parameterized query expressions with allowlisted operators. Apply server-side projection, pagination and explicit row, byte and query budgets. Validate data before a transaction commits. Use compare-and-set row revisions for interactive edits.
- UI access uses user and team policy. Engine access uses an explicit grant bound to the effective saved workflow and allowed operations. Keep caller, resource owner and effective workflow distinct. Validate added or changed bindings and mappings on save, import, restore and unsaved execution against the authoring user's dataset access. Unchanged authorized workflow versions can run under their explicit grants. Cover nested calls, resume, debug/test and recovery, and deny public entry points. External credentials are scoped to the exact datasets and allowed operations and use the existing token handling conventions for storage, rotation and revocation.
- A storage-agnostic Dataset port connects engine operations to services. Treat rows returned by a node as workflow state and disclose that they may appear wherever workflow state is persisted or displayed. Audit, logs and telemetry use identifiers, operation names, counts and outcome codes. Agent reads project only configured columns and are bounded.
- A transaction applies a run-originated write, verifies the applicable fence and records a durable operation receipt. Use a stable identity per logical node execution and reject reuse with incompatible arguments. Exact retries return the previous outcome. Explicit test and debug dry runs simulate writes without touching production rows.

## Export Contract

- Define one language-neutral binding format for API, SQLite and PostgreSQL, with stable field keys, required types, unique-key requirements and the operations used. Export Python and TypeScript from that same contract. Destination IDs, paths, DSNs and credentials come from deployment configuration. The configuration explicitly selects one backend per binding.
- The connected adapter uses a scoped token and bounded Dataset API operations. A write includes the stable idempotency identity and checks schema compatibility at the destination. Audit identifies the external credential and operation. Reuse existing secure HTTP handling where applicable.
- Standalone projects ship app-owned schema and a documented explicit setup command. Use runtime parameter binding and validated identifiers, a database-enforced unique key and transactional write receipts. Startup validates compatible schema and reports missing, incompatible or inaccessible bindings. Setup must be safe to repeat and preserve existing data. Snapshot import is explicit, permission checked and uses the same schema rules.
- Studio runtime access, connected export and standalone databases should return equivalent typed records and actionable domain errors. Validate mixed bindings, falsey and null values, stale schema, concurrent upserts and retry after commit in both languages.

## Migration, Risks And Recovery

- Studio schema changes are additive Alembic migrations. Validate upgrade on existing SQLite and PostgreSQL. On application rollback, retain dataset tables and data. Disable entry points if necessary and document data export and recovery before destructive rollback.
- Benchmark representative indexed lookup, paginated filter/sort and CSV import on both databases before setting operational limits. The portable JSON model trades arbitrary indexed analytics for predictable schema evolution. Revisit indexes if fixture workloads fail the agreed budgets.
- A standalone PostgreSQL adapter operates on app-owned tables. External connection permissions, transport settings and data retention are deployment responsibilities. Mixing backends provides no cross-dataset transaction or automatic synchronization.
