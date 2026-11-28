# Design

## Metadata

- Project: superstep
- Design ID: DES-0008
- Status: Proposed for design review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Related: [Requirement](REQ-0102-dataset-formulas-and-relations.md), [Plan](PLAN-0020-dataset-formulas-and-relations.md), [Dataset design](DES-0007-datasets.md), [Architecture](ARCH-0004-dataset-formulas-and-relations.md)

## Schema

- A dataset manager adds **Formula** in the existing column form, then selects Number, Boolean or Text and edits the expression. Use a labeled expression input with a field picker that inserts `[field_key]` at the cursor. List only supported fields and present the user-facing field name beside its key. Required, unique and default settings are unavailable for formulas.
- A manager can preview the formula on a selected existing row or sample values in an empty dataset. The result uses the output type's existing display formatting. Structural diagnostics appear on blur, preview, or save. Keep the expression available and put focus on the expression when save fails. An incomplete row previews an empty result. A row-specific calculation error gives the reason at the preview without blocking a structurally valid definition.
- A manager adds **Relation** in the column form, selects a visible dataset in the same ownership scope, and chooses an active text display column. Place Column type and Target dataset side by side at equal widths on desktop and stack them at narrow widths. Display column sits underneath. Show empty options and permission errors in their own states. Keep the target immutable after creation for the first release. The display column can be changed within the same target. The schema names the target and explains that linked records must be unlinked before deleting them.

## Rows

- Formula cells retain the existing type-specific rendering, format, keyboard selection, copy and read-only states. Show a Formula icon in the column header. Use an accessible cell error indicator for a null result caused by a calculation error. Keep the grid row height and disclose the error on focus or activation.
- A Relation cell opens a searchable row picker on double-click or Enter for editors. The first page loads on open. Search and Next page update the result set, with keyboard navigation and focus return to the originating cell. Labels that occur more than once show a secondary row identifier. Empty labels fall back to row identifiers only for readers who can access the target.
- Selecting a row commits one revision-checked edit. Escape dismisses the picker and returns focus. Clearing the saved link uses the existing confirmation flow for unlinking. A permission or revision change keeps a localized actionable error visible and preserves the previous saved value.
- A Viewer can inspect a Formula result and a visible Relation without write controls. When target visibility is lost, show an unavailable state for the link. A failed target deletion retains the row and explains that incoming links must be cleared.
- Use the existing shadcn controls, theme tokens, translated labels and narrow-grid behavior. Verify focus, disclosure, loading, empty search, missing target, referential error, and stale-schema states in both locales and themes.

## Workflow And Export

- Dataset and Agent read selections treat Formula results as their scalar type. Mapping selectors omit computed fields from writes. Relation selections label the identity result and use the existing Dataset lookup flow for a separately authorized target read.
- Export lists the target binding as an explicit dependency. Show setup incompatibilities against the affected binding. Snapshot inclusion remains an explicit selection per binding. Shared export, API and handbook instructions explain result nulls and how to remap relation identities between environments.
