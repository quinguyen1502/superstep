# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0241
- Task ID: TASK-0258
- QA Owner: Grok (advisory; owner asked to finish the PR, not to merge)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: pass

## Validation Scope

Inspected the branch diff against `origin/develop` at `e1c4284d` and the four
handbook PNGs on `factory/task-0258-handbook-browser-shots`. Referenced the
validation already recorded in the TASK-0258 activity log. Did not start the
browser runtime and did not run a new product experiment.

## Acceptance Criteria Coverage

- Criterion: Both handbook locales use real Studio screenshots for
  `browser-connection-settings.png` and `browser-agent-url-binding.png`, not
  generated mockups.
  - Result: pass
  - Evidence: Visual inspection of the committed PNGs. Connection card is the
    rendered "Demo isolated browser" MCP card. Agent figure is the rendered
    editor. English and Vietnamese copies are the same bytes:
    connection `0439b91624173f0412e23672e0dac280350f1169` (1284x881),
    agent `ef2e1ddeb83333d698b3d181adfc4777b326c862` (2160x1500).
- Criterion: The connection image shows the "Demo isolated browser" card on
  Settings → MCP servers, including the tools discovery returned with the
  default safety toggles.
  - Result: pass
  - Evidence: Card reads managed, Personal, "6 tools found", last discovery
    11/7/2026, 8:18:44 AM, and lists navigate, snapshot, click, fill, extract,
    and screenshot. Evaluate, upload, and download are absent. The crop is the
    card, which is the figure the guide step describes.
- Criterion: The agent image shows the "Web researcher" node selected on the
  Data tab, with URL source "Filled by the Agent" for `navigate`.
  - Result: pass
  - Evidence: Workflow title "Web research", selected Agent node "Web
    researcher", Data tab active, Browser and fetch URL bindings, navigate,
    URL source "Filled by the Agent".
- Criterion: The guide image paths are unchanged. The capture does not claim
  the isolated browser runtime executed a page.
  - Result: pass
  - Evidence: Diff keeps `../images/browser-connection-settings.png` and
    `../images/browser-agent-url-binding.png` in both guides. The card says
    "No operations yet." The task log records `STUDIO_ENABLE_BROWSER=1` and
    the browser runtime left off.
- Criterion: TASK-0251 and TASK-0252 remain in backlog.
  - Result: pass
  - Evidence: Both files are still under `.factory-state/tasks/backlog/` with
    status backlog (deferred). The branch diff does not touch them.

## UX And Accessibility Coverage

- Criterion: Handbook figures match the English UI described by the guide, in
  both locales.
  - Result: pass
  - Evidence: Existing alt text still points at the same paths. The English
    and Vietnamese discovery sentences both name the same six tools. No app
    control, theme token, or locale catalog changed, so no new accessibility
    surface was added.

## Checks Performed

- Artifact inspection of the seven-file diff and both unique PNGs.
- Confirmed TASK-0251 and TASK-0252 status on this branch.
- Recorded tool-policy results from the earlier activity log, then repeated
  on the squashed tree before push: frontend build 12s, lint 1s (warnings
  only), test 18s (frontend 169, React 22, TypeScript SDK 102); backend
  pytest 1416 passed, 71 skipped, 492.72s; sdk/python 229 passed, 8 skipped,
  14s; sdk/typescript build 2s, test 102 passed in 1s, typecheck 1s.
  `git diff --check` passed. Node commands used arm64 Node.
- `scripts/check-browser-handbook.py` is not in tool-policy and was not used
  as a declared check.

## Defects

- None.

## Gaps Or Untested Areas

- The isolated browser runtime was not executed. The task lists that as out of
  scope.
- `.factory-state/verification/latest.yaml` was not updated to a pass. The
  activity log is the evidence. The factory failure was the x86_64 virtualenv
  launching arm64 Node bindings.
- Captures used local workflow `689d7560` on this Mac, not the box workflow ids.

## Residual Risk

- The connection card includes the discovery timestamp 11/7/2026, and the agent
  figure includes the editor sample input. Both are rendered UI. They will age
  as copy, not as a behavior defect.
- The eight tool-policy commands and `git diff --check` passed on the squashed
  tree. `factory validate` still fails on develop's TASK-0253 review-reference
  gap. This branch does not change that file, and factory verify CI does not
  run `factory validate`.

## Assumptions

- The validation log on `06d20038` still describes this handbook diff. Review
  and QA add factory metadata only.

## Required Follow-Up

- None for the handbook figures. Keep TASK-0251 and TASK-0252 deferred.
- Do not merge PR #318 until the owner asks and required CI is green.

## QA Decision

Passed to done. Merge is not authorized.
