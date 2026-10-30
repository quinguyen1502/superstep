# Task

## Metadata

- Project: superstep
- Task ID: TASK-0190
- Status: doing
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0077, REQ-0078, REQ-0079, REQ-0081 (TASK-0174 to TASK-0189)
- Design IDs: none
- Architecture IDs: DEC-0069, DEC-0073, DEC-0075

## Objective

Version 0.10.0. The owner asked in chat to finish the remaining tasks and then release ("Code luôn các task còn lại
xong rồi mới lên 0.10.0"), and later added AI review of approvals (REQ-0081) to this release. It follows the 0.9.0
release (TASK-0139):
- bump `backend/pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json`,
  `sdk/python/src/superstep/_version.py` and the `scripts/install.sh` pin (`superstep[cli]==0.10.0`) to 0.10.0;
- rename `## Unreleased` in CHANGELOG.md to `## 0.10.0 (2026-10-31)`;
- fix what the full e2e run on develop found before the release;
- then open a release PR from develop to main, tag v0.10.0 and publish a GitHub Release.

## Contents Of 0.10.0

- Chat attachments (REQ-0077): TASK-0174 to TASK-0177 (#222 to #225).
- Agent hand-offs and the Help desk template (REQ-0078): TASK-0178 to TASK-0184 (#228, #230, #233 to #237).
- The `sstep` alias for the CLI (TASK-0185, #226).
- AI review of approvals (REQ-0081): TASK-0186 to TASK-0189 (#232, #238 to #240).
- SQLite restore and upgrade rollback fixes (REQ-0079).
- Release checks (this task): the run trace keeps one row per waiting tool slot after a resume; stale e2e specs.
- Public API: new routes `GET/PUT /api/approvals/auto` and `GET/PUT /api/approvals/auto/workflows[/{id}]` for the
  studio, and new optional workflow fields (`handoffs`, `max_handoffs`, `approval.auto`). The run API the SDKs wrap
  (`/api/workflows/{id}/runs`, `/api/runs/{id}`) is unchanged, so the SDKs stay 0.1.0 (`sdk-py-v0.1.0`,
  `sdk-ts-v0.1.0`). The `superstep` Python package (CLI) is published at 0.10.0 by the `v0.10.0` tag.

## Acceptance Criteria

- The version files and the install pin say 0.10.0, and the CHANGELOG has `## 0.10.0 (2026-10-31)` with an empty
  `## Unreleased` above it.
- The full e2e suite and `factory verify run --profile full` pass on the branch.
- The roadmap lists TASK-0190 under Releases.
- `factory validate` passes, and CI on the bump PR is green.

## Validation

- `factory verify run --profile full`, `npx playwright test` (full suite), `factory validate`.
- CI on the bump PR and on the release PR; the Image and Publish SDKs workflows on the tag.

## Review And QA

- Review: `.factory-state/artifacts/REV-0174-task-0190.md`. QA: `.factory-state/artifacts/QA-0174-task-0190.md`.

## Activity Log

- 2026-10-31: full verify on develop 59836bb2 passed; the full e2e run failed 6 tests (4 stale specs, 1 trace bug).
  Fixed here; version bump and CHANGELOG heading.
