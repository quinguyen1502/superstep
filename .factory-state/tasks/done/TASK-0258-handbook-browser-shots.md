# Task

## Metadata

- Project: superstep
- Task ID: TASK-0258
- Title: Replace handbook browser mockups with real Studio screenshots
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: S

## Objective

Replace the two AI-generated images that PR #317 stored as handbook screenshots with captures of the running Studio UI. Keep the existing English and Vietnamese guide paths.

## Scope

### In Scope

- `handbook/docs/en/images/browser-connection-settings.png` and the same filename under `handbook/docs/vi/images/`.
- `handbook/docs/en/images/browser-agent-url-binding.png` and the same filename under `handbook/docs/vi/images/`.
- The English UI only: Settings → MCP servers card "Demo isolated browser", and the Agent editor Data tab for a node labeled "Web researcher".

### Out Of Scope

- TASK-0251 and TASK-0252 stay deferred. No Python or TypeScript export work.
- Enabling the browser runtime, building worker or gateway images, or claiming a browser run completed.
- Rewriting the guide prose, changing routes, or merging.

## Inputs

- Handbook pages `handbook/docs/en/guide/browser.md` and `handbook/docs/vi/guide/browser.md`.
- Develop at `e1c4284d` (merge of PR #317).
- Dev account documented in `docs/deploy/README.md`: `admin@example.com` / `admin123`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0086-browser-tools.md`
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`
- Decisions: `.factory-state/decisions/DEC-0085-browser-tools.md`
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- Previous delivery: `.factory-state/tasks/done/TASK-0253-browser-e2e-handbook.md`
- Review: `.factory-state/artifacts/REV-0241-TASK-0258-handbook-browser-shots.md`
- QA: `.factory-state/artifacts/QA-0241-TASK-0258-handbook-browser-shots.md`

## Expected Outputs

- The four handbook PNG paths above show the rendered Studio UI.
- This task artifact records what was captured and what was not run.

## Implementation Notes

- Capture with a browser on the same machine as the dev servers. Do not treat a successful `curl` to `127.0.0.1` as proof that a remote browser can open the app.
- Do not weaken Vite host checks or the box browser's private-address refusal to obtain the pictures.
- English and Vietnamese copies stay the same bytes, because both guides illustrate the English UI.

## Constraints

- Do not commit to `main`. The owner asked to finish this PR, which allows one squash and `git push --force-with-lease` on this branch. Do not merge unless the owner asks and required CI is green.
- Browser runtime stays off. The model stays on the mock. Discovery may list tools; that is not a browser session.

## Dependencies

- TASK-0253 is already on `develop`. This task only replaces its handbook images.
- TASK-0251 and TASK-0252 are not dependencies and stay deferred.

## Acceptance Criteria

- Both handbook locales use real Studio screenshots for `browser-connection-settings.png` and `browser-agent-url-binding.png`, not generated mockups.
- The connection image shows the "Demo isolated browser" card on Settings → MCP servers, including the tools discovery returned with the default safety toggles.
- The agent image shows the "Web researcher" node selected on the Data tab, with URL source "Filled by the Agent" for `navigate`.
- The guide image paths are unchanged. The capture does not claim the isolated browser runtime executed a page.
- TASK-0251 and TASK-0252 remain in backlog.

## Validation Plan

- Compare the new PNG files with the rendered Settings and editor screens before they are kept.
- Declared project checks stay for a later validation step. This change does not alter application source.

## Assumptions

- A local dev server at the same commit is a valid source for the handbook figures when the box browser cannot reach the VM loopback.
- Default safety toggles hide evaluate, upload and download, so discovery lists six tools.

## Open Questions

- None for this replacement. Extra tab captures stay out of Git until the owner asks to add them to the guide.

## Activity Log

- 2026-11-07: Allocated TASK-0258 with `factory ids next TASK --all-refs` after `git fetch --all --prune`. Branch `factory/task-0258-handbook-browser-shots` from `develop` at `e1c4284d`. Not committed.
- 2026-11-07: `factory ready` passed while this task was in todo. Moved to doing. Replaced the four handbook PNGs with Chrome captures of the local Studio UI (`STUDIO_ENABLE_BROWSER=1`, browser runtime off, mock model, temporary SQLite). Workflow id on this machine was `689d7560`. Not committed. Validation not run.
- 2026-11-07: Kept the discovered "Demo isolated browser" card as `browser-connection-settings.png` (the figure follows Discover tools). The create form stays out of Git. English and Vietnamese guides now say discovery lists six tools at the default toggles, and evaluate/upload/download after those toggles are on. Not committed. Validation not run.
- 2026-11-07: Owner asked to commit this branch. Validation not run. Not pushed.
- 2026-11-07: Validation on this branch. `factory verify run --profile full` recorded a failure in `.factory-state/verification/latest.yaml` because the x86_64 backend virtualenv launched Node as x64, and the installed native bindings are darwin-arm64. Those four commands were run again with arm64 Node and passed: `npm run build` (12s), `npm run lint` (1s, warnings only), `npm run test` (18s), and `sdk/typescript` `npm run test` (1s). Passed on the first run: backend pytest (505s), sdk/python pytest (15s), sdk/typescript build (7s), sdk/typescript typecheck (3s). Not QA-passed. The false factory record was not kept.
- 2026-11-07: Review REV-0241. No blocking findings. Approved for QA. Advisory only; not owner approval of the product change.
- 2026-11-07: QA QA-0241. Acceptance criteria passed by artifact inspection and the recorded eight tool-policy commands. Outcome pass. Passed to done. Merge is not authorized.
- 2026-11-07: Owner asked to finish PR #318. Moved this task to done on this branch. Squash, final checks, `--force-with-lease`, and Draft-to-Ready follow on the same PR. Do not merge.
- 2026-11-07: Final checks on the squashed tree passed. `git diff --check` passed. Tool-policy: frontend build 12s, lint 1s (warnings only), test 18s (frontend 169, React 22, TypeScript SDK 102); backend pytest 1416 passed, 71 skipped, 492.72s; sdk/python 229 passed, 8 skipped, 14s; sdk/typescript build 2s, test 102 passed in 1s, typecheck 1s. Node commands used arm64 Node. `factory validate` still reports the pre-existing TASK-0253 review-reference error that already fails on `develop`; this branch does not change that file. Do not merge.

## Handoff Notes

- Worktree: `/tmp/superstep-wt-0258`. `/workspace` is not present on this Mac, so the worktree is under `/tmp`.
- Review REV-0241 and QA QA-0241 are recorded. Status is done. PR #318 stays the only delivery PR. Do not merge until the owner asks and required CI is green.
- TASK-0251 and TASK-0252 stay in backlog.
