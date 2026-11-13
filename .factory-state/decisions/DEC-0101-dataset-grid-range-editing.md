# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0101
- Status: Proposed 2026-11-13; awaiting the owner's choice. Revisits DEC-0097 under its stated revisit condition.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0101, REQ-0097
- Related Decisions: DEC-0097
- Related Tasks: TASK-0350, TASK-0354, TASK-0355

## Context

DEC-0097 chose TanStack Table with shadcn/ui rendering for single-cell editing and said to revisit the grid choice if multi-cell clipboard or spreadsheet navigation becomes a committed requirement. REQ-0101 proposes range selection, clipboard paste, and a fill handle, inspired by the owner's PolarBase spreadsheet. PolarBase implements these in its own Angular spreadsheet component, which Superstep cannot reuse.

## Options

- Option A (recommended): keep TanStack Table and shadcn/ui. Build range selection, TSV copy and paste, and a fill handle as a Datasets grid module, add `@tanstack/react-virtual` for scrolling, and apply changes through one atomic batch API (TASK-0354).
- Option B: adopt React Data Grid with a grid component exception to the Studio UI rules. Faster keyboard and virtualization; multi-cell paste still custom; second styling system.
- Option C: AG Grid Enterprise. Complete clipboard and fill; commercial license and a component exception.
- Option D: do not ship multi-cell editing; keep CSV import for bulk changes.

## Decision

Proposed: Option A. TASK-0354 and TASK-0355 stay blocked until the owner accepts this decision or picks another option.

## Rationale

- Option A keeps one component system and theme tokens (DEC-0008), and the batch API keeps the server the single place for type, validation, unique, and revision checks.
- Range editing in Option A is a bounded module (selection model, TSV parser, fill series), similar in size to what PolarBase built.
- Options B and C add a second rendering system or a license for one screen.

## Risks

- Accessibility of range selection needs explicit announcements and keyboard parity; TASK-0355 owns that.
- Paste of many cells can exceed the batch limit; the UI splits into confirmed batches or refuses with a clear limit message.
