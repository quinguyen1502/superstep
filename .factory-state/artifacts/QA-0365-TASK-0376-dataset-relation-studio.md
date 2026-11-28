# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0365
- Task ID: TASK-0376
- QA Owner: Codex
- Created: 2026-11-28
- Updated: 2026-11-29
- Outcome: local acceptance and reviewed-head CI passed

## Acceptance Coverage

- Schema Playwright coverage checks same-scope options, text display columns, the empty display-column state, saving a definition, changing the display column and keeping the target fixed. The controls align side by side on desktop and stack at 390 pixels.
- Rows Playwright coverage opens by Enter, chevron and double-click. The picker loads pages and server search, distinguishes duplicate labels by row ID, returns focus on Escape and saves with the keyboard.
- The grid displays renamed labels on the next read. Filters match a selected record's identity or an empty link. Referenced deletion shows the API conflict in the existing confirmation and leaves the target row present.
- The shared unlink confirmation checks the exact linked label and returns focus. A stale write preserves the previous link. A viewer reads authorized labels and an unavailable lookup clears the visible label.
- New UI uses existing shadcn Select, Popover, Command, Alert, Button and shared confirmation components. English and Vietnamese catalogs use the same keys and pass the glossary test. The changes add no new theme colors or control size overrides.

## Results

- Nine Playwright cases passed on the disposable SQLite stack covering Relation, Formula, grid and public Dataset share regressions.
- All three Relation cases passed again after the final dialog width change and mobile localization assertion. Screenshots verify the desktop Schema dialog in English light mode, the mobile Schema dialog in Vietnamese dark mode, and the searchable Rows picker in dark mode.
- Root build and lint passed. Vitest passed 191 Studio, 22 React package and 117 TypeScript SDK tests. Factory hygiene and artifact IDs passed.

- [PR #437](https://github.com/quinguyen1502/superstep/pull/437/checks) passed 24 CI checks on reviewed head `84357ac2`. The container publish job was skipped.

## Gaps And Follow-Up

- The existing API preview flag remains off by default. The task uses the merged transactional Relation persistence and adds no database migration.
- Connected Relation bindings, workflow runtime and standalone exports remain in the [approved plan](PLAN-0020-dataset-formulas-and-relations.md).

## QA Decision

Local acceptance and reviewed-head CI passed. The owner approved integration pending CI on the final head.
