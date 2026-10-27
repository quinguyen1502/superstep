# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0067
- Status: Done (TASK-0111, PR #138)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner decision in chat, 2026-10-24 (step 4 of the v0.6.0 plan).

## Summary

- Release 0.6.0 from develop to main as 0.5.0 was released.

## Acceptance Criteria

- Versions and CHANGELOG at 0.6.0; full e2e and `factory verify run --profile full` pass on develop.
- Release PR into main merged with CI green; annotated tag `v0.6.0` on the merge commit; GitHub Release with the changelog.
- Images `0.6.0`, `0.6` and `latest` published to GHCR for superstep and superstep-sandbox and pullable anonymously.
- The Render demo runs the new code.
