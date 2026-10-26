# Task

## Metadata

- Project: superstep
- Task ID: TASK-0128
- Status: doing
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0047, REQ-0072 (TASK-0125), REQ-0007, REQ-0015 (TASK-0126), REQ-0071 (TASK-0127)
- Design IDs: none
- Architecture IDs: DEC-0051, DEC-0062, DEC-0063

## Objective

Version 0.8.0 (owner request in chat, 2026-10-26: "Merge và bump version đi"), the same way as 0.7.0 (TASK-0124):
- bump `backend/pyproject.toml`, `frontend/package.json` and `frontend/package-lock.json` to 0.8.0;
- turn `## Unreleased` in CHANGELOG.md into `## 0.8.0 (2026-10-26)`;
- then a release PR develop -> main, the tag v0.8.0 and a GitHub Release.

## Contents Of 0.8.0

- Agent nodes in the TypeScript export (#158).
- Templates say what they still need, "Hàm" label, "1 error to fix" (#160).
- An answer accepted just before a restart is not lost (#163, migration 0039).
- SDKs and the public API contract are unchanged: no SDK release.

## Validation

- CI on each merged PR: #158, #160 and #163 had 15 passed, 2 skipped.
- Full e2e on develop: see below.
