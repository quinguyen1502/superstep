# Review

## Metadata

- Project: superstep
- Review ID: REV-0241
- Task ID: TASK-0258
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: approved for QA

## Review Scope

Branch `factory/task-0258-handbook-browser-shots` against `origin/develop` at
`e1c4284d` (PR #318). Commits reviewed: `a2c814ed` (handbook figures and the
six-tool sentences) and `06d20038` (validation activity log).

Files:

- `.factory-state/tasks/doing/TASK-0258-handbook-browser-shots.md`
- `handbook/docs/en/guide/browser.md`
- `handbook/docs/vi/guide/browser.md`
- `handbook/docs/en/images/browser-connection-settings.png`
- `handbook/docs/vi/images/browser-connection-settings.png`
- `handbook/docs/en/images/browser-agent-url-binding.png`
- `handbook/docs/vi/images/browser-agent-url-binding.png`

No application source, schema, locale catalog, or export task changed.

## Reference Artifacts

- TASK-0258 acceptance criteria
- REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006
- TASK-0253 (previous handbook delivery on develop)
- TASK-0251 and TASK-0252 (backlog, deferred)
- Task activity log for the eight tool-policy commands

## Findings

### Blocking

- No blocking findings.

### Non-Blocking

- The discovery step in both guides changed. The original out-of-scope line said
  not to rewrite the guide. The owner later asked for the next step so the
  sentence matches the card: six tools at the default safety toggles, and
  evaluate, upload, and download after those toggles are on. The introduction
  still lists all nine capabilities. This is owner-directed and not a defect.
- `.factory-state/verification/latest.yaml` is not a pass record. `factory
  verify` failed four Node commands because the x86_64 backend virtualenv
  launched Node as x64 against darwin-arm64 bindings. Those four commands passed
  when run again with arm64 Node. The false record was discarded. The activity
  log is the evidence.
- `browser-connection-settings.png` is the card element, not the Settings page
  chrome. It shows "Demo isolated browser", managed, Personal, and six tools
  after Discover tools. Last discovery reads 11/7/2026, 8:18:44 AM.
- `browser-agent-url-binding.png` includes the editor sample input
  `Where is my order A100?`. The required content is present: workflow "Web
  research", node "Web researcher" selected, Data tab, navigate URL source
  "Filled by the Agent".
- Captures were taken on this Mac at the same develop commit. Workflow id
  `689d7560`. The box workflow ids were not on this machine. The browser runtime
  was not started. Recent operations on the card say "No operations yet."

## Standards And Architecture Alignment

Docs and factory metadata only. No router, service, repository, API envelope,
error catalog, or frontend component changed, so the UI, layering, and locale
rules are not in play. English and Vietnamese guides use the same image paths
and the same PNG bytes. TASK-0251 and TASK-0252 remain `backlog` and were not
edited.

## Design Alignment

The figures match the first-delivery handbook in DES-0004 / PLAN-0006: the
connection card after Discover tools, and the Agent Data tab URL source for
`navigate`. Default safety toggles hide evaluate, upload, and download, so the
card lists navigate, snapshot, click, fill, extract, and screenshot. The pages
do not claim a browser run. Alt text and image paths are unchanged.

## Validation Review

Declared checks are the eight commands in `.factory-state/tooling/tool-policy.yaml`.
The task log records all eight passed on this diff: backend pytest 505s,
sdk/python pytest 15s, sdk/typescript build 7s, sdk/typescript typecheck 3s on
the factory run; `npm run build` 12s, `npm run lint` 1s (warnings only),
`npm run test` 18s, and sdk/typescript `npm run test` 1s with arm64 Node.
This review did not re-run them. Finish-pr repeats them on the squashed tree
before push. The task is not QA-passed by the log alone.

## Assumptions

- A local Studio UI at develop `e1c4284d` is a valid source for these figures
  when the box browser cannot open the VM loopback.
- Identical PNG bytes for both locales are correct because both guides show the
  English UI.

## Required Follow-Up

- None before QA. TASK-0251 and TASK-0252 stay deferred and are a separate
  stream. Do not merge PR #318 until the owner asks and required CI is green.

## Review Decision

Approved for QA. This recommendation is advisory and is not owner approval of
the product change. The owner separately asked to finish PR #318.
