# Task

## Metadata

- Project: superstep
- Task ID: TASK-0373
- Title: Prepare version 0.14.0
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-28
- Priority: P1
- Size: S

## Objective

Prepare a reviewed Superstep 0.14.0 release candidate from integrated develop at 764fc1d9.

## Dependencies

- Dataset Connected OpenAPI, SDK clients, live updates and read-only sharing have landed through PR #432.
- Dataset Formula remains an opt-in Studio preview while its runtime and export parity work continues. Relation remains planned.
- Merge to develop, promotion to main, and artifact publication require explicit owner approval and passing checks.

## Acceptance Criteria

- Align server, frontend, Python SDK, CLI, and installer at 0.14.0.
- Prepare TypeScript SDK 0.4.0 for Dataset clients and React toolkit 0.1.5 for peer compatibility with the new SDK while retaining its previous supported SDK series.
- Describe integrated features and migrations 0072–0074 in the changelog. Keep end-user documentation independent of the release-candidate wording.
- Validate synchronized package metadata, the tag-triggered publisher configuration, and local release artifacts. Confirm candidate tags and versions are unused.

## Validation Plan

Run the Python SDK and installer tests, Python distribution build, TypeScript generation check, typecheck, tests and package smoke, workspace install, frontend build, React tests and pack dry run, deployment metadata and Factory hygiene checks. Verify migration from 0071 on a disposable database, and require full integrated CI before release.

## Related Artifacts

- [Previous release](../done/TASK-0360-release-0-13-0.md)
- [Dataset integrations and live sharing](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)
- [Dataset Formula and Relation](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md)

## Publication Handoff

After approval and checked integration into develop, prepare a checked promotion to main with the final changelog date. Verify that the promotion includes the reviewed candidate and only intended release content. With publication approval, push immutable tags `v0.14.0`, `sdk-ts-v0.4.0`, and `sdk-react-v0.1.5` from the exact main release commit. Publish the TypeScript SDK before the React toolkit. Verify PyPI, npm and GHCR outputs before publishing the GitHub release notes. React Native keeps its independent release cycle.

## Activity Log

- 2026-11-22: The owner requested preparation of 0.14.0. The candidate covers the integrated Dataset changes since v0.13.0.

- 2026-11-22: Candidate prepared. Local package, documentation and migration checks passed. See [REV-0362](../../artifacts/REV-0362-TASK-0373-release-0-14-0.md) and [QA-0362](../../artifacts/QA-0362-TASK-0373-release-0-14-0.md). Awaiting integration CI and owner review.

- 2026-11-22: The owner approved merging [PR #433](https://github.com/quinguyen1502/superstep/pull/433) into develop. All 25 test and verification checks passed on reviewed head `4380c98d`. GHCR publication and handbook deployment were skipped for the pull request. The final state-only head must also pass CI before merge.

- 2026-11-28: Final CI confirmed all 25 checks passed on the integrated candidate, and PR #433 landed in develop at `5c97622b`. The owner approved merging [PR #434](https://github.com/quinguyen1502/superstep/pull/434) into main and publishing 0.14.0 with the TypeScript SDK and React toolkit. Publication remains gated by the final promotion CI and verified registry artifacts.
