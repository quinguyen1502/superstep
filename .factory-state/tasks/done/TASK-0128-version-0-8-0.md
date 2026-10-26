# Task

## Metadata

- Project: superstep
- Task ID: TASK-0128
- Status: done
- 2026-10-26: released with the owner's approval ("Merge và bump version đi"):
  - #164 (TASK-0127 to done) merged into develop (aee59a2);
  - #165 (version bump) merged into develop (05ea1c2);
  - #166 (release, develop -> main) merged (f3834ce), with CI 31 passed and 2 skipped;
  - tag `v0.8.0` on f3834ce, and the GitHub Release "Superstep v0.8.0".
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
- Full e2e on develop at 0ff009c: 95 passed, 11 skipped, 1 failed.
  - The failure: `notifications-deliveries.spec.ts`, "webhook deliveries ... secret rotation". The delivery list was
    still empty after 20 s, so the run's callback had not been queued yet.
  - Re-runs:
    - develop, the file 3 times: 1 failure in 9 tests;
    - then the test 6 times, and the file 4 and 10 times: 48 out of 48 passed;
    - v0.7.0, the same commands: 48 out of 48 passed.
  - Each run uses a fresh database, and 0.8.0 changes nothing in webhook deliveries. Treated as a timing flake under
    load; the cause is not found. Worth watching: if it fails again, look at how long the API run takes to settle.

## Review And QA

- Review: the owner approved the release in chat ("Merge và bump version đi"). No separate REV artifact.
- QA: the CI results above, and the Image workflow on the tag. No separate QA artifact.
- Added by TASK-0129 on 2026-10-26: `factory validate` reported the task without these references.
