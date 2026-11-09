# Task

## Metadata

- Project: superstep
- Task ID: TASK-0282
- Title: Clean the repository hygiene debt and enforce the hygiene checks in CI
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0093
- Architecture IDs: DEC-0093

## Objective

Make `factory validate --only hygiene` pass honestly: no artifact references in product files and no Vietnamese outside locale catalogs, then run the hygiene and PR-text checks in CI. Stacked on TASK-0281 (#344); lands after it.

## Acceptance Criteria

- `factory validate --only hygiene` exits 0 with `hygiene.yaml` holding only the owner's name in `allowed_terms` (no `i18n_paths`, no `skip_paths`).
- Product behaviour is unchanged; Vietnamese UI and server copy only moved into locale catalogs, with en and vi kept in sync.
- Tests keep exact expectations and read Vietnamese from the catalogs.
- `.github/workflows/factory-verify.yml` runs `factory validate --only hygiene`; `.github/workflows/factory-pr-text.yml` runs `factory pr check`.

## Scope

- Artifact references removed from 24 product files (README files, CHANGELOG, docs, CI comments, `.env.example`, compose). The task renumbering table moved from `docs/` into DEC-0007.
- Backend catalogs `backend/app/locales/{en,vi}.json` and `app/engine/locale.py` helpers; engine and channel modules read them.
- Frontend e2e helper `e2e/catalog.ts` and fixture `e2e/fixtures/inputs.vi.json`; specs and unit tests use them.
- React Native package and example labels, promo captions and the vi glossary moved into locale files.
- SDK token vectors regenerated with a non-Vietnamese non-ASCII secret; SDK CLI tests read `Catalog.load("vi")`.
- `.factory-state/` artifacts and the three browser-tool preview mockups translated to English.

## Hygiene Counts

- Before (TASK-0281 head): 381 findings, 24 files with artifact references and 357 files with Vietnamese (255 of them under `.factory-state/`).
- After: 0.

## Validation

- `factory validate --only hygiene`: passed.
- Backend `pytest tests`: 1578 passed, 30 skipped; the files changed afterwards were rerun (107 passed, 3 skipped).
- SDK Python `pytest tests`: 233 passed, 9 skipped.
- Frontend `vitest run`: 39 files, 177 tests passed; `tsc -p tsconfig.app.json` clean; the e2e specs type-check.
- `@superstep/react` public test, `@superstep/react-native` Jest (12 tests) and the TypeScript SDK token vectors passed.
- Playwright e2e was not run locally; CI runs it.

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0093-hygiene-debt-cleanup.md`
- Previous task: `.factory-state/tasks/done/TASK-0281-factory-hygiene-sync.md`

## Activity Log

- 2026-11-09: Owner asked to clean up the debt (pt267u). Branch `factory/task-0282-hygiene-debt` from the TASK-0281 head `2aba4ec5`.
