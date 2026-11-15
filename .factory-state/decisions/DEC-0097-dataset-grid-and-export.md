# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0097
- Status: Accepted for planning
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Related: [Requirement](../artifacts/REQ-0097-datasets.md), [Architecture](../artifacts/ARCH-0003-datasets.md), [Plan](../artifacts/PLAN-0016-datasets.md)

## Decision And Rationale

- Use TanStack Table for table state and shadcn/ui for rendering and editors. The v1 requirements are single-cell editing and server-driven table operations. This follows the existing Studio component rules and keeps form and theme behavior consistent.
- Keep Studio data in its existing SQLite or PostgreSQL database using stable typed schema metadata and versioned JSON rows. Explicit grants authorize access from workflows and external API credentials.
- Give each Python and TypeScript export binding three configurable backends: Superstep API, standalone SQLite and standalone PostgreSQL. A standalone project carries schema and setup instructions, with permission-checked snapshot inclusion off by default.

## Alternatives Considered

- AG Grid Community supplies keyboard and scroll behavior but needs a grid component exception to Studio UI rules. AG Grid Enterprise adds multi-cell clipboard and fill with a commercial license.
- React Data Grid supplies an editable virtualized grid and a single-cell paste hook. Multi-cell paste still requires implementation. It also needs a grid component exception.
- Dedicated physical tables per Studio dataset would provide database-native user schemas at the cost of runtime DDL, migration and permission complexity.
- A connected-only export would share Studio data with less adapter work. Standalone deployment is part of the owner's requested outcome.

## Approval And Review

- The owner selected the proposed TanStack and shadcn direction and requested recording the requirement and tasks on 2026-11-12. The earlier owner request includes both connected and standalone exports with configuration.
- Revisit the grid choice if multi-cell clipboard or spreadsheet navigation becomes a committed product requirement. Revisit the storage model based on measured workload limits.
