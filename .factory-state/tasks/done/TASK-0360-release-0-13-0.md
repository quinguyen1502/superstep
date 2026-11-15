# Task

## Metadata

- Project: superstep
- Task ID: TASK-0360
- Title: Prepare version 0.13.0
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-15
- Updated: 2026-11-15
- Priority: P1
- Size: S

## Objective

Prepare the 0.13.0 release candidate following owner feedback on Dataset, with synchronized package metadata and upgrade notes.

## Dependencies

- The release-only commit is based on develop after Dataset polish PR #417 merged at 424aff7b.
- Integration, tag pushes, GitHub Release publication, and registry publication require explicit owner approval and successful CI.

## Acceptance Criteria

- Server, frontend, Python SDK, CLI, and installer agree on 0.13.0.
- Prepare the independently versioned React toolkit 0.1.4 and TypeScript SDK 0.3.0. The latter introduces workflow schedule methods. React continues to accept the 0.2 SDK series and adds compatibility with 0.3.
- Changelog covers Dataset, schedules, observability, and migrations 0059 through 0071. Existing packages, tags, and deploys are preserved while this candidate is under review.
- Verify candidate names against existing Git tags and public registries. Check frontend and SDK artifacts locally and open a stacked draft PR.

## Validation Plan

Run the Python release tests, TypeScript generated types, SDK tests and package smoke tests, React lint, tests and pack dry run, lockfile installation, and Factory hygiene. Full CI is required on the integrated source before release.

## Related Artifacts

- [Dataset UI polish PR](https://github.com/quinguyen1502/superstep/pull/417)
- [Previous release](../done/TASK-0276-release-version-0-12-0.md)

## Publication Handoff

After explicit approval, integrate the checked Dataset and release PRs into develop, then merge the reviewed release candidate to main. Verify the main release commit and the aligned package versions. At publication time, create and push the immutable release tags from that commit. Publish the TypeScript SDK tag before verifying the public React peer combinations. Verify PyPI, npm and GHCR artifacts before publishing release notes. Keep the separately versioned React Native package outside this candidate.

## Activity Log

- 2026-11-15: Prepared the candidate and verified local packaging, the bilingual handbook and SQLite migration. See [REV-0351](../../artifacts/REV-0351-TASK-0360-release-0-13-0.md) and [QA-0351](../../artifacts/QA-0351-TASK-0360-release-0-13-0.md).

- 2026-11-15: Owner approved merging PR #418 into develop after the integrated candidate passes CI. Publication remains a separate approval.

- 2026-11-15: The first integrated CI run exposed a fractional-second Usage bucket regression in PostgreSQL. Fixed bucket calculation and added deterministic coverage for both database dialects on the same PR. Merge remains gated on CI for the updated commit.
