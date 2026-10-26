# Task

## Metadata

- Project: superstep
- Task ID: TASK-0129
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0066 (clean `factory validate`)
- Design IDs: none
- Architecture IDs: DEC-0064 (supersedes DEC-0060 point 1)

## Objective

Clear the factory records debt left after 0.8.0 and the framework update in #162 (owner request in chat on
2026-10-26: "Mục 1").

## Scope

- Review and QA records for TASK-0125, TASK-0126 and TASK-0127 (REV/QA-0113 to 0115), written after the merge. TASK-0128
  gets a "Review And QA" section, as the 0.7.0 release task (TASK-0124) has.
- Requirement statuses: requirements whose tasks are done are marked Done.
- `roadmap.md`: the Agent node section is brought up to date. Sections are added for REQ-0069 to REQ-0071, the owner
  requests, and the 0.7.0 and 0.8.0 releases.
- DEC-0064: the verify workflow is maintained by hand, `.factory-state/configuration/` is removed, and the
  verification commands live in `tool-policy.yaml`.
- `factory verify run --profile full` records the commands into the policy and refreshes `verification/latest.yaml`.

## Out Of Scope

- Source code changes.
- Listing TASK-0087 to TASK-0112 in the roadmap one by one (their task files and CHANGELOG.md have them).
- Deleting `.factory-state/verification/runs/` (DEC-0064 point 4).

## Acceptance Criteria

- `factory validate` reports no missing review or QA reference for a done task.
- No requirement whose tasks are all done is still "In review" or "Accepted".
- `roadmap.md` lists TASK-0113 to TASK-0128 with their PRs.
- `tool-policy.yaml` lists the verification commands; `factory verify validate` passes without the legacy-evidence
  warning.

## Validation

- `factory validate`, `factory verify validate`, `factory ids check --all-refs`, `factory skills validate`.

## Changes

- REV-0113 / QA-0113 (TASK-0125), REV-0114 / QA-0114 (TASK-0126), REV-0115 / QA-0115 (TASK-0127), written after the merge
  from the merged diffs, the task records and CI; no blocking finding. A "Review And QA" section in each of
  TASK-0125 to TASK-0128.
- Requirement statuses set to Done: REQ-0049 to REQ-0055, REQ-0065 to REQ-0068, REQ-0070 to REQ-0072.
- `roadmap.md`: the Agent node tasks are merged and TASK-0125 is added. New sections: Comparison pages, Workflows as
  MCP tools, Runs across restarts, Owner requests, Releases.
- DEC-0064, and DEC-0060 marked superseded (its point 2 still holds). `.factory-state/configuration/` removed.
- `tool-policy.yaml` lists the 8 verification commands, recorded by `verify run` from the manifests. `tooling/generated.yaml`
  is refreshed by `factory tools apply` (the policy hash). `verification/latest.yaml` is in the new format.

## Findings

- **The backend suite is close to the verify timeout.** `factory verify` stops a command after 300 seconds (a constant in
  the framework, not configurable). The backend suite took 205 s in CI (develop, run 40300256421) and 346 s on this
  machine, so the local `factory verify run --profile full` failed on `backend-test` with a timeout. The evidence here
  comes from the same plan run through the framework's Python API with `timeout_seconds=1200`. All 8 checks passed.
- **Two small framework issues, not fixed here:**
  - `deps validate` counts `sdk/typescript/dist/cjs/package.json`, a build output, as a manifest. It then warns
    "dependency manifests or lockfiles changed after installation" after any local SDK build. A clean checkout does not
    have the file.
  - `deps apply` still records absolute executable paths in `dependencies/installed.yaml`. The local re-install was
    therefore not committed.

## Validation Results

- `factory deps apply --allow-network`: installed (local only).
- Verification (`verify run` plan, timeout 1200 s): backend-test 345.6 s, frontend build, lint and test,
  sdk-python test, sdk-typescript build, test and typecheck: all passed.
- `factory validate`: passed. Warnings: the local `dist/` manifest above, and no todo task.
- `factory verify validate`: passed, with no legacy-evidence warning. `factory tools validate`, `factory skills validate` (70),
  `factory ids check --all-refs`: passed.
