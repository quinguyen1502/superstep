# Task

## Metadata

- Project: superstep
- Task ID: TASK-0289
- Title: Settings Usage section
- Status: backlog
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
