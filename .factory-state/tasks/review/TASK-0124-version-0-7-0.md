# Task

## Metadata

- Project: superstep
- Task ID: TASK-0124
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0069, REQ-0070, REQ-0071 (and the Agent node requirements of TASK-0116 to TASK-0120)
- Design IDs: none
- Architecture IDs: DEC-0061, DEC-0062, DEC-0063

## Objective

Version 0.7.0 (owner request in chat, 2026-10-26), the same way as 0.6.0 (TASK-0111):
- bump `backend/pyproject.toml`, `frontend/package.json` and `frontend/package-lock.json` to 0.7.0;
- turn `## Unreleased` in CHANGELOG.md into `## 0.7.0 (2026-10-26)`;
- then a release PR develop -> main, the tag v0.7.0 and a GitHub Release.

## Contents Of 0.7.0

- Handbook comparison pages: visual builders, agent frameworks (#141).
- Workflows as MCP tools at `/mcp` (#142, migration 0038).
- Runs survive a restart without Redis (#143).
- Agent node:
  - engine loop (#144);
  - tool approval (#146);
  - editor and trace (#145);
  - tests, template and export (#147);
  - handbook (#148).
- Phone layout and node Config tabs (#150).
- Intro video (#152).
- Fixes for time travel after a Condition, and for restart recovery counting resumes (#153).
- SDKs (`sdk/python`, `sdk/typescript`) and the public API contract are unchanged since `sdk-py-v0.1.0` and
  `sdk-ts-v0.1.0`: no SDK release.

## Validation

- CI on develop at 405b54f (PR #153): 15 passed, 2 skipped. This covers:
  - backend on SQLite and Postgres + Redis;
  - the frontend build on Node 20 and 22;
  - the SDKs, including against a live backend;
  - the image and compose smoke tests;
  - the code sandbox images.
- The version bump changes no code, so the release PR's CI is the check.

- Full e2e on develop at 89b0d42: 95 passed, 11 skipped, 1 failed.
  - The failure: `alignment.spec.ts`, dark-en, rename dialog footer. It failed 3 times out of 3.
  - Cause: the check measured the buttons during the dialog's zoom-in, at a scale of about 0.96 (30.76 px instead
    of 32 px), so it is a timing problem in the test, not a layout regression.
  - Fix in #156: `settled()` in `e2e/helpers/alignment.ts` waits for the dialog's animations to end before
    measuring. After the fix: 24 passed out of 24 with `--repeat-each 3`.

## Review And QA

- Review: the owner approves the release in chat. No separate REV artifact.
- QA: the CI results above. No separate QA artifact.
