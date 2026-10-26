# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0060
- Status: Superseded by DEC-0064 (2026-10-26); point 2 still holds
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-26
- Related Requirements: REQ-0066
- Related Architecture: none
- Related Tasks: TASK-0110

## Decision

1. `.github/workflows/factory-verify.yml` is the generated file again (`factory stack apply`), so `factory stack validate` and `factory validate` report no drift.
2. The hand edit made in #114 (also running on pushes to `main`) is dropped: every change reaches `main` through a release PR, and `pull_request` runs the verification on that PR; pushes to `develop` still run it.

## Consequences

- One fewer verification run per release (the post-merge push to `main`); the release PR's run is the gate.
- Future changes to the workflow go through the stack configurator, not by hand.
