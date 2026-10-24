# Task

## Metadata

- Project: superstep
- Task ID: TASK-0106
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0062
- Design IDs: none
- Architecture IDs: none
- Pull request: [#124](https://github.com/quinguyen1502/superstep/pull/124) `fix/v050-polish`
- Merge commit: `4dd2d8532c8913f5f06e5540adfa2e5c8790dc49` (2026-10-24)

## Objective

v0.5.0 polish: top bar, demo errors, rate-limit test, README captions.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- Editor top bar: info badges hide whole via container queries instead of half-clipping (demo viewer, vi, 1440px); new alignment e2e for admin+viewer in en/vi.
- Demo node errors: no `AppError: ` prefix.
- Unit test for STUDIO_DEMO_RUN_RATE_LIMIT.
- Demo docs: visitor chat, shared history/chats documented as a known limit.
- README feature-row captions no longer clipped.
- CHANGELOG 0.5.0 updated.

## Changed files

- 9 files: `CHANGELOG.md`, `README.md`, `README.vi.md`, `backend/app/engine/limits.py`, `backend/tests/test_demo_mode.py`, `docs/deploy/demo.md`, `docs/deploy/demo.vi.md`, `frontend/e2e/alignment.spec.ts`, `frontend/src/components/editor/editor-header.tsx`.

## Activity Log

- 2026-10-24: merged into develop (4dd2d85).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0098, QA QA-0098 (retroactive records).
