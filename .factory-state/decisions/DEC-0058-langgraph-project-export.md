# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0058
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Related Requirements: REQ-0053
- Related Architecture: DEC-0008
- Related Tasks: TASK-0090

## Decision

1. The project wraps the existing single-file export (engine.python_export / typescript_export) instead of a second generator: `graph = build_graph()` / `export const graph = buildGraph();` is appended.
2. TypeScript: `npm:` specifiers are rewritten to bare imports listed in package.json, and the example `main()` only runs with `RUN_EXAMPLE=1`, so importing the module (as the dev server does) has no side effects.
3. Zip entries have fixed timestamps so the same workflow gives the same bytes.
