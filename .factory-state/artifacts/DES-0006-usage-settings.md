# Design

- Design ID: DES-0006
- Project: superstep
- Status: Proposed 2026-11-09, awaiting owner acceptance
- Created/Updated: 2026-11-09
- Related: REQ-0094, PLAN-0013, TASK-0288, TASK-0289, TASK-0290

The owner reviewed a static preview of the page in chat on 2026-11-09 (Overview, Models, Server and queue, Product). This design narrows it to what the MVP can show truthfully from the database; server and queue charts live in Grafana, and per-model tables wait for the usage table (phase 2).

## Placement

- Settings section id `usage`, route `/settings/usage`, added to `SECTION_IDS` and `SECTIONS` in `frontend/src/pages/settings/sections.ts` directly before `activity`, permission `users.manage`, lucide icon `ChartColumn` (or the nearest existing chart icon). Component `UsageSection.tsx` mapped in `SettingsPage.tsx` like the other sections; the command palette picks it up from `sections.ts`.
- No new entry in the main sidebar. The run panel keeps per-run totals.

## Layout

1. Header: title "Usage", one-line description, window picker (24 hours, 7 days, 30 days; default 7 days), and a muted note that cost is an estimate from the price table.
2. Summary cards: runs, success rate, tokens in / out, estimated cost, unpriced runs (count and share, with a link to the handbook section on `STUDIO_PRICES`).
3. Runs over time: stacked bars by status (ok, error, timeout, cancelled), one bar per hour (24 h) or per day.
4. Top workflows table: workflow name, runs, error rate, tokens, cost, unpriced runs; up to 10 rows, sortable by runs or cost; a deleted workflow shows its id.
5. Product health (TASK-0290): waiting approvals (count, oldest age), approvals expired in the window, webhook deliveries failed and retrying, overdue schedules, schedules disabled by the scheduler with their note.
6. Footer: link to the handbook observability page and, when the server reports one, a link to Grafana (`STUDIO_GRAFANA_URL`, optional).

## States

- Loading: existing skeleton pattern. Empty window: "No runs in this window". API error: the existing inline error alert with retry.
- Without `users.manage`: the section is not listed and a direct visit shows the existing permission message.
- When every run is priced, the unpriced card shows 0 and no warning; when the unpriced share is above zero, the cost card shows an "at least" prefix.

## UI Rules

- shadcn default sizes, existing Card, Table, Tabs/Select and alert patterns; charts with the chart helper already used in the app, otherwise plain CSS bars (no new chart dependency in the MVP).
- Every string in `frontend/src/locales/en.json` under `settings.usage.*` with the vi entry in `vi.json` following `vi-glossary.md`; locale parity tests pass.
- Numbers use the user's locale formatting; cost shows USD with up to 4 decimals below 1 USD.

## Phase 2 (not in the MVP)

- Per-model table (tokens, cost, errors, fallbacks) and per-user/per-team breakdown once a usage table is written at run end.
- Channel refusal codes (`chat_message.status = refused` grouped by `code`, approval log `code`): deferred because `chat_message` has no index on `created` or `status`, and adding the index plus channel semantics would bloat the first slice.
