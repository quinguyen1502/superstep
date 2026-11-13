# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0101
- Status: Proposed 2026-11-13 (Asia/Saigon); awaiting owner acceptance of this requirement, PLAN-0019, and DEC-0101
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Source: Owner chat 2026-11-13 (pt286u, asking for a Datasets phase 3 plan based on the ideas worth borrowing from PolarBase, https://github.com/polarbase-team/polarbase, the owner's own project; reference clone at commit `5a717f4`).
- Related: REQ-0097, REQ-0099, REQ-0100, DES-0007, ARCH-0003, DEC-0097, DEC-0098, DEC-0101, PLAN-0019, TASK-0345 to TASK-0358

## Summary

Datasets phase 3 makes operational tables easier to query and maintain: nested AND/OR filters with more operators, server-side column summaries and grouping, an aggregate operation so Agents answer counting questions without reading rows, a grid that handles wide and long tables, more field types that fit the one-JSON-row storage, per-column validation and display formats, and (behind DEC-0101) range paste and fill.

## Scope

### In Scope

| Area | From PolarBase | Superstep shape | Tasks |
| --- | --- | --- | --- |
| Query | Filter groups and operators (`field-system/filter/models.ts`, `where-filter.schema.ts`) | Filter tree with AND/OR groups (depth 3, 20 rules); `in`, `not_in`, `not_contains`; same contract for API, Dataset node, Agent tool, and exports | TASK-0345, TASK-0346 |
| Grid | Column calculations, grouping, frozen columns, row height, virtual scroll | Server-side summaries for the current filter; group by one column; freeze up to 3 columns; row height; `@tanstack/react-virtual` | TASK-0347, TASK-0349, TASK-0350 |
| Agent | Database MCP tool split with aggregate-style tools | `aggregate_rows` operation for the Agent tool and the Dataset node, read grant, at most 20 groups | TASK-0348 |
| Fields | Long text, URL, multi-select, auto-number, created and updated time | Same kinds stored in the JSON row or derived from row metadata | TASK-0351, TASK-0352 |
| Rules | Field validation and display formats | Min and max length, value, date; email domains; number and date display formats; enforced by every writer | TASK-0353 |
| Editing | Clipboard and fill handle | Range selection, TSV paste, fill series, atomic batch API (DEC-0101) | TASK-0354, TASK-0355 |
| Export | — | Python and TypeScript parity for every operator, operation, kind, and rule that reaches an exported project | TASK-0356, TASK-0357 |

### Out Of Scope

| Item | Reason |
| --- | --- |
| Agent or MCP tools that create tables or change schema | REQ-0097 excludes arbitrary SQL and external database administration; schema stays a manager action in Studio with binding checks. |
| External MCP exposure of datasets | REQ-0097 defers external MCP exposure; the aggregate operation is an Agent tool inside workflows only. |
| Relations, formulas, attachments, JSON, and map fields | REQ-0097 excludes formula columns and cross-table relations; attachments and JSON break the typed one-row contract and the export parity of DEC-0097; map has no product use case yet. |
| Calendar, map, Gantt, Kanban, and dashboard views; saved or shared views | REQ-0097 defers saved views and calendar and map views. Grid layout stays a personal browser preference. |
| Realtime change feeds and change triggers | REQ-0097 defers change triggers; Studio refreshes on demand. |
| Feature-scoped API keys | Superstep keeps per-dataset, per-operation tokens (REQ-0097, DEC-0098), which are narrower. |
| PolarBase Angular components | Studio stays on TanStack Table and shadcn/ui (DEC-0008, DEC-0097). Ideas are reimplemented, not copied. |
| Multi-level grouping, regular expression rules, conditional formatting | Not needed for the support-ticket scenario; revisit after phase 3. |

## Business Rules

- The flat `filters` and `filter_mode` form stays valid and maps to one group; saved workflows keep working.
- Every new operator follows REQ-0100 semantics: null-safe negation, case-insensitive text matching, exact `eq` and unique keys.
- Summaries, grouping, and `aggregate_rows` need read permission. A write-only grant or an Agent tool without Aggregate cannot use them. Results contain aggregates only; traces and audit carry operation, counts, and outcome, never cell values.
- System fields (`created_time`, `updated_time`, `auto_number`) are read-only for every writer. Auto-numbers are assigned under the writer lock and never reused.
- Validation rules apply to Studio edits, CSV import, the Dataset node, the Agent tool, connected tokens, batch edits, and standalone exports. Adding a rule that existing rows violate is refused with a count and sample rows.
- Display formats change presentation only.
- Batch edits (DEC-0101) are atomic per batch and check each row's revision.
- Row, column, byte, and query limits of REQ-0097 still apply; new limits (tree depth and size, `in` values, groups, batch size) are part of the contract and the error messages.

## Acceptance Criteria

- A support lead filters `(status in [open, pending]) AND (priority = high OR csat < 3)`, sees count, empty percent, and average csat in the summary row, groups by team, and the numbers match SQL on SQLite and PostgreSQL.
- An Agent answers "how many open high-priority tickets per team" with one `aggregate_rows` call; the trace contains no row values.
- Each new field type and rule works in Studio, CSV, the Dataset node, the Agent tool, and both exports.
- With DEC-0101 accepted, a 5x20 paste from a spreadsheet updates in one batch and can be undone.
- English and Vietnamese UI and handbook; keyboard reachable; both themes.

## Constraints

- REQ-0100 fixes TASK-0332 to TASK-0344 land before phase 3 tasks that depend on them (see PLAN-0019).
- Backend layers, error catalog, locale parity, shadcn/ui, and theme tokens as in REQ-0099.

## Open Questions

- DEC-0101: grid range editing approach (recommended: Option A, TanStack and shadcn with a batch API).
- Grid layout persistence: browser only (recommended) or per user on the server.
- Multi-select CSV delimiter: `;` (recommended) or JSON array text.
- Regular expression validation rules: not recommended.
- REQ-0099 lists selections DS2-08, DS2-09, and DS2-11 to DS2-16 for later requirements; their definitions are not recorded in the repository. Confirm whether this phase 3 replaces them or which of them should be added.
