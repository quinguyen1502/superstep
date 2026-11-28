# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0359
- Task ID: TASK-0370
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| A second Studio session sees committed changes in the active query, rows, groups and summaries | Real browser contexts on the same team exercise a keyboard cell save and a CSV import. Open group, search and focused cell stay in place. The predecessor writer tests cover the corresponding workflow, Agent and Connected revision updates. | Pass |
| Keep a draft and coalesce pending work, then catch up when push is missed or interrupted | While a peer edits a changed row, a second cell write and CSV import queue no group query. The save shows the row conflict and preserves the draft. Escape releases the pending refresh. A narrow sorted grid retains its scroll position and auto-loaded pages after a dropped frame, a focus resync, fallback polling and a schema change delivered by a new connection. | Pass |
| Remove protected data after visibility changes | Removing a real team member and committing another row wakes the stream. The member's grid, editor draft and catalog entry disappear. | Pass |

## UX And Accessibility Coverage

- Verified keyboard editing, mouse grouping and summary controls, retained cell focus and narrow scroll behavior.
- The delayed notice uses a polite live region and the warning token. Access loss uses the localized alert in the existing empty state.
- Captured the narrow grid with the delayed footer in light and dark for visual review.

## Checks Performed

- Dataset Playwright passed 34 cases against the local API, Vite and Chrome, including all three realtime cases. The opt-in handbook capture was skipped.
- Frontend Vitest passed all 191 tests, including locale parity. Production build, TypeScript, UI lint, the UI convention source checks and Factory hygiene passed.
- Python SDK passed 265 tests with 10 integration skips. Focused Dataset backend, layer and envelope checks passed locally with 17 passed and 10 external-service cases skipped. The public OpenAPI drift check passed.
- The English and Vietnamese handbook builds and image validation passed. Both pages explain live refresh, conflict recovery and lost access.

- [PR #430 CI](https://github.com/quinguyen1502/superstep/pull/430/checks) passed all 25 runnable checks for reviewed head `d6fd32f8`, including the full Factory profile, all Playwright shards, English and Vietnamese handbook builds, PostgreSQL 17 and Redis 7.

- Finalization exposed a timing assumption in the grouped-refresh Playwright case. It now synchronizes on the committed WebSocket frame and the coalescing window before closing the draft. The expected data, summary and conflict assertions are unchanged.

## Gaps And Residual Risk

- Local browser tests use SQLite and in-memory notifications. PR CI covers PostgreSQL and Redis on the backend, including split-process delivery.

## QA Decision

Pass. Require successful checks on the final PR head before integration.
