# Task

## Metadata

- Project: superstep
- Task ID: TASK-0375
- Title: Store and authorize Dataset Relations
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-28
- Updated: 2026-11-28
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Add an opt-in backend Relation contract with durable same-scope link integrity and authorized target lookup. Establish the database contract for the later Studio, Connected and export work.

## Scope

- Store immutable target Dataset and editable display field metadata and normalized many-to-one row edges. Link and unlink through revisioned, authenticated Studio APIs.
- Reuse existing Dataset writer locks in sorted ID order. Check destination existence and source and target authorization after locking.
- Protect referenced definitions and rows against explicit, batch and granted deletion. Team and account cleanup can remove links wholly within the deletion set. Reject unlink-less deletion that would affect a surviving Dataset.
- Query link identities before paging, disclose target labels only through an authorized target lookup. Public shares, Connected relation bindings, relation imports and generated workflow projects stay outside this slice.

## Acceptance Criteria

- Fresh and upgraded SQLite/PostgreSQL databases support named edge keys and a reverse index. Downgrade guards active definitions.
- Same personal or team scope, current read permission on the target, valid display column and current source revision are required. Unavailable targets return the same generic error.
- Link edits, replacements and unlinks update row and data revision atomically. Link/delete races preserve referential integrity. Role and membership changes are respected at the write boundary.
- Row, column, Dataset, team and account cleanup preserve references or remove only edges in the authorized deletion set. Linked row errors carry no referrer identity.
- Bearer Dataset and public share capabilities cannot browse target labels or write Relation cells.

## Validation Plan

Run layered API and repository tests on SQLite and PostgreSQL 17, additive migration and rollback tests, link/delete races, authorized lookup and data revision tests. Verify published spec drift, both locale catalogs, Factory hygiene and full CI.

## Related Artifacts

- [Plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md)
- [Requirement](../../artifacts/REQ-0102-dataset-formulas-and-relations.md)
- [Design](../../artifacts/DES-0008-dataset-formulas-and-relations.md)
- [Architecture](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md)
- [Storage decision](../../decisions/DEC-0102-dataset-formula-relation-storage.md)

- [Review](../../artifacts/REV-0364-TASK-0375-dataset-relation-storage.md)
- [QA](../../artifacts/QA-0364-TASK-0375-dataset-relation-storage.md)

## Activity Log

- 2026-11-28: Started the next approved Dataset milestone after Formula runtime and export merged. Keep Relation behind a server preview flag and require review of the compatibility and migration evidence before integration.
- 2026-11-28: Implemented and reviewed the opt-in storage, lookup and mutation contract. CSV definitions and public shares reject Relation configuration. Require owner approval of the migration and compatibility evidence and CI before integration.

- 2026-11-28: The owner approved merging [PR #436](https://github.com/quinguyen1502/superstep/pull/436) into develop. Reviewed head `173fc29a` passed 25 CI checks, with publish and deploy jobs skipped. Require CI on the final state-only head before integration.
