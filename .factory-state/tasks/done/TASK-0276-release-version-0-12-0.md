# Task

## Metadata

- Project: superstep
- Task ID: TASK-0276
- Title: Release version 0.12.0
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: owner-authorised 0.12.0 release
- Architecture IDs: DEC-0033

## Objective

Publish the owner-authorised 0.12.0 release from integrated develop, using the checked develop, main, tag and registry process.

## Owner Approval

The owner instructed “ok, release đi” on 2026-11-07 after PR #336 merged. This authorises the release metadata, the checked develop and main merges, immutable tags, a GitHub Release, and the configured PyPI, npm and GHCR publication. It does not authorise a React Native package, cross-language code nodes, or a live provider or bot cutover.

## Acceptance Criteria

- Shared server, frontend, Python SDK, CLI and installer metadata agree on 0.12.0. The React toolkit, its frontend pin and the lock agree on 0.1.3. The TypeScript SDK stays 0.2.0 and its tag is not republished.
- The changelog replaces the stale Unreleased browser notes with the work integrated since v0.11.2, including migrations 0055 through 0058 and the browser feature flags.
- Release metadata only. No runtime, workflow or dependency selection changes.
- Existing tags stay immutable. v0.12.0 and sdk-react-v0.1.3 point at the checked main commit.
- GitHub Release stays Draft until PyPI superstep 0.12.0, npm @superstep/react 0.1.3 and the configured GHCR images are verified.

## Validation Plan

- `factory validate`
- `cd sdk/python && .venv/bin/python -m pytest tests/test_release.py -q`
- Version pins agree. `git diff --check`

## Activity Log

- 2026-11-07: Allocated TASK-0276, REV-0262 and QA-0262 after fetch. Develop is ca278c23, which includes PR #336.
- 2026-11-07: `factory ready` passed before the version edits. Review REV-0262 and QA QA-0262 record the metadata handoff. Owner approval is the release instruction. Publication is not claimed from this commit.

## Handoff Notes

- Do not claim publication from the source commit alone.
