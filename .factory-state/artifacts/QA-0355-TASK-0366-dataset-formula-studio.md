# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0355
- Task ID: TASK-0366
- QA Owner: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Pass

## Validation Scope

Validated Studio with a live local backend and temporary datasets, plus the Formula preview and persistence contracts against SQLite and PostgreSQL 17.

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Editor, computed values and keyboard | Playwright adds a Formula, inserts a key reference, sees syntax feedback after blur, previews a stored row and saves. Rows shows the computed value and updates it after an input edit. Double-click keeps the formula cell read-only | Pass |
| Updating an existing Formula and displaying an error | Playwright edits the expression, confirms the result type is locked, and sees the division-by-zero diagnostic in the grid | Pass |
| Empty dataset and mobile dark mode | Playwright enters sample values, distinguishes null from an error, verifies a valid result and checks dialog bounds at 390 px | Pass |
| Authorization, no writes and stale schemas | Backend tests cover saved row and transitive sample preview, missing rows, stale revision, inaccessible dataset and Viewer denial, and unchanged persistence after preview | Pass |
| Existing behavior | Playwright CSV and grid regressions, 50 backend tests on SQLite and PostgreSQL, production build, strict UI lint and 191 frontend unit tests including locale parity | Pass |

## Gaps And Residual Risk

Preview uses the first 20 rows as examples. Formula configuration is opt-in. Standalone export parity and Relation implementation remain separate milestones.

## QA Outcome

Pass for review of the Studio Formula slice. Captured screenshots with live local Dataset data on desktop and mobile.
