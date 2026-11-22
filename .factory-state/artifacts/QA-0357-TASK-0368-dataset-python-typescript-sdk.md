# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0357
- Task ID: TASK-0368
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Six operations on a live backend with explicit bindings and scoped tokens | The SDK integration runner exercised each operation in Python sync, Python async and TypeScript. It covered nested filters, paged lookup, aggregate results, scope denial, schema mismatch and revocation. | Pass on SQLite |
| Stable identity on uncertain writes, fresh identity on new writes, identifiers-only projection and stable errors | Live tests interrupted the first response after commit. The retry produced the same request and a single persisted row. Unit tests verified distinct IDs across new calls, preserved error details, redirects, aborts and status handling. | Pass |
| Existing workflow and Chat entry points and package checks | Both SDKs ran workflow and Chat live tests. The Python wheel exposed all clients. TypeScript ESM and CommonJS smoke tests, typecheck, code generation and npm pack dry run passed. Python model keys and literal unions matched OpenAPI. | Pass |

## Checks Performed

- Python SDK unit suite. 265 passed and 10 opt-in live tests skipped in that invocation.
- Root npm test. 191 frontend, 22 React package and 117 TypeScript SDK tests passed. Build, lint and compiled exports passed.
- Live SQLite SDK runner. 10 Python and eight TypeScript tests passed, including all three Dataset client variants.
- Python wheel and sdist built. Wheel import smoke confirmed Dataset, workflow and Chat clients.
- Both handbook editions built. OpenAPI drift, Factory hygiene and whitespace checks passed.

## CI Evidence

[PR #428 checks](https://github.com/quinguyen1502/superstep/pull/428/checks) passed all 25 applicable checks on `6648d7b2`. The [live SDK job](https://github.com/quinguyen1502/superstep/actions/runs/44969818232/job/137046916588) passed both its SQLite and PostgreSQL 17 steps. Factory verification and all Playwright shards passed.

## QA Decision

Pass. The owner approved integration on 2026-11-22. Repeat required checks on the approval-recording commit before merge.
