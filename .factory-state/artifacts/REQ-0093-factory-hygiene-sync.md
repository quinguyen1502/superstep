# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0093
- Status: Owner-authorised 2026-11-09 (pt259u: no Vietnamese in code, PRs, or related docs except i18n; pt261u: implement the rules upstream in sw-ai-factory; pt262u: merge the upstream PR and sync the new framework into Superstep)
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-09
- Related: DEC-0092, TASK-0281

## Summary And Scope

1. Update the vendored framework in `.factory/` to `quinguyen1502/sw-ai-factory` `main` at merge commit `cd2e3f5` (PR #31, repository hygiene checks), the same copy-mode way earlier framework updates were done.
2. Add `.factory-state/hygiene.yaml` with legitimate exceptions only (the owner's name in artifact metadata).
3. Do not change Superstep product code or CI enforcement in this task. Record the remaining hygiene debt so it can be cleaned in follow-up tasks.

## Acceptance Criteria

- Files under `.factory/` are byte-identical to the upstream commit for every file Superstep already vendors, plus the new `cli/factory_cli/hygiene.py` and `templates/ci/factory-pr-text.yml`.
- `factory validate --only hygiene` runs and reports the existing debt; no product file is changed.
- Superstep CI stays green (the project workflow does not yet run the hygiene step).
- factory deps apply / verify full; REV/QA; CI green including E2E before merge.
