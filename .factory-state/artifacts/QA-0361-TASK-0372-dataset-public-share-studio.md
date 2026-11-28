# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0361
- Task ID: TASK-0372
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| A permitted manager creates and previews a limited view | Playwright configures a published order and a filter on an unpublished field, returns to edit without losing the draft, compares all rows on the first page against a fresh guest context, and confirms clipboard copy of the generated URL. The browser reads with the dedicated header and omits query secrets, cookies and referrers. | Pass |
| The visitor can read and navigate the permitted result | Playwright checks the initial loading state, empty result, published-only search, paging, focus, retry after an interrupted read and unavailable state. At 390 px the page stays within the viewport. The search control and action align, and the reader works in Vietnamese dark mode and on a light desktop. | Pass |
| Replacing or revoking a link ends old access | Playwright opens the replacement in the same tab, rejects the previous capability on its next search, verifies exact-name revoke, and rejects a reload of the revoked link. Anonymous UI exposes no editing actions or hidden columns. | Pass |
| Validate integration and document the flow | The TypeScript SDK inserts a permitted row. Two Studio sessions refresh without reloading. The guest sees the row on retry within the approved projection. The handbook explains creation, visitor access and invalidation in both locales. | Pass |

## Checks Performed

- Dataset and alignment Playwright suite passed with 44 passed and 1 opt-in capture skipped. Captured manager preview, light desktop reader and dark narrow reader on the seeded support fixture.
- Frontend build, TypeScript, lint, UI source review and all 191 unit tests passed.
- Focused Dataset share API, frame and reader document policy, layer and envelope tests passed with 21 passed and 10 database or environment cases skipped locally. The public OpenAPI drift check passed. The exact Compose nginx image passed configuration checks and served both the protected reader document and the normal Studio fallback.
- English and Vietnamese handbook builds and image validation passed. Factory hygiene, ID check, PR text and whitespace checks passed.

- The two share browser scenarios also passed against PostgreSQL 17 and Redis 7.
- All 25 PR checks passed on reviewed commit `f6b12929`, including both database backends, all Playwright shards, Factory verification, and the handbook and container builds. [PR #432 checks](https://github.com/quinguyen1502/superstep/pull/432/checks)

## Gaps And Residual Risk
- Public views fetch fresh rows on the next request. Existing open pages keep the rendered data until then.

## QA Decision

Pass. The owner approved integration. The final task commit must pass PR CI before merge.
