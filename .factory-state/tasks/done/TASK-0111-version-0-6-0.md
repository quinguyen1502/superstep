# Task

## Metadata

- Project: superstep
- Task ID: TASK-0111
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-25
- Requirement IDs: REQ-0067, REQ-0050, REQ-0051, REQ-0052, REQ-0053, REQ-0054, REQ-0065, REQ-0066
- Design IDs: none
- Architecture IDs: none

## Objective

Version 0.6.0, the same way as 0.5.0 (TASK-0105, #123): bump `backend/pyproject.toml`, `frontend/package.json` and
`frontend/package-lock.json` to 0.6.0 and turn `## Unreleased` in CHANGELOG.md into `## 0.6.0 (2026-10-24)`.

## Contents Of 0.6.0

- LangGraph project export (#128), Agent Server API subset at `/api/lg` (#129, migration 0036), LangSmith evals and
  trace links (#132, migration 0037), time travel / fork from a checkpoint (#133), handbook Superstep vs LangSmith
  (#134), backfilled factory records (#135), flaky-test fixes (#136), clean `factory validate` (#137).
- SDKs (`sdk/python`, `sdk/typescript`) unchanged since `sdk-py-v0.1.0` / `sdk-ts-v0.1.0`: no SDK release.

## Activity Log

- 2026-10-24: bumped, verified (QA-0103); PR into develop. After merge: full e2e and verify on develop, release PR develop -> main, tag v0.6.0, GitHub Release.
- 2026-10-25: PR #138 merged into develop (1dd9313); moved to done by TASK-0112.

## Handoff Notes

- Review REV-0103, QA-0103.
