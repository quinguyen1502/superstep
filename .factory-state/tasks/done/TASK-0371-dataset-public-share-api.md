# Task

## Metadata

- Project: superstep
- Task ID: TASK-0371
- Title: Enforce read-only Dataset share links on the server
- Status: done
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
- [Review](../../artifacts/REV-0360-TASK-0371-dataset-public-share-api.md)
- [QA](../../artifacts/QA-0360-TASK-0371-dataset-public-share-api.md)
- [HTTP contract](../../../docs/backend-architecture.md#dataset-share-links)

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

None blocking. The prerequisite Studio realtime task integrated into develop at `837f3e5e`.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.
- 2026-11-22: Started from develop at `837f3e5e` after PR #430 merged. Factory ready passed. Migration 0073 remains the head, Formula is present and Relation remains a separate milestone.
- 2026-11-22: Added migration 0074 and the Dataset share management and anonymous read endpoints. The local projection, capability isolation, quota, revision and migration checks passed. Moved to review with REV-0360 and QA-0360.
- 2026-11-22: Fixed runtime annotation compatibility and locale interpolation from initial CI. Verified the focused backend suite on Python 3.12.13 and all frontend unit tests.
- 2026-11-22: Added the share token redaction module to the sandbox image's explicit file list. A local Docker build and the focused PostgreSQL 17 and Redis 7 regressions passed.

- 2026-11-22: The owner explicitly approved merging PR #431 into develop. All 25 checks passed on reviewed commit `6387135a`. [PR #431 checks](https://github.com/quinguyen1502/superstep/pull/431/checks)

## Handoff Notes

After integration, use the documented manager endpoints and send the copied fragment in X-Dataset-Share on each anonymous API read. Preview returns the same metadata and row values as the visitor routes. The UI must handle unavailable links and enforce its noindex and referrer policy on the reader page.
