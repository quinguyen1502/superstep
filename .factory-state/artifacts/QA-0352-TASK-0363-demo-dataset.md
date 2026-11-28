# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0352
- Task ID: TASK-0363
- QA Owner: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Pass

## Validation Scope

Local demo-style startup with a fresh SQLite database, API regression coverage, and browser verification with the existing Studio frontend.

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| One sample with 125 synthetic rows, no duplicate or replacement on restart, no sample in regular mode | `test_demo_dataset_is_readable_but_immutable_for_old_and_new_visitors` compares the first page including row IDs before and after reseeding and checks non-demo startup | Pass |
| Active owner after upgrade from developer defaults | `test_demo_boot_uses_active_admin_after_development_account_is_disabled` checks seed ownership and deactivation of the development account | Pass |
| Existing and new visitors can read, filter, sort, page, group, summarize and export only visible rows | API regression covers the queries, an authorized 125-row CSV, and 404 for an unrelated private dataset. Chromium checked Try the demo, the support-ticket grid, search, grouping and an actual CSV download as Viewer | Pass |
| Visitor writes and workflow Dataset calls stay blocked, workflow samples stay available | API regression asserts `DEMO_READ_ONLY` and `DATASET_GRANT_DENIED`; existing demo tests check sample workflows and visitor privacy | Pass |
| English and Vietnamese demo docs | `docs/deploy/demo.md` and `docs/deploy/demo.vi.md` | Pass |

## Results And Gaps

- Backend demo, dataset, layers, envelope and PaaS regression suite: 147 passed, 127 skipped locally. PostgreSQL and Deno variants require the CI environment.
- Final focused demo dataset tests, including owner fallback and CSV assertions: 2 passed.
- Factory hygiene and Git diff whitespace checks passed.
- Hosted deployment is outside the validated scope. The local preview uses a disposable database and no existing application data.

## QA Outcome

Pass for integration review.
