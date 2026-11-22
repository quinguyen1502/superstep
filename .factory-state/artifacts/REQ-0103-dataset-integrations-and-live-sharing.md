# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0103
- Status: Accepted for planning
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Source: Owner approval on 2026-11-22 of Connected OpenAPI and SDKs, Studio realtime, and a read-only Dataset link, in that order.

## Summary

Make Datasets usable from supported integration clients, let Studio users see committed changes promptly, and let managers share a limited dataset view with someone outside Studio.

## Problem Or Opportunity

Exported workflows already call a token-authenticated Connected API. Application developers need a versioned specification and reusable clients. Studio users currently reload their query to see someone else's writes. A manager who needs to share selected rows with an outside reader has no revocable Dataset link.

## Scope

- Document Connected API v1 in the public OpenAPI. Add Python sync and async and TypeScript Dataset clients to the existing packages for Find, Get, Aggregate, Insert, Upsert and Delete.
- Update the authenticated Studio Rows view when a Dataset changes. Refresh the active query, summary and groups and preserve unsaved edits.
- Add an explicit read-only share link for a manager-selected set of columns and fixed filter, with preview, rotation and revocation. The visitor can open it without a Studio account and page through or search the published result.

## Out Of Scope

- Workflow change triggers, durable external event feeds, presence and concurrent editing of the same draft.
- Dataset schema administration in the SDK, and changes to existing grants, connected export clients or standalone storage behavior.
- Public writes, public CSV downloads, public Relation traversal, public realtime, general Saved Views, embeds and password or domain policies.

## Business Rules

- Preserve Dataset credential scope, the separate delete capability, write-only response minimization and write receipt semantics.
- The Studio feed inherits normal Dataset read permission. A rollback, simulation or replay has no visible change. A conflict uses the existing row revision check and preserves the user's draft.
- Creating or administering a link requires existing Dataset manager permission. Link holders can see only the chosen columns and matching rows. A share grants no Studio session, Dataset token or workflow permission.
- A rotated or revoked link and a share whose Dataset no longer exists return an unavailable state on the next request. Schema changes cannot broaden a share implicitly.

## Acceptance Criteria

- **AC1.** The runtime and published OpenAPI describe compatible Connected v1 requests and typed envelopes, and both official SDKs pass end-to-end operation, scope, schema drift and uncertain-write retry tests on a live backend.
- **AC2.** A second authenticated session sees committed writes and query summaries update without page reload, including after reconnect. A same-row write conflict preserves the local draft. Access removal stops future notifications and reads.
- **AC3.** A manager can preview and share a filtered view. A logged-out visitor sees the same rows and fields under paging and search. Forged input, hidden-field searches, scope changes and link rotation or revocation cannot expose any additional data.
- **AC4.** SQLite and PostgreSQL migration and compatibility coverage passes. Redis fan-out works across processes. English and Vietnamese docs cover token setup, live editing behavior and the scope of an anonymous share.

## Assumptions And Open Questions

- Sequence the three milestones as accepted by the owner. Coordinate shared migration order and field contract changes with the Formula and Relation plan.
- The approved link model is a live, read-only view with a fixed share configuration. Link lifetime is controlled by rotation and revocation in v1.
- No product decision blocks the first task. Validate deployment-specific rate and connection budgets during implementation.

## Related Artifacts

- [Dataset baseline](REQ-0097-datasets.md), [write and grant changes](REQ-0099-dataset-writes.md), [Phase 3](REQ-0101-datasets-phase-3.md).
- [Formula and Relation plan](PLAN-0020-dataset-formulas-and-relations.md).
- [Design](DES-0009-dataset-integrations-and-live-sharing.md), [architecture](ARCH-0005-dataset-integrations-and-live-sharing.md), [decision](../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md), [delivery plan](PLAN-0021-dataset-integrations-and-live-sharing.md).
