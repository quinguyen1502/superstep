# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0098
- Status: Accepted 2026-11-13 by the owner, who asked to open the pull request after the Dataset review found no further UI changes
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-13
- Source: Owner chat 2026-11-13, after reviewing Settings and editor screenshots
- Related: DEC-0008, DEC-0025, docs/ui-conventions.md

## Summary And Scope

Studio form controls should match the width of the group they belong to, external-link icons should come before their labels, and a typed delete name should read as bold text inside double quotes.

In scope:

- Node connection headings state the count in one phrase, in English and Vietnamese.
- Handbook and Grafana links put the external-link icon before the label.
- The monthly budget form fills its columns. The create-team row matches the width of one team card. A form with a single field stays compact.
- The shared delete confirmation renders the typed name as bold text inside quotes. The API stays a plain DELETE.
- A select in a multi-field question card fills its column.

Out of scope: Dataset catalog, grid, access, CSV, and export dialogs. Those layouts already follow the same rules. Also out of scope: new product behavior, new colors, and any confirm field on the API.

## Business Rules

- Theme tokens and shadcn components only (DEC-0008). No hard-coded status colors.
- Delete confirmation stays UI-only (DEC-0025, docs/ui-conventions.md rule 7).
- English and Vietnamese catalogs keep identical keys.
- A lone field is not stretched across a wide settings column. A row that sits above a card grid uses the same column width as one card.

## Acceptance Criteria

- A selected node shows the connection count inside the heading, with English plural forms and a matching Vietnamese phrase, instead of a detached number.
- External-link icons on the handbook link and the Usage Grafana links precede the label.
- Budget selects and the amount row span the form. The create-team control matches one team card. The access-token name field stays `max-w-md`.
- Typed delete names render as bold quoted text, and the Playwright helper reads `[data-confirm-name]`.
