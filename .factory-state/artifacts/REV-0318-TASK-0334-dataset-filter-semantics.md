# Review

## Metadata

- Project: superstep
- Review ID: REV-0318
- Task ID: TASK-0334
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for null-safe `ne` and case-insensitive contains, search, and text sort against REQ-0100, PLAN-0018, and the TASK-0334 acceptance criteria. The Dataset node, Agent tool, Studio grid filter, handbook, and changelog were reviewed. Standalone export runtimes were checked to stay unchanged.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md
- docs/backend-architecture.md

## Findings

### Blocking

- None.

### Non-Blocking

- PostgreSQL folds with `lower` under the `und-x-icu` collation, else `pg_c_utf8`, else the database default. The collation is looked up once per engine. A PostgreSQL 16 or older server without ICU and with a `C` ctype folds only ASCII. PostgreSQL 17 always has `pg_c_utf8`. Local tests ran on PostgreSQL 16 with `C.UTF-8` and no ICU, which uses the default-collation path. CI runs PostgreSQL 17, which uses the ICU path.
- Case folding does not normalize Unicode composition. A value typed in decomposed form (NFD) does not match a composed (NFC) query. Browsers and CSV files normally send NFC.
- SQLite registers a Python `lower` function on each connection. On 10,000 rows the measured query time matched the previous build within noise.

## Standards And Architecture Alignment

- `ne` compiles to `IS DISTINCT FROM` (SQLite `IS NOT`) for every kind, boolean included.
- `eq`, `lt`, `lte`, `gt`, `gte`, unique-key lookup, and upsert matching keep the exact binary comparison.
- Text sort orders by the folded value, then the exact value, then row id, so ties are stable and the same on both databases.
- The repository layer owns the SQL. The fold function lives in `core/dataset_types.py` and is registered in `models/database.py`. No layer rule changes.

## Design Alignment

- The grid filter shows one line that explains Equals, Is empty, and search. The node editor explains the selected operator under the operator control. Both are in English and Vietnamese.
- Agent tool schemas describe the operator semantics.

## Test Coverage Review

- New SQLite and PostgreSQL row tests cover `ne` on number, text, and boolean with empty cells, search and contains in three letter cases, Vietnamese letters with diacritics, exact `eq`, and ascending and descending text sort with ties.
- New Dataset node and Agent tool tests cover contains with a different case and `ne` with an empty cell.
- Playwright checks the grid help text, a search in a different case, and the node editor operator help.

## Risk Review

- Saved workflows that use `ne` or `contains` can return more rows. The changelog and handbook state it.
- Standalone Python and TypeScript exports keep the old semantics until TASK-0343.

## Required Fixes

- None.

## Approval Decision

Approved for QA.
