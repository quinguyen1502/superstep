# Task

## Metadata

- Project: superstep
- Task ID: TASK-0139
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0073 (TASK-0133 to TASK-0138), REQ-0045 (TASK-0132), REQ-0048 (status fix)
- Design IDs: none
- Architecture IDs: DEC-0065, DEC-0066

## Objective

Version 0.9.0. The owner said "Làm tiếp đi" in chat on 2026-10-27, after the next-task recommendation to release 0.9.0.
It follows the 0.8.0 release (TASK-0128):
- bump `backend/pyproject.toml`, `frontend/package.json` and `frontend/package-lock.json` to 0.9.0;
- rename `## Unreleased` in CHANGELOG.md to `## 0.9.0 (2026-10-27)`;
- then open a release PR from develop to main, tag v0.9.0 and publish a GitHub Release. Each merge needs the owner's
  approval.

Also fixes a record: REQ-0048 phase 1 (TASK-0084, TASK-0085) was merged in #116 and #117, but its status still said
"in stacked draft PRs". Phase 2, the public chat page, became REQ-0074. The owner asked on 2026-10-27 to ship it in
this release ("Tôi muốn đưa vào chung release luôn"), so this PR waited for it.

## Contents Of 0.9.0

- Workflows as Agent tools (REQ-0073), PRs #177 to #182:
  - tool settings and checks (#177);
  - linked child runs, migration 0040 (#178);
  - approvals inside a child (#179);
  - editor card and nested trace (#180);
  - the Support team template and exports (#181);
  - handbook (#182).
- The public chat page (REQ-0074), PRs #186 to #191:
  - publish settings, the public API by slug, visitor identity and limits (#186);
  - the public socket, runs as the owner, the visitors list (#187);
  - the `/c/{slug}` page and its settings (#188);
  - frame protection for the studio, the iframe snippet and the `widget.js` bubble (#189);
  - handbook (#190);
  - the chat's logo, migration 0041 (#191).
- Run trace layout fixes (TASK-0146, #193).
- Workflow check messages in the UI language, `issues` codes (#174).
- Factory tooling: the per-command verify timeout (#170), framework fixes (#172) and the framework update (#162).
- The test fix for the Postgres and Redis CI job (#183).
- Public API: added the optional fields `parent_run_id` and `waiting.child_run_id`, and their types in both SDKs. The
  public chat routes (`/api/public/chat/...`, `WS /ws/public/chat/{slug}`) are new and are not in the SDKs.
  - The change is additive, so existing clients keep working.
  - SDK versions stay 0.1.0 (`sdk-py-v0.1.0`, `sdk-ts-v0.1.0`). The owner decides whether to make a separate SDK release.

## Acceptance Criteria

- The three version files say 0.9.0, and the CHANGELOG has `## 0.9.0 (2026-10-27)` with an empty `## Unreleased` above
  it.
- REQ-0048's status names its merged PRs, and the roadmap lists TASK-0139 under Releases.
- `factory validate` passes, and CI on the bump PR is green.

## Validation

- `factory validate`.
- CI on the bump PR and on the release PR.

## Review And QA

- Review: the owner approved the release in chat ("Ok, merge #196 into main, tag v0.9.0 and publish the GitHub
  Release"). No separate REV artifact.
- QA: CI on #184 and #196, main CI after the merge, and the Image workflow on the tag. No separate QA artifact.

## Activity Log

- 2026-10-27: version bump and CHANGELOG heading; held as a draft while REQ-0074 was built.
- 2026-10-27: the owner approved merging #186 to #191 ("Merge chuỗi và chuẩn bị release 0.9.0"); develop merged into
  this branch, so 0.9.0 lists the public chat page, the logo and the trace fix. TASK-0140 to TASK-0146 moved to done.
- 2026-10-27: released with the owner's approval: #184 into develop, release PR #196 into main (585ed72), tag
  `v0.9.0` and the GitHub Release.
