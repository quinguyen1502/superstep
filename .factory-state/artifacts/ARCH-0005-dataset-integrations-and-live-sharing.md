# Architecture

## Metadata

- Project: superstep
- Architecture ID: ARCH-0005
- Status: Proposed for implementation review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Related Requirements: REQ-0103

## Connected v1

Keep `POST /api/datasets/{id}/connected` and its body version. Include just that Dataset data-plane route in the public OpenAPI. Document six operation variants with the shared envelope and a Dataset Bearer scheme. Keep existing route/service validation and exporter compatibility as the contract boundary. Generate TypeScript schema types from the public spec, align Python models through the existing spec checks, and reuse each SDK transport and error mapping. Keep one operation ID and one body for all transport retries. Legacy connected exports stay independent of an installed SDK.

## Studio Invalidation

Reuse the authorized workflow-history socket and memory/Redis notification hub patterns. Propose a same-origin Studio session WebSocket and a lightweight authorized revision read. Keep Dataset data revision separate from schema and per-row optimistic revisions. Advance the marker under the existing writer lock in the mutation transaction. Publish one invalidation after a changed transaction commits. Keep the socket payload bounded to an invalidation and revision metadata, with no values, row IDs or diagnostics.

Check Dataset visibility before subscribing, on push, and on heartbeat. Subscribe before the initial authoritative read. Coalesce refreshes per active query. After reconnect, tab activation or a low-frequency fallback revision check, reread through the original authorized routes if the marker changed. Close and clear inaccessible data on permission loss. A Redis outage may delay push while the revision read still detects changes.

The writer matrix must include Studio row operations, batch and undo, CSV, Connected, Workflow, Agent and Formula schema backfill. Skip revision advances and notifications for rollbacks, no-op writes, simulations and receipt replay. The repository owns transaction consistency. The service notifies after commit.

## Public Read Boundary

Add a dedicated share resource with Dataset ID, name, public column keys, validated base filter, token hash and revocation metadata. A manager creates it under the same permission boundary as Access. Use a random secret and a separate capability namespace. The initial proposal places the secret in the copied URL fragment and transfers it in a share-specific request header from the same-origin reader. Verify that access logs, metrics and audit records omit the secret. Record the share ID and action for management audit.

The anonymous service resolves the capability and validates its current state on every request. Apply the fixed predicate and projected columns in the repository query. Apply visitor text search only across published searchable columns. Return only the public view metadata, permitted cells and paging within the filtered result. Reject mismatched or archived keys and incompatible filters, and exclude Relation values and Formula definitions or error metadata from public serialization. Preview calls the same projection path as the visitor page.

Configure bounded request bodies and pagination, per-link and per-IP rate limits, no-store responses, and noindex for the public page. Rotation atomically replaces the secret and revocation disables subsequent reads. Dataset deletion invalidates dependent links. The page and endpoints use a distinct public route with no Studio or Connected authority.

## Compatibility, Migration And Recovery

- Add realtime metadata and share storage through additive migrations in separate PRs. Coordinate Alembic heads and Dataset write boundaries with the Formula and Relation plan. Test upgrades from the existing populated schema on SQLite and PostgreSQL.
- Validate same-origin sessions, worker-to-API delivery with Redis and in-memory single-process mode. Measure the effect of refresh bursts and large imported batches on API and query load.
- Roll back the live UI by returning to manual query refresh while preserving the marker. For share rollback, close the public read surface before changing storage. Preserve manager revocation records while any deployment can still serve shares.
- Follow existing API envelope, authorization, localization and backend layer conventions. Keep new error codes synchronized between the catalog, error reference and both locales.

## Related Artifacts

- [Requirement](REQ-0103-dataset-integrations-and-live-sharing.md), [design](DES-0009-dataset-integrations-and-live-sharing.md), [Dataset architecture](ARCH-0003-datasets.md), [Formula and Relation architecture](ARCH-0004-dataset-formulas-and-relations.md).
- [Decision](../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md).
- [Connected service](../../backend/app/services/dataset_connected.py), [existing history socket](../../backend/app/api/routes/runs_ws.py), [notification hub](../../backend/app/services/notification_hub.py), [public OpenAPI builder](../../backend/app/api/openapi_public.py).
