# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0356
- Task ID: TASK-0367
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Validation Scope

Verified the public contract against the running API on SQLite, generated Python and TypeScript exporters, the SDK checks and the published documentation sources.

## Acceptance Criteria Coverage

| Criterion | Result | Evidence |
| --- | --- | --- |
| Six discriminated requests on one operation, typed result envelope, scoped Bearer scheme and representative errors | Pass | `test_public_openapi.py` checks the operation allowlist, discriminator, scheme, argument bounds and errors. `test_dataset_connected.py` validates the published examples and real replies against the served schemas. |
| Existing exporters and permission behavior | Pass on SQLite | The backend regression suite exercises generated Python and TypeScript connected and standalone projects, write-only projections, cross-Dataset and revoked credentials, independent delete capability, schema drift, receipt conflict and replay. |
| Served spec, snapshot and handbook agree, with a limited endpoint allowlist | Pass | Spec drift check, byte-for-byte copy comparison, public OpenAPI tests and EN/VI handbook builds. |

## Checks Performed

- Backend Dataset, exporter, public API, error envelope and layer suites with Deno on SQLite. 64 passed and 45 PostgreSQL cases skipped.
- Final public OpenAPI, error envelope and layer subset. 13 passed.
- Python SDK suite. 234 passed and eight opt-in live cases skipped.
- TypeScript SDK generated type check, typecheck and 106 unit tests passed.
- Root npm build, lint and tests passed. 191 frontend, 22 React package and 106 TypeScript SDK tests passed.
- Zensical handbook builds passed in English and Vietnamese. Factory hygiene, artifact IDs and whitespace checks passed.

## CI Evidence

[PR #427 checks](https://github.com/quinguyen1502/superstep/pull/427/checks) passed all 25 applicable jobs on the implementation commit `c52537ab`. This covered PostgreSQL 17 with Redis 7, the full Factory profile, both SDKs against a live server and all Playwright shards. Publish and deploy jobs were skipped for the pull request.

## QA Decision

Pass. The owner approved integration on 2026-11-22. Repeat required CI on the commit that records approval before merging.
