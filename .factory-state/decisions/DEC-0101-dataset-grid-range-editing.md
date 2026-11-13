# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0101
- Status: Accepted 2026-11-13 (Asia/Saigon) by the owner (pt287u): library-first; custom code only when truly necessary and high value. Revisits DEC-0097 under its stated revisit condition.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0101, REQ-0100, REQ-0097
- Related Decisions: DEC-0097, DEC-0008
- Related Tasks: TASK-0341, TASK-0347, TASK-0349, TASK-0350, TASK-0354, TASK-0355

## Context

DEC-0097 chose TanStack Table with shadcn/ui rendering for single-cell editing and said to revisit the grid choice if multi-cell clipboard or spreadsheet navigation becomes a committed requirement. REQ-0101 adds range selection, clipboard paste, fill, frozen columns, grouping, summaries, and virtual scrolling, inspired by the owner's PolarBase spreadsheet. PolarBase implements these in its own Angular component, which Superstep cannot reuse.

The Studio grid uses `@tanstack/react-table` 8.21. The current stable TanStack Table line (9.x, 9.3.1 at planning time) adds a cell selection feature: click, drag, Shift extension, multi-range selection, and an API that returns the selected ranges' data for copying. TanStack Table has no paste or fill handle. `@tanstack/react-virtual` (3.x) provides row and column virtualization.

## Decision

Accepted, as the owner directed: stay as close as possible to the libraries already chosen, and write custom code only where the library has no support and the value is high.

- Use TanStack Table features for grid state: column ordering, sizing, visibility, pinning (frozen columns), manual pagination and sorting, and grouping and expanding state in manual (server-driven) mode. Column footers render server summaries.
- Upgrade the grid to TanStack Table 9.x stable (TASK-0350) and use its cell selection feature for range selection and copy. Use `@tanstack/react-virtual` for virtual scrolling and row heights.
- Use shadcn/ui components and theme tokens for all rendering (DEC-0008). Use the browser Clipboard API and a well-maintained parser (for example Papa Parse) for pasted TSV or CSV.
- Custom code is allowed only for these high-value gaps:
  - mapping pasted cells onto typed columns from the anchor cell, with a preview when rows would be added;
  - fill down and fill right of a selected range (Ctrl+D, Ctrl+R), built on the library selection;
  - one-step undo of the last batch.
- Keep the atomic batch save API (TASK-0354). Every multi-cell change is one server-checked batch with per-row revisions, types, validation, and unique checks. This is server-side by nature and not a grid concern.
- Not built now: a drag fill handle and series continuation (no library support, lower value; revisit after use), multi-level undo, custom virtualization, custom pinning, custom selection models.
- Grid layout preferences stay in browser storage, not on the server.

## Rationale

- One component system and theme tokens. Library upgrades carry most of the behavior, so less code to own.
- The remaining custom pieces are small and directly protect data or save the most manual work (bulk paste from spreadsheets).
- The server stays the single place for type, validation, unique, and revision checks.

## Alternatives Considered

- Gigatable: adds range selection, paste, fill, and undo to TanStack Table, but it is installed as copied source with its own theme. That is custom code to maintain under another design system. Not chosen.
- MonkeyTab: a young grid with a single maintainer and its own field model. Not chosen.
- React Data Grid or AG Grid (DEC-0097 alternatives): a second rendering system and, for AG Grid Enterprise, a commercial license. Not chosen.
- Build everything custom: against the owner's direction.

## Risks

- The TanStack Table 9 upgrade touches the existing grid. TASK-0350 runs the full grid Playwright suite before adding features.
- Accessibility of range selection needs explicit announcements and keyboard parity. TASK-0355 owns that.
- A paste larger than the batch limit is refused with a clear limit message, or split into confirmed batches.
- Every task that adds custom grid code lists it and its reason in the PR.
