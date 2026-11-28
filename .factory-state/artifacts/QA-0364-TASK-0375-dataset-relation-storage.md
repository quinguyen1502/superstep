# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0364
- Task ID: TASK-0375
- QA Owner: Codex
- Created: 2026-11-28
- Updated: 2026-11-28
- Outcome: local acceptance and reviewed-head CI passed

## Acceptance Coverage

- Migration `0075_dataset_relations` upgrades existing SQLite and PostgreSQL 17 fixtures, preserves their prior rows, adds the named edge keys and blocks downgrade while active definitions exist. After removing the definitions and edges, downgrade preserves legacy rows.
- The Relation API checks Dataset scope, visibility, the display column and source revisions. Error payloads for unknown, private and cross-scope targets match. Member revocation and role downgrade are covered at the transaction boundary.
- Link changes update row and data revisions together. Concurrent link and target deletion preserve referential integrity whichever wins. Batch rollback, source deletion, archive, and account and team cleanup are covered.
- Dataset bearer tokens cannot use the label picker or modify links. An authorized Connected deletion of a referenced row returns the generic conflict code. Public configuration rejects Relation fields. Authenticated CSV returns IDs and rejects creation of Relation columns.
- Studio renders the preview field as read-only using existing grid and schema components. Formula and general Dataset compatibility, both locale catalogs, API envelope, public spec parity and SDKs are checked.

## Local Performance

Synthetic Datasets contained 10,000 or 25,000 rows each. Measurements use 30 warmed repository calls per case without concurrent load. Link time includes lock acquisition and commit. Picker time covers a search matching every synthetic label. These results record local behavior on SQLite and Docker PostgreSQL 17.

| Engine | Rows per Dataset | Link p95 | First 50 picker results p95 | 50 requested labels p95 | 50 grid rows p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SQLite | 10,000 | 4.37 ms | 37.09 ms | 1.95 ms | 2.08 ms |
| SQLite | 25,000 | 4.71 ms | 93.96 ms | 1.96 ms | 1.93 ms |
| PostgreSQL 17 | 10,000 | 17.05 ms | 14.16 ms | 10.43 ms | 7.31 ms |
| PostgreSQL 17 | 25,000 | 20.97 ms | 30.29 ms | 18.40 ms | 6.26 ms |

## Results

- The final focused backend run passed 64 tests using SQLite, PostgreSQL 17 and Redis 7. It covered the Relation, CSV, live Dataset, API envelope, public spec and backend-layer suites.
- Playwright seeded a Relation through the authenticated API, verified Rows and Schema in light and dark mode, and checked that double-click left the linked value read-only. Four screenshots were captured from the disposable preview. The diff uses the existing Select and icon components, locale strings and theme styles. There are no new destructive UI actions or controls.
- Frontend and SDK build and lint passed. The JavaScript workspaces passed 330 tests, including locales and error parity. TypeScript SDK generation and typecheck passed.
- Python SDK passed 265 tests on Python 3.12. Ten environment-dependent integration cases were skipped locally.
- Both handbook languages built in strict mode. Image coverage, public OpenAPI drift and Factory hygiene passed.

- Broad backend regression passed 447 tests. The two Redis cases skipped in that run passed in the final focused run.
- [PR #436](https://github.com/quinguyen1502/superstep/pull/436/checks) passed 25 CI checks on reviewed head `173fc29a`. Publish and deploy jobs were skipped.

## Gaps And Follow-Up

- Local search timings use synthetic text and no competing clients. Recheck picker responsiveness with real search terms and longer labels during Studio acceptance.
- Keep Relation authoring off during migration rollout. Before enabling preview, take a restorable pre-enable database backup. Before downgrade, freeze Relation writes and remove active definitions or restore the pre-enable backup. Verify the previous server can read and write a representative pre-existing Dataset after rollback.
- UI editing, Connected Relation bindings and standalone exports remain in the approved plan.

## QA Decision

Local acceptance and reviewed-head CI passed. The owner approved integration pending CI on the final head.
