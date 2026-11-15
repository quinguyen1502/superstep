# Design

## Metadata

- Project: superstep
- Design ID: DES-0007
- Status: Planned
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Related: [Requirement](REQ-0097-datasets.md), [Architecture](ARCH-0003-datasets.md), [Plan](PLAN-0016-datasets.md)

## Information Architecture And Flows

- **Datasets.** The authenticated Studio destination uses a full-width workbench with a left-aligned dataset catalog grouped by scope. The catalog heading shares a row with Create and Collapse. The collapsed desktop rail keeps icon navigation and the narrow layout folds the list under its header. The collapse preference persists in the browser. A dataset opens on Rows, with Schema and Access available as sibling views. Empty and inaccessible states explain the available action without exposing private metadata.
- **Create dataset.** Choose a name and owner scope, then add typed columns or preview a CSV with inferred headers and suggested types. Review source-to-field mapping, required values, defaults, select options and unique keys before applying. Show field and row errors with locations. CSV export has an explicit action and applies the user's read permissions.
- **Rows.** Use a spreadsheet-style grid with vertical dividers, typed column headers, numbered rows and visible-page row selection. Filter and Sort sit in the grid toolbar. A click selects a cell, arrow keys move between cells, and double-click, Enter or the selected-cell edit action opens its typed editor. Add row opens a draft within the grid. Search, typed filters, sorting and pagination use the Dataset API. Activate a cell to open its type-specific shadcn editor. Enter commits where appropriate, Escape cancels, and validation or a stale version leaves the draft available for correction. Use the shared typed confirmation for row and dataset deletion. Rows without a business key use the displayed stable row identifier in confirmation.
- **Schema.** Show editable labels, stable field keys, types, defaults and constraints. Warn when a change would invalidate a binding or existing data and direct the user to resolve it. Use shared typed confirmation for column removal.
- **Access.** Authorized managers see team access and explicit workflow grants. Show the workflow, dataset and allowed operations before saving. Revoke grants and external tokens through shared typed confirmation. Show external token secrets once, with an explicit copy control.
- **Canvas.** Add the Dataset node from the palette. Select an accessible dataset binding and operation. Find rows shows filters, selected fields and limit. Get row shows the row identifier. Insert and Upsert show typed input mapping, with a unique key picker for Upsert. Surface missing access, removed fields and incompatible schema in validation. Test mode labels simulated writes.
- **Agent.** Add a read-only Dataset tool scoped to one binding and an allowed output column list. Show tool outcomes and counts in the run trace without emitting additional copies of row values.
- **Export.** Extend the project export flow for both languages with a table of dataset bindings. Each binding displays its operations and a backend choice: Superstep API, SQLite or PostgreSQL. Show the configuration fields in the project README and `.env.example`. Provide an unchecked snapshot option for standalone bindings and show that it includes row data. Explain that standalone data changes in the selected database.

## Accessibility And States

- Use shadcn components and theme tokens with English and Vietnamese locale parity. Keep semantic table headers and accessible sorting state. Make row and schema actions keyboard reachable without hover. Restore focus after cell editing and dialogs.
- Cover loading, empty, no matches, validation failures, access revoked, stale edit and retryable service errors. Announce updates and associate errors with the affected field. Use a horizontal table scroll container on narrow screens and keep schema and export forms usable at mobile widths.
- Capture evidence in both themes and representative desktop and mobile layouts. The interactive prototype shown in the owner discussion covers browsing and workflow lookup/upsert using mock data. This design defines the additional creation, CSV and export flows.
