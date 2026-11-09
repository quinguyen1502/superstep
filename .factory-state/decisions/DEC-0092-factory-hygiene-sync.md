# Decision

- Decision ID: DEC-0092
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0093
- Created/Updated: 2026-11-09
- Related: REQ-0093, TASK-0281

## Decision

Vendor the new framework into `.factory/` in copy mode, without changing `.github/workflows/factory-verify.yml`. The upstream template now runs `factory validate --only hygiene` before `factory deps apply`, and adds an optional `factory-pr-text.yml` workflow. Superstep adopts both only after the existing hygiene debt is cleaned, so that the sync does not turn CI red.

`.factory-state/hygiene.yaml` lists the owner's name under `allowed_terms`, because artifact metadata records it verbatim. It does not list product paths as i18n surfaces or skip paths; leftover Vietnamese in source, tests, and docs is debt to fix, not an exception.

## Alternatives considered

- Enable the hygiene step in CI in the same PR: rejected for now. About 1,200 Vietnamese lines in 357 files and 335 artifact references in 24 product files would have to be fixed first, which is a much larger change than a framework sync.
- Mark e2e tests or engine label maps as i18n paths to make the check pass: rejected; that would hide the debt the owner asked to remove.
