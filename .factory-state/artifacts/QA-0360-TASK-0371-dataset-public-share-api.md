# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0360
- Task ID: TASK-0371
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Dataset managers administer links and revoke prior capabilities | Shared team ownership, editor peers, outsiders and unauthenticated callers exercise every management method. Rotation, revocation, cross-Dataset mutations, Dataset deletion and an in-flight rotation use the real repository. | Pass on SQLite and PostgreSQL 17 |
| Preview and public projection match | Typed rows, fixed predicates on a private column, published-only Unicode search, selected column order, missing rows and byte-limited pagination are checked. Captured SQL selects no row identity or Formula diagnostics. A changed Formula dependency or archived field fails closed. | Pass on SQLite and PostgreSQL 17 |
| Bounded routes and unrelated credentials | Real Dataset and workflow tokens fail at the share endpoint. A share token fails at Connected writes. Invalid query shape, duplicate headers, both rate buckets, body limits, cache headers and generic errors are covered. | Pass locally |
| Secrets and existing data | Storage contains only the digest. Management audit details and sanitized request IDs omit the capability. The migration round trip preserves an existing Dataset and its rows. | Pass locally |

## Checks Performed

- Dataset, export, migration, activity and API regressions passed locally with 212 passed and 158 external-service or runtime cases skipped.
- Focused share, metrics, envelope and layer checks passed with 40 passed and 10 PostgreSQL or environment cases skipped.
- First PR CI identified eager annotation evaluation on Python 3.12 and a locale placeholder with single braces. Deferred annotations and the paired locale placeholders resolve both failures. Focused share, envelope, layers, logging, telemetry and OpenAPI tests pass in the Python 3.12.13 virtualenv. All 191 frontend unit tests passed.
- English and Vietnamese error key and placeholder parity, the public OpenAPI drift check, handbook builds and image validation passed.
- A local Docker sandbox image build passed its startup import after the Dockerfile copy list included the share token redaction module. A separate PostgreSQL 17 and Redis 7 run passed the share, realtime, Public Chat, telemetry and layer checks.
- Factory hygiene, artifact IDs and whitespace checks passed.

- All 25 checks passed on reviewed commit `6387135a`, including SQLite, PostgreSQL 17 with Redis 7, all three Playwright shards, and Docker images. The PR skips the publishing and deployment jobs. [PR #431 checks](https://github.com/quinguyen1502/superstep/pull/431/checks)

## Gaps And Residual Risk
- The share controls, browser link handling and the public reader are covered by the following task.

## QA Decision

Pass. The final task commit must pass PR CI before owner-approved integration.
