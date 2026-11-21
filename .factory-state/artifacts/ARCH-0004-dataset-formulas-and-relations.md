# Architecture

## Metadata

- Project: superstep
- Architecture ID: ARCH-0004
- Status: Proposed for design review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Related: [Requirement](REQ-0102-dataset-formulas-and-relations.md), [Design](DES-0008-dataset-formulas-and-relations.md), [Plan](PLAN-0020-dataset-formulas-and-relations.md), [Base architecture](ARCH-0003-datasets.md), [Storage decision](../decisions/DEC-0102-dataset-formula-relation-storage.md)

## Formula Contract Version 1

- A Formula definition carries its expression and version in optional column metadata. The column's existing scalar kind describes the materialized result. Supported results are number, Boolean and text. Key references are case-sensitive and use the existing column key pattern in brackets.
- Scalar inputs include Number and Auto-number as numbers, Boolean, and Text, Long text, Select, URL and Email as strings. Exclude multi-values, date/time, system timestamps and Relation from expressions. Read Formula dependencies with their declared output kind after topological ordering.
- Tokens include booleans `true` and `false`, decimal or exponent numeric literals, JSON-style double-quoted strings, bracketed fields and parentheses. Binary precedence from tightest to loosest is multiplication and division, addition and subtraction, text concatenation `&`, then comparisons. Unary plus and minus bind more tightly. Operators at the same precedence associate to the left. Equality and inequality require equal operand types and compare text exactly. Ordered comparisons require numbers. `IF(test, yes, no)` requires a Boolean test and matching branch types and evaluates only the selected branch.
- Null or missing operands produce null. An IF with a null test produces null. Evaluate both binary operands from left to right and report the first evaluated error. A reference to a failed formula propagates a dependency error at the new column. Cycles are rejected when compiling the whole schema even if an IF might skip one edge.
- Limit source to 1,024 Unicode code points, tokens to 256 and parser nesting to 24. The Dataset column limit also bounds dependency depth. Use binary64 arithmetic within the existing Dataset number range, normalize zero and reject non-finite or out-of-range results at each evaluation step. Existing text limits apply to intermediate and final values.
- Use structured schema diagnostics with the Formula column key, reason, optional referenced key, and optional zero-based Unicode code point offset. Cell diagnostics are machine-readable reasons keyed by Formula column. Division by zero, invalid input, an out-of-range number, excess text and a failed dependency produce null results. A failed row calculation does not abort a valid input edit. Structural invalidity aborts the schema change. Fixtures under `backend/tests/fixtures/dataset_formula_contract.json` define the initial cross-runtime cases.

## Storage And Write Boundaries

- Add nullable Formula metadata on column definitions and nullable cell-diagnostic metadata on rows together in an additive migration. Store evaluated scalar values in the existing row values object so ordered reads, filters, aggregates and exports reuse the existing typed queries. Row projections return diagnostics only for projected formula columns in authorized reads. Connected bindings carry optional versioned formula definitions and validate them before write. Standalone Python and TypeScript use the same contract and fixtures.
- Compile the active schema once per operation or revision. Recompute from a complete normalized row after defaults and auto-number assignment, including row insert, upsert, patch, batch additions, fill, undo and CSV. Persist values and diagnostics in the same transaction as the source change. Rejected writes and simulated writes leave the database unchanged. Replay returns the same identifier-only receipt semantics and reads current authorized values where applicable.
- During Formula add or expression update, acquire the existing dataset writer lock and verify the expected schema revision. Use ordered pages of row IDs to backfill in one transaction and advance affected row revisions. Validate the total stored value and response budgets. A compatible schema or label change does not backfill. Block removing a referenced field and converting a plain column to a Formula in place. If analysis shows the transaction cannot satisfy the writer-lock budget, return to design before enabling large backfills.
- Keep computed keys out of all write mappings and unique-match fields. Existing definitions and bindings without metadata retain their shape. Avoid creating Formula schemas for general use until Python and TypeScript standalone both have compatible writers. Older application releases must not write datasets with configured formulas during a rollback because they cannot recalculate their results. Operators may restore the pre-enable backup or freeze affected writes and revalidate the data on upgrade.

## Relation Contract

- Relation column metadata names one stable target dataset ID and one display column key in the same personal or team scope. A normalized edge row is the authority for a saved cell. Key the edge by source dataset, row and field, and index target dataset and row for reverse checks. Add named foreign keys to the source column and both dataset rows where supported. Read relation IDs from the edge and batch display-label queries for authorized visible targets. Apply supported relation filters before paging.
- Acquire existing dataset write locks in ascending identifier order for link edits and for operations that may affect links or definitions. Revalidate the source and target scope, permissions, expected revisions and target existence after acquiring locks. A target deletion checks reverse edges under its lock. Surface a localized conflict without revealing inaccessible referrers. Delete outgoing edges during authorized source removal. Dataset, team and account cleanup must remove edges in its authorized deletion set without silently detaching unrelated datasets.
- The SQLite app does not depend on FK enforcement for existing tables. App writer lock and existence checks enforce the invariant on both engines, with foreign keys as defense in depth where enforced. Verify concurrent delete/link behavior and rollback with CI on both engines before enabling.
- Preserve the source Dataset grant, row projection and receipt rules. Link edits beyond Studio require a separate current permission or capability on the target, checked at mutation time. An authorized source projection can carry the stored ID. Target metadata, labels, search results and rows require target read permission. Derive no disclosure of target data through response metadata or diagnostics alone.
- Export relation dependencies by portable binding name. Connected target and source must share a Superstep instance. Standalone target and source must share the same actual database. Reject incompatible or unresolved dependencies before row access and preserve explicit per-binding snapshot consent. Target credentials are deployment settings.

## Validation Gates

- Additive migration and compatibility review precedes storage work. Release exposes each field after read, write, permission and export parity. Record pre-enable backup, affected-write freeze, compatibility check and restore steps before rollout.
- Run old-to-new SQLite and PostgreSQL migration tests, batch rollback and receipt replay tests, parallel link/delete tests, permissions and redaction suites, and cross-runtime conformance fixtures. Measure lock duration on 10,000 and 25,000 rows and label lookup cost for a page.
