# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0064
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Related Requirements: REQ-0066
- Related Architecture: none
- Related Tasks: TASK-0129 (PR #162 brought in the framework change)
- Supersedes: DEC-0060 point 1

## Context

The vendored factory framework (sw-ai-factory f9526b7, merged in #162) removed `factory stack`. It no longer
generates `.github/workflows/factory-verify.yml` or checks it against a stored hash. It ships a static example at
`.factory/templates/ci/factory-verify.yml` instead. `factory verify` now reads its commands from
`.factory-state/tooling/tool-policy.yaml`.

## Decision

1. `.github/workflows/factory-verify.yml` is maintained by hand in this repository. It stays as `factory stack apply`
   last wrote it. The framework template is a reference only. DEC-0060 point 2 still holds: the workflow runs on pull
   requests and on pushes to `develop`, not on pushes to `main`.
2. `.factory-state/configuration/` is removed. Nothing reads it any more.
3. The verification commands are listed in `tool-policy.yaml` and committed. `factory verify` runs exactly those, in
   CI and locally. A new package or check is added to the policy by hand.
4. `.factory-state/verification/runs/` stays as history (QA-0104 cites one of its files). The CLI no longer writes
   there. `factory gc --apply` would delete it, so run gc with that in mind.

## Consequences

- A change to the workflow is an ordinary reviewed edit; there is no drift check against a generated copy.
- CI and local runs use one command list. Discovery from manifests no longer adds a check silently.
- `verification/latest.yaml` holds only the commands and their results, so re-running the same checks does not change
  the file.
