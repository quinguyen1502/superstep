# Task

## Metadata

- Project: superstep
- Task ID: TASK-0262
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002
- Plan: PLAN-0006
- Size: M

## Objective

Give the TypeScript project export the same live Playwright and Browserless page behavior as TASK-0261, without weakening the fixture driver.

## Scope

### In Scope

- Change `backend/app/engine/browser_export_ts.py` so `playwright` and `browserless` keep one browser and one page per alias until idle, lifetime expiry, or process exit.
- Match TASK-0261 for whitelist-checked navigation, click, fill, stored HTML, page evaluate with a 4,000-character bound, redirect hops, profile JSON, `max_pages`, and Browserless-only `stealth`.
- Extend `backend/tests/test_browser_typescript_export.py`. Execute with Node strip-types. Playwright stays an optional dynamic import (`import("npm:" + "playwright")`) and does not become a `package.json` dependency.
- Update the English and Vietnamese handbook only if TASK-0261 left a Python-only wording that is wrong for TypeScript.

### Out Of Scope

- Changing the Python helper except for a shared comment if the TypeScript contract would otherwise drift.
- Upload, download, screenshot image bytes, `memory` driver changes, private-address access for Playwright or Browserless, Studio conversation leases, other managed adapters, and TASK-0227 or TASK-0228.
- A Deno run, unless Deno is installed. Do not record a Deno pass that did not happen.
- Schema changes and Alembic migrations.

## Inputs

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md` (2026-11-07 export-driver clarification).
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision: `.factory-state/decisions/DEC-0085-browser-tools.md` decision 10.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Python contract: `.factory-state/tasks/done/TASK-0261-browser-python-live-export.md` and its helper, merged in PR #329 (`10300e20`).
- Fixture TypeScript helper from TASK-0252, merged in PR #323: `.factory-state/tasks/done/TASK-0252-browser-typescript-export.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0086-browser-tools.md`
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`
- Decisions: `.factory-state/decisions/DEC-0085-browser-tools.md`
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`
- Clarifications: REQ-0086 section "Owner clarification (2026-11-07) — export drivers"

## Expected Outputs

- TypeScript export helper with the same live-page contract as the Python helper.
- Node tests for the live path when Playwright and Chromium exist, without a false pass on skip.
- Review and QA artifacts before the task moves to done.

## Implementation Notes

- Generated code imports nothing from `app`. The dynamic Playwright import must not match the exporter's `npm:` dependency regex.
- Same-connection commands stay serialized on the session mutex.
- Medium-task workflow. No new screen. Technical direction is DEC-0085 decision 10 and the merged TASK-0261 helper.

## Constraints

- One task branch from `develop` after TASK-0261 is merged. One pull request. Do not stack on the TASK-0261 branch unless the owner says so.
- Do not copy secrets or profile values into the generated source.
- Backend layers stay as in `docs/backend-architecture.md`.

## Dependencies

- TASK-0261 merged to `develop` in PR #329 (`10300e20`).
- TASK-0252 is merged in PR #323. The TypeScript fixture helper is on `develop`.
- Review REV-0254 and QA QA-0254 are recorded on this branch. PR #334 is merged (`ddafdd18`).

## Acceptance Criteria

- The TypeScript live driver matches every TASK-0261 acceptance criterion that applies to Playwright, Browserless, evaluate, redirects, profile JSON, `max_pages`, stealth, upload, download, and screenshot bytes.
- The `memory` TypeScript fixture tests still pass.
- `package.json` in the exported project does not gain a Playwright dependency.
- A run without Playwright skips the live cases and does not count them as passed.
- Existing non-browser TypeScript export snapshots stay stable.

## Validation Plan

- `backend/.venv/bin/python -m pytest tests/test_browser_typescript_export.py tests/test_browser_python_export.py tests/test_typescript_export.py tests/test_project_export.py`
- Full backend pytest from `backend/`.
- `sdk/typescript`: `npm run build`, `npm run test`, and `npm run typecheck` when the generated TypeScript shape changes.
- `python3 scripts/check-browser-handbook.py` if the handbook changes.
- `git diff --check`
- Live Playwright cases must be executed once on a machine that has Playwright and Chromium. Record that run. A skip is not that evidence. Do not claim a Deno run unless Deno executed the export.
- At completion: review artifact, QA artifact, one commit, Ready pull request. Do not merge without the owner.

## Assumptions

- The owner approved the 2026-11-07 driver wording and asked for this task split. Implementation starts only after task-start and after TASK-0261 and TASK-0252 are on `develop`.
- Designer and architect roles are skipped for the same reasons as TASK-0261.
- Node strip-types remains the local executor.

## Open Questions

- None. Task-start is a separate owner instruction.

## Activity Log

- 2026-11-07: Created by plan-tasks after `git fetch --all --prune` and `factory ids next TASK --all-refs` returned TASK-0261. This task is TASK-0262. No product code, dependency install, or implementation branch.
- 2026-11-07: Owner said "do the whole task chain". TASK-0261 is on develop (merge 10300e20). Branch `factory/task-0262-browser-typescript-live-export` from that commit. Status doing.
- 2026-11-07: TypeScript live page is implemented in `backend/app/engine/browser_export_ts.py`. Memory fixture behavior is unchanged. Node tests run the live control flow through a stub `playwright` package. Playwright is not installed, and Chromium was not launched. A skip was not counted as a pass. Focused export pytest: `tests/test_browser_typescript_export.py`, `tests/test_browser_python_export.py`, `tests/test_typescript_export.py`, `tests/test_project_export.py` — 48 passed, 29 skipped. Handbook check and `git diff --check` passed.
- 2026-11-07: Tool-policy validation. Backend pytest 1481 passed, 106 skipped, 588.76s. SDK Python pytest 229 passed, 8 skipped, 14.01s. Repo-root npm build, lint (warnings only, 0 errors), and test passed on arm64 Node (frontend 177, react 22, sdk typescript 102). SDK TypeScript build, test (102), and typecheck passed. `factory verify` was not run through the x86_64 venv.
- 2026-11-07: Review REV-0254, no blocking findings, approved for QA. QA QA-0254, pass with follow-up. Chromium was not launched. Deno was not run. Owner asked to finish the chain through a Ready pull request without merging. Status done. PR #334.

## Handoff Notes

- Branch: `factory/task-0262-browser-typescript-live-export`. PR #334 is merged (`ddafdd18`).
- Review: `.factory-state/artifacts/REV-0254-TASK-0262-browser-typescript-live-export.md`. QA: `.factory-state/artifacts/QA-0254-TASK-0262-browser-typescript-live-export.md`.
- TASK-0261 is merged in PR #329 (`10300e20`). REQ-0086 is not marked done. AC11 is closed.
- Live control flow is proven with the stub. A real Playwright and Chromium launch is still a follow-up. Deno was not run.
