# Task

## Metadata

- Project: superstep
- Task ID: TASK-0086
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0049
- Design IDs: none
- Architecture IDs: DEC-0055, DEC-0008

## Objective

Alignment guardrails: a UI convention, a Playwright alignment helper and spec, and a lint check, with every hit on
develop fixed or opted out with a reason.

## Scope

### In Scope

- `docs/ui-conventions.md` rule 11 and checklist item; `handbook/docs/en/reference/development.md` (en; the vi
  handbook is maintained by the localisation worker).
- `frontend/e2e/helpers/alignment.ts`, `frontend/e2e/alignment.spec.ts`.
- `frontend/scripts/check-ui-classes.mjs`, `npm run lint:ui`, CI `npm run lint` step, unit test
  `src/lib/__tests__/ui-class-check.test.ts`.
- Badge and TabsList `size="sm"` variants; the fixes in the components listed in REV-0079.

### Out Of Scope

- The chat / panel layout (#117, `mock/panel-layout`).

## Activity Log

- 2026-10-23: lint check found 54 hits on develop (plus 16 hand-sized icon Buttons once `size-*` on Button was
  added: 14 moved to `icon-xs`/`icon-sm`/`icon`, 2 opted out); the alignment spec found the editor header (28px buttons next to a 32px input and icon buttons) and the
  list header (28px approvals badge next to 32px icon buttons) on develop. Fixed; draft PR into develop.
- 2026-10-24: PR #118 merged into develop (5e1d1fa); moved to done by TASK-0110.

## Handoff Notes

- vi handbook: mirror the new paragraph in `handbook/docs/vi/reference/development.md`.
- Review REV-0079, QA QA-0079.
