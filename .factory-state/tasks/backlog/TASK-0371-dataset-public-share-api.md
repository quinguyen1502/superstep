# Task

## Metadata

- Project: superstep
- Task ID: TASK-0371
- Title: Enforce read-only Dataset share links on the server
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Allow a Dataset manager to share one fixed projection through revocable anonymous reads.

## Scope

Add a Dataset share resource holding the approved field keys and base filter, with a random capability and hashed secret. Add authenticated create, list, preview, rotate and revoke operations, and distinct anonymous metadata and paged rows endpoints. Limit public queries and rate by link and visitor IP.

## Inputs

- Existing Dataset manager authorization, dataset filtering and projection, public Chat transport patterns, permission and deletion rules, and the share design.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)

## Expected Outputs

Additive schema, two authorization boundaries, audit and public-read safeguards, and tests that enforce the configured projection and base filter.

## Implementation Notes

Validate active keys and typed filter on creation and before using them. Apply the server-side predicate and projection in the query; visitor search can only inspect published searchable fields. Fail closed for incompatible schema, revoked link or deleted dataset. Public responses omit private schema metadata, formula expressions/diagnostics and Relation traversal.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0370](../done/TASK-0370-dataset-live-studio-grid.md). Start after this dependency integrates, or document an approved stack.

## Acceptance Criteria

- A permitted manager can create, preview, rotate and revoke. Studio peers without manager authority cannot administer a link. Rotation invalidates the old capability and revocation or deletion blocks future anonymous reads.
- An anonymous visitor sees only approved columns and matching rows. Metadata, search, pagination, forged parameters and responses with no matching rows cannot expose hidden fields, row counts, identifiers or linked target data.
- Only bounded read routes accept the link. Dataset or workflow tokens cannot act as a share capability, and a share link cannot authorize Connected writes. Raw secrets remain out of stored records, telemetry and application logs.

## Validation Plan

Run SQLite and PostgreSQL repository and API tests with two roles, missing/rotated/revoked links, cross-dataset requests, schema drift, hidden-field search, deleted rows, cache behavior, limits and layer checks. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and the proposed interfaces in ARCH-0005.

## Open Questions

Confirm the predecessor contract and integration before promoting to todo.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.

## Handoff Notes

Use a dedicated task branch from current develop when implementation is requested. This plan does not authorize a release or merge.
