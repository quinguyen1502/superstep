# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0102
- Status: Accepted for implementation on 2026-11-21
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Source: Owner request on 2026-11-21 to plan Formula and Relation. REQ-0099 had selected both for a later requirement as DS2-08 and DS2-09.

## Summary

Add two Dataset column types: Formula calculates a typed result from fields in the same row, and Relation lets a row reference one record in another dataset.

## Problem Or Opportunity

Operators have to recalculate derived values by hand and copy identifiers between datasets. Values can drift when a source cell changes, and a copied identifier can refer to a record that no longer exists.

## Scope

### In Scope

- **Formula.** Same-row references to compatible fields by stable column key, typed arithmetic, comparisons, an if expression and basic text concatenation. Support number, Boolean and text results. Formula columns are read-only and may depend on other eligible Formula columns in the same row. Show a preview and validate references, types and cycles before saving the schema.
- **Relation.** An optional many-to-one link to a row in a different dataset in the same ownership scope. A personal dataset targets another dataset owned by the same user. A team dataset targets another dataset owned by that team. Use a searchable row picker, a configured display column and an option to clear the link. The link stores the target row identity. The current display value appears when the reader can access the target.
- Preserve filtering, sorting, typed summaries where appropriate, and paging for Formula results. Provide Relation filters for target row identity and empty links. The picker supports server-side search and paging.
- Cover Studio, Dataset nodes, Agent tools, connected API, Python and TypeScript exports. Formula results are readable and unavailable in write mappings. Relation identities can be read or matched. Relation writes outside Studio require independently authorized target access and proof that the row exists. Agent Relation writes are deferred in the first release.
- CSV exports Formula results as scalar values and Relation links as target row IDs. Import skips Formula columns. Relation values can be imported only into a configured Relation with an explicit mapping and target authorization. Use a Dataset project export to carry schema and link dependencies across environments.

### Out Of Scope

- Cross-row formulas, Formula lookups through a Relation, rollups, spreadsheet coordinates, arbitrary code, and time-dependent or external functions.
- Same-dataset links, one-to-many editors, multi-value links, backlinks, cross-scope targets, cascading deletes and automatic cross-instance ID remapping.
- Runtime dereferencing of target labels or fields through a source Dataset grant alone. First-release workflow, Agent and token reads return only the stored target identity and require a separately scoped lookup to read target values.

## Desired Behavior

- In **Schema**, a manager chooses **Formula**, selects a result type and builds an expression with field references. For example, `[quantity] * [unit_price]` fills a read-only Total column for existing and new rows. The editor identifies the field or expression range that needs correction.
- A valid expression with incomplete inputs can return null. A row-specific error, such as division by zero, shows an error state in Studio and has a null value for projection, CSV and aggregation. Valid source edits still save. Existing row revisions and undo behavior reflect source edits and their recomputed results atomically.
- In **Schema**, a manager chooses **Relation**, its allowed target dataset and a text display column. In **Rows**, an editor can find and link a company to a support ticket with the keyboard or pointer. A viewer can inspect the visible label. Duplicate labels remain distinguishable in the picker and a label change is reflected on the next read.
- A target with incoming links cannot be deleted. Removing the link allows deletion to proceed. Errors identify the blocked action and direct the operator to clear references without disclosing hidden records.

## Business Rules

- Formula evaluation is deterministic and bounded. The server validates referenced types, null behavior, number range and output length. Formula definitions have no access to other rows, network, files, time or random values. Missing, archived and cyclic references fail schema validation.
- Recompute Formula values on each relevant write path, including CSV, batch/fill/undo, connected and authorized workflow writes. Schema edits that affect existing Formula values commit coherently and advance the schema revision. A referenced source column cannot be removed or changed incompatibly while a dependent formula uses it.
- Enforce target visibility, scope and relation integrity at the write boundary. A link creation and target deletion racing each other cannot both commit. A Relation definition protects the target dataset and its configured display column from schema or ownership changes that would invalidate it. A Relation column can be removed explicitly via the existing confirmation flow.
- Preserve current checks for write-only responses, grants, revision conflicts and idempotency receipts. Trace, audit and receipt records carry identifiers and outcomes without formula inputs or target labels.
- Validate export dependencies and backend compatibility before access. Each connected relation requires both bindings on one reachable Superstep instance. Each standalone relation requires both bindings in the same database. Unsupported binding combinations fail during setup without partial writes. Row snapshots remain opt-in for each binding.

## Acceptance Criteria

- On SQLite and PostgreSQL, add a Formula to an existing dataset. A single-cell edit, CSV import, batch write, undo and authorized workflow write update the result. Sorting, filters, aggregates and CSV agree on typed values and null handling. Reject dependency cycles and attempts to write calculated values.
- Link a ticket to a company via the Studio picker. A renamed label updates, a missing or inaccessible row cannot be linked, an existing link prevents target deletion and a concurrent link/delete test preserves integrity.
- A read-only role can browse Formula values and visible relation labels. It cannot edit definitions or rows. A source token or workflow grant cannot disclose target labels or row contents. Unauthorized, revoked, write-only and expired-session cases retain their existing behavior.
- Connected and standalone exports pass the common contract fixtures in Python and TypeScript. Existing datasets, bindings and exports still work after upgrade. A relation project reports an incompatible backend or missing target binding during setup.
- The Scenario in PLAN-0020 works with keyboard navigation, English and Vietnamese, mobile and desktop, and light and dark themes.

## Implementation Approval

- The owner authorized the proposed scope on 2026-11-21. Storage and compatibility decisions remain subject to the design review specified in the plan.

## Related Artifacts

- [Proposed delivery plan](PLAN-0020-dataset-formulas-and-relations.md)
- [Earlier selections](REQ-0099-dataset-writes.md)
- [Phase 3 scope](REQ-0101-datasets-phase-3.md)
- [Dataset design](DES-0007-datasets.md)
- [Dataset architecture](ARCH-0003-datasets.md)
- [Grid and export decision](../decisions/DEC-0097-dataset-grid-and-export.md)
