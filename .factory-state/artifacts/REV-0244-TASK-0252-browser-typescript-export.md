# Review

## Metadata

- Project: superstep
- Review ID: REV-0244
- Task ID: TASK-0252
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

Branch `factory/task-0252-browser-typescript-export` stacked on
`factory/task-0251-browser-python-export` at `c39064ed` (PR #321). The owner
authorised the stack on 2026-11-07 because TASK-0251 is not merged. The
reviewed diff is only the TypeScript export on top of that commit.

Files:

- `backend/app/engine/browser_export_ts.py` (new standalone helper)
- `backend/tests/test_browser_typescript_export.py` (new Node execution tests)
- `backend/app/engine/typescript_export.py`
- `backend/app/engine/browser_export.py` (removes the TypeScript refusal constant)
- `backend/app/engine/project_export.py`
- `backend/tests/test_browser_python_export.py` (assertions now expect `browserCall`)
- `handbook/docs/en/guide/browser.md`
- `handbook/docs/vi/guide/browser.md`
- `roadmap.md`
- `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- `.factory-state/tasks/done/TASK-0252-browser-typescript-export.md`

No schema migration, UI component, locale catalog, or secret value was added.
The Python helper clock is unchanged.

## Reference Artifacts

- TASK-0252 acceptance criteria
- REQ-0086 AC8 (TypeScript half; Python is TASK-0251 / REV-0255 / QA-0255)
- DES-0004, ARCH-0002, DEC-0085, PLAN-0006
- `docs/backend-architecture.md` (service may call engine; the embedded runtime imports nothing from `app`)

## Findings

### Blocking

- None.

### Non-Blocking

- The memory driver fetches a whitelisted origin with `fetch`, including a loopback origin, so a local fixture can run. Playwright and Browserless call `requirePublic` before `import("playwright")`. That matches the Python export. It is wider than the studio always-on private-IP block.
- A real Chromium launch and a live Browserless session are not executed. Missing Playwright, a missing token, and a private address fail closed before launch.
- Deno is not installed in this worktree. Tests execute the generated module with Node (`--experimental-strip-types`) and a local LangGraph stub. The emitted file still uses `npm:` specifiers so Deno can load it. This review does not claim a Deno run.
- `max_pages` is in the public policy and is not enforced by the Python or TypeScript runtime.
- When an Agent export runs more than one tool call at once, `interrupt()` can be raised off the graph thread (`Promise.all`). Same-connection browser commands still take the session mutex. A single-call approval pause stays on the calling async chain.

## Standards And Architecture Alignment

- The TypeScript helper is emitted by the exporter. Generated code imports nothing from `app`.
- Annotations `_browser_export` and `_managed_export` stay stripped before save. The recipe test reads the stored workflow and asserts both keys are absent.
- Invalid browser settings stay a managed placeholder. Other managed adapters are unchanged. The TypeScript snapshot has no browser step, so it stays stable.
- Secret fields are not copied into `BROWSER_POLICY`. `.env.example` lists names with empty values. The fallback Playwright import is `import("npm:" + "playwright")` so the project zip does not add a `playwright` dependency. README tells the operator to `npm install playwright` when that driver is chosen.
- No new API error code, envelope, or Alembic migration.
- Upload and download raise an explicit capability refusal outside Studio, including when the allow flag is on. Evaluate allows only `document.title` and `document.body.innerText`, and only when the connection allows it.
- Approval accepts only `true` or `{approved: true}`. A model-shaped `{text: "yes"}` is not a grant. The check happens before a stale observation is applied. Rejection does not change the page URL.
- `GraphInterrupt` and `GraphBubbleUp` are rethrown from the agent tool catch so an approval pause is not reported as "The tool failed".
- The idle test ages `touched` from `Date.now()/1000`, so it does not depend on process uptime. The Python test on the parent commit ages `touched` from `time.monotonic()` for the same reason.

## Design Alignment

No new screen. The handbook section 5 bullet in English and Vietnamese now describes `browserCall` parity: same whitelist, session order, approval, and refusal; Node (`npx tsx`) or Deno; Playwright is an optional install. `scripts/check-browser-handbook.py` passed. No new screenshots.

## Validation Review

Declared tool-policy commands were run from `/tmp/superstep-wt-0252` with arm64 Node (`process.arch` arm64, v22.12.0), not through the x86_64 backend virtualenv:

- `backend`: `.venv/bin/python -m pytest` — 1435 passed, 71 skipped, 526.00s, exit 0
- Focused backend pytest (`test_browser_typescript_export.py`, `test_browser_python_export.py`, `test_typescript_export.py`, `test_project_export.py`, `test_handoff_exports.py`) — 45 passed, 30 skipped, 50.67s, exit 0. The skips are the existing Deno-gated TypeScript export checks.
- repo root `npm run build`, `npm run lint`, `npm run test` — exit 0 (lint warnings only, pre-existing). Frontend tests 169 passed. `@superstep/react` tests 22 passed.
- `sdk/python`: `.venv/bin/python -m pytest` — 229 passed, 8 skipped, 13.75s
- `sdk/typescript`: `npm run build`, `npm run test` (102 passed), `npm run typecheck` — exit 0
- `scripts/check-browser-handbook.py` — passed
- `git diff --check` — passed

The full backend pytest is recorded above and in QA-0244.

`factory validate` was not used as a gate. On clean develop it already fails because TASK-0253 lacks the capital strings the done-task check wants. CI runs `factory verify`, which does not call `factory validate`.

## Assumptions

- The owner authorised implementation through a Ready pull request and did not authorise merge.
- The pull request base is `factory/task-0251-browser-python-export`, not `develop`, so the diff is only this task. Merge TASK-0251 first.
- REQ-0086 stays open until both export pull requests merge.

## Required Follow-Up

- Merge waits for the owner. Merge PR #321 before this pull request.
- Do not mark REQ-0086 done on this branch.

## Review Decision

Approved for QA. No blocking findings.
