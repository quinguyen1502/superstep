# Task

## Metadata

- Project: superstep
- Task ID: TASK-0289
- Title: Settings Usage section
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: M

## Objective

Add the Usage section at `/settings/usage` per DES-0006.

## Scope

### In Scope

- `usage` in `SECTION_IDS`/`SECTIONS` before `activity`, permission `users.manage`, icon; `UsageSection.tsx` mapped in `SettingsPage.tsx`.
- Window picker, summary cards, runs-over-time bars, top workflows table, unpriced note and handbook link, optional Grafana link from a new optional `STUDIO_GRAFANA_URL` (exposed read-only to admins; documented in `.env.example`).
- English strings and vi catalog entries under `settings.usage.*`; glossary-consistent vi.
- Unit tests for formatting and empty/error states; a Playwright spec for the admin view and the hidden section for a viewer.

### Out Of Scope

- Product health block (TASK-0290); per-model tables (phase 3).

## Dependencies

- TASK-0288 merged.

## Acceptance Criteria

- An admin sees the section next to Activity and the numbers match the API; a viewer does not see it and a direct URL shows the permission message.
- Locale parity tests pass; shadcn default sizes; no new chart dependency.
- Handbook screenshot capture spec gains the Usage page only if TASK-0292 uses it.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
- 2026-11-09: `usage` added to `SECTION_IDS`/`SECTIONS` before `activity` (permission `users.manage`, `ChartColumn` icon); `UsageSection.tsx` mapped in `SettingsPage.tsx`. Window picker (default 7 days), summary cards, runs-over-time bars in plain CSS with theme tokens, top workflows table sortable by runs or cost, an "at least" cost when some runs have no price and a link to the price settings, loading skeleton, empty and error states with retry, handbook link and an optional Grafana link from `STUDIO_GRAFANA_URL` (returned only to admins in the usage response; `.env.example` and the configuration reference in both languages).
- 2026-11-09: `settings.nav.usage`, `settings.intro.usage` and `settings.usage.*` in en and vi; `settings.usage.col.workflow` stays "Workflow" per the glossary and is on the reviewed same-as-English list.
- 2026-11-09: Tests: `src/lib/__tests__/usage.test.ts` (number, money, share and age formatting, unknown share, bucket totals); `e2e/usage.spec.ts` (admin sees the section and the workflow it ran, window switch; a member has no Usage entry and `/api/admin/usage` answers 403).
- 2026-11-09: Deviation: a member opening `/settings/usage` directly is redirected to Profile by the existing Settings page rule for admin sections (the same as Users and Activity), instead of seeing a permission message; the section still renders the admin-only alert if it is ever mounted without the permission. No screenshot capture was added.
- 2026-11-09: Review REV-0275 and QA-0275. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0275-TASK-0289-usage-settings-section.md`
- QA: `.factory-state/artifacts/QA-0275-TASK-0289-usage-settings-section.md`
