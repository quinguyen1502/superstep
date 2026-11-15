# Task

## Metadata

- Project: superstep
- Task ID: TASK-0281
- Title: Sync vendored factory to sw-ai-factory cd2e3f5 (repository hygiene checks)
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0093
- Architecture IDs: DEC-0092

## Objective

Update `.factory/` to the upstream framework that adds `factory validate` hygiene rules and `factory pr check`, add the project hygiene config, and record the remaining debt.

## Acceptance Criteria

- See REQ-0093.

## Upstream

- Repository: `quinguyen1502/sw-ai-factory`
- Commit: `cd2e3f5` (merge of PR #31, branch `factory/validate-hygiene`, head `d23c7d7`)
- Previous vendored commit: the parent `cd2e3f5^1` (vendored files were byte-identical to it)

## Remaining Hygiene Debt

Measured with `factory validate --only hygiene` after this sync, with the owner's name allowed:

- Artifact references in product files: 335 lines in 24 files (`.env.example`, `CHANGELOG.md`, README files, docs, CI workflows, and similar).
- Vietnamese outside i18n surfaces: 1,208 lines in 357 files. 669 lines are in 231 `.factory-state/` artifacts (mostly quoted owner instructions); the rest are in frontend e2e assertions, backend tests and engine label maps, `docs/ui-conventions.md`, promo scripts, SDK tests, React Native packages, and examples.

Enabling the hygiene step in `.github/workflows/factory-verify.yml` (and the optional PR text workflow) is a follow-up once this debt is cleaned.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0268-TASK-0281-factory-hygiene-sync.md`
- QA: `.factory-state/artifacts/QA-0268-TASK-0281-factory-hygiene-sync.md`

## Activity Log

- 2026-11-09: Vendored upstream `cd2e3f5`, added `hygiene.yaml`, recorded the debt.
- 2026-11-09: Owner approved the merge (pt262u); task moved to done on this PR.
