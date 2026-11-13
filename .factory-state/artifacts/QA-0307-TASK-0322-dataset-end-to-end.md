# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0307
- Task ID: TASK-0322
- QA Owner: Grok
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Pass

## Acceptance Criteria Coverage

- `tests/test_dataset_acceptance.py` passed on SQLite: CSV import, lookup, upsert, denied CSV download, stale schema, and a snapshot that survived a second setup.
- `tests/test_dataset_csv.py` passed on the restacked export tip.
- Pull request #378 ran PostgreSQL 17 pytest, the strict English and Vietnamese handbook builds, Playwright, and `verify`.
- Desktop 1440×900 and narrow 390×844 Studio screenshots were captured for the grid and the CSV preview in both languages.

## Checks Performed

- Local SQLite acceptance and CSV tests.
- `factory validate --only hygiene` after the screenshot labels moved into the locale fixtures.
- CI on PR #378, including `Strict build (en, vi)`, `Backend (pytest on Postgres 17 + Redis 7)`, and `verify`.

## References

- [Task](../tasks/done/TASK-0322-dataset-end-to-end.md)
- [Review](REV-0307-TASK-0322-dataset-end-to-end.md)
