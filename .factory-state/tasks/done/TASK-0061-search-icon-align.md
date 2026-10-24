# Task

## Metadata

- Project: superstep
- Task ID: TASK-0061
- Status: done (PR #77)
- Phase: release
- Owner: Thái Quí Nguyễn
- Created: 2026-10-20
- Updated: 2026-10-20
- Requirement IDs: none (a UI fix reported by the owner)
- Design IDs: none
- Architecture IDs: DEC-0008

## Objective

Center the search icon, and the clear button, in the search boxes. The owner reported that the icon sat low in the
audit log search box.

## Cause

The input is `h-8` (32 px). The 16 px icon was placed at `top-2.5` (10 px), so it sat 2 px low. The clear button had
the same kind of offset: `top-1` with `size-7` in Workflows, and `top-0.5` with `size-8` (taller than the input) in
`FilterBar`.

## Fix

- The icon uses `top-1/2 -translate-y-1/2` and `pointer-events-none`.
- The clear button is `right-0.5 top-0.5 size-7`. It uses no translate, so the Button's active `translate-y` still
  works.
- Files: `components/settings/filter-bar.tsx` (Channels and Audit log) and `pages/Workflows.tsx`. Theme tokens only.

## Acceptance Criteria

- The icon and the clear button are vertically centered in the input.

## Validation

- In the browser (dev server, local demo account), measured with `getBoundingClientRect`:
  - Audit log: icon 8 px above and 8 px below, clear button 2 / 2 px, both in a 32 px input.
  - Workflows: icon 8 / 8 px.
- `npm run build`, `npm run lint` and `vitest run` (58 passed).
- CI on PR #77 (commit `8ac56b8`): all six checks passed.

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review none recorded at the time; QA none recorded at the time; develop verified retroactively by QA-0085.
