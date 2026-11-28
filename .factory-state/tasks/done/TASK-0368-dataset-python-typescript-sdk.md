# Task

## Metadata

- Project: superstep
- Task ID: TASK-0368
- Title: Add Dataset clients to Python and TypeScript SDKs
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Let integrations call the six Connected operations with a typed Dataset client.

## Scope

Expose Python sync and async and a TypeScript client under the existing packages. Accept a base URL, dataset ID, Dataset token and explicit binding definition. Reuse existing HTTP and error plumbing, typed filter and paging inputs, field projection and receipt semantics. Document working snippets in the same PR.

## Inputs

- Published Connected v1 OpenAPI, SDK generation and packaging, existing exports and their conformance evidence.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)
- [Review](../../artifacts/REV-0357-TASK-0368-dataset-python-typescript-sdk.md)
- [QA](../../artifacts/QA-0357-TASK-0368-dataset-python-typescript-sdk.md)

## Expected Outputs

Clients, schema generation and parity checks, shared contract fixtures where applicable, live integration test coverage, and examples for read and write credentials.

## Implementation Notes

Use binding metadata rather than requiring callers to construct the whole raw envelope. Keep operation identity stable for retries and expose caller-supplied identity for application recovery. Preserve server error codes. Type the operation envelope and dynamic cell values without implying compile-time knowledge of keys from an arbitrary dataset.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0367](../done/TASK-0367-dataset-connected-openapi.md). Start after this dependency integrates, or document an approved stack.

## Acceptance Criteria

- Python sync and async and TypeScript can find, get, aggregate, insert, upsert and delete on a live backend using one scoped token and an explicit binding.
- A retried uncertain write reuses the same operation ID and arguments without adding a second row. A new intentional write receives its own identity. Write-only outputs stay identifiers only, and errors retain stable code and details.
- The existing workflow and Chat imports still build and run. Both package suites pass their spec and package checks.

## Validation Plan

Run both SDK unit and package suites, TS generation check, Python shape tests and live integration on SQLite and PostgreSQL. Validate revoked tokens, schema drift, network retry and permission parity. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and ARCH-0005. Writes request identifiers by default. SDKs retry once with the same serialized body and accept a caller-supplied operation ID for recovery across calls.

## Open Questions

None blocking. The Connected v1 contract is integrated at `4d71b119`.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.
- 2026-11-22: Started on develop at `4d71b119` after PR #427 merged. The OpenAPI contract includes the current Formula metadata. Relation and standalone Formula parity are tracked separately. Factory ready passed before source work.
- 2026-11-22: Implemented and validated the Dataset clients, package exports, and English and Vietnamese examples. Moved the task to review with REV-0357 and QA-0357. The Postgres 17 live SDK run and full Factory profile are covered by PR CI.
- 2026-11-22: All 25 applicable checks passed for [PR #428](https://github.com/quinguyen1502/superstep/pull/428) at `6648d7b2`, including live SDK tests on SQLite and PostgreSQL 17. The owner approved merge into develop. The updated PR head requires its own CI pass.

## Handoff Notes

After #428 integrates, promote TASK-0369 to todo and start it from develop. Package publication follows the separate release workflow.
