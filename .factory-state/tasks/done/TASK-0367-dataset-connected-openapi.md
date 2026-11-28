# Task

## Metadata

- Project: superstep
- Task ID: TASK-0367
- Title: Publish the Dataset Connected v1 OpenAPI contract
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Document the existing six operations as a stable, typed public integration surface.

## Scope

Add only the Connected v1 data operations to the existing public specification. Model each request by operation and each response by its envelope, including the identifiers-only write result. Document Dataset Bearer credentials, permissions, binding validation and receipt retries. Keep the current route and body compatible with deployed exporters.

## Inputs

- Connected router and service, DatasetConnectedInput, API envelope and error catalog, public OpenAPI generator and spec-sync tests, and TASK-0318.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)
- [Review](../../artifacts/REV-0356-TASK-0367-dataset-connected-openapi.md)
- [QA](../../artifacts/QA-0356-TASK-0367-dataset-connected-openapi.md)

## Expected Outputs

Dataset-tagged runtime, committed and handbook OpenAPI with examples and typed results. Update Connected documentation to agree with the checked handler and include Aggregate.

## Implementation Notes

A discriminated request schema documents per-operation arguments instead of the current bare dictionary. Apply the existing runtime validators and preserve the accepted v1 bodies. Test valid legacy exports and invalid cases before changing any parsing behavior.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0318, Connected export contract](../done/TASK-0318-dataset-export-api.md) is integrated on develop.

## Acceptance Criteria

- The public spec describes Find, Get, Aggregate, Insert, Upsert and Delete with one stable HTTP operationId, discriminated models, the Dataset credential and representative 401, 403, validation, schema mismatch and receipt-conflict envelopes.
- Existing exporters use the same path and accepted wire shapes. A write-only token receives identifiers only, a cross-dataset or revoked token is denied, and Delete needs its explicit capability.
- The served spec, committed JSON, and handbook copy agree. Dataset management and share configuration routes stay outside this API contract.

## Validation Plan

Run public OpenAPI and envelope tests, Dataset Connected and exporter regressions, layer checks, and generated-spec drift checks on the current toolchain. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and the proposed interfaces in ARCH-0005.

## Open Questions

None blocking.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.
- 2026-11-22: Owner confirmed task start. Created `factory/task-0367-dataset-connected-openapi` from `origin/develop` at `848f2351` and moved the task to doing. TASK-0318 is integrated. Formula work through TASK-0366 is integrated and Relation work remains pending.
- 2026-11-22: Implemented the typed public contract, verified SQLite and exporter compatibility, and moved to review. Review REV-0356 and QA QA-0356 record the local results. PostgreSQL and the full Factory profile remain CI gates.
- 2026-11-22: The Draft PR passed 25 CI checks on `c52537ab`, including PostgreSQL 17 and full Factory verification. The owner approved merging [PR #427](https://github.com/quinguyen1502/superstep/pull/427) into develop. This commit records the move to done. The updated head requires its own successful checks before integration.

## Handoff Notes

After #427 integrates, promote TASK-0368 to todo and start it from develop using the integrated Connected v1 contract.
