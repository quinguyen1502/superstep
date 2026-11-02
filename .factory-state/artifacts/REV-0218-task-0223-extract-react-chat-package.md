# Review

## Metadata

- Project: superstep
- Review ID: REV-0218
- Task ID: TASK-0223
- Reviewer: Codex self-review, advisory; owner accepted 2026-11-02
- Created/Updated: 2026-11-02
- Outcome: approved for QA; full verification and targeted regressions passed; owner accepted 2026-11-02

## Review Scope

Diff against develop 221df9a after #285–287 merged: root npm workspace/lock, packages/react presentation and its shadcn dependency closure, frontend forwarding modules and Studio adapter, v1 public-page transport, tests, Docker/CI/scripts/docs and Factory workspace compatibility. No backend runtime/schema change or public hook/theme/widget API is introduced.

## Reference Artifacts

TASK-0223, REQ-0082, PLAN-0002, DEC-0079/0033/0008/0009/0010, docs/ui-conventions.md, QA-0218. Factory upstream main commit ce00ad0 in quinguyen1502/sw-ai-factory precedes the byte-identical vendored changes.

## Findings

### Blocking

No unresolved blocking implementation findings.

Resolved during review: coded errors initially depended on the Studio's global i18next singleton. Shared components now pass the host's context instance to the one error formatter; a standalone SSR regression proves an independent host's translation is used. Existing Studio error formatting remains forwarded through lib/i18n.ts.

Resolved migration requirement: Factory did not recognise workspace membership/hoisting. The upstream fix installs declared npm members once from the locked root, validates hoisted/nested dependencies and preserves unrelated packages. All 146 upstream tests passed before push/vendor sync. The project dependency gate now succeeds with one npm command.

Resolved by full verification: the Deno export-test probe detected the new repository package.json and switched to manual node_modules resolution. The test harness now explicitly uses its isolated Deno cache for check/run, leaving exporter/runtime source and assertions unchanged. All 39 export regressions pass. A local mixed-architecture Node installation was also corrected by using the same runtime PATH for install and verify.

Resolved compatibility detail: synthetic subgraph/agent exit icons inherit their original icons in the shared map. A regression compares all Studio node metadata icons with the shared presentation, including synthetic entries.

### Non-Blocking

- Public useChat, composed Chat, scoped CSS/theme, widget and mobile remain later tasks; this internal extraction is not package publication. Existing React 19 is exercised; a React 18 host/device compatibility matrix is not claimed.
- Four browser variants are visually unchanged on inspection: both dark images are pixel-identical; each light image differs by 19/1152000 pixels at the 24px avatar corners. This is recorded honestly as a small raster difference, not four byte-identical screenshots.
- Existing frontend hook/i18n warnings, CodeMirror chunk warning and combined pre-existing npm audit findings are outside this extraction. No external package name/version pair was added beyond the previous two lockfiles.

## Standards And Architecture Alignment

Eight chat components and 16 shared shadcn primitives have one owner in packages/react. Frontend compatibility modules only forward exports; Studio child-run reads and reviewer navigation are provided by its adapter/context, not imported into the package. Studio settings/session ownership/routes stay in frontend. Markup, theme tokens, en/vi keys and existing delete interactions are preserved; no new delete feature, literal UI text or hard-coded colour is introduced. The strict UI class guard covers both source trees.

The public page uses v1 HTTP/socket paths and auth frames without query tokens. A small pure bridge preserves the existing trace presentation, ignores additive frames and sends strict message/answer fields. Studio's run transport remains separate. Stable legacy logo asset URLs are retained so existing unchanged e2e/favicon contracts continue to pass. API calls still use lib/api.ts and shared error formatting.

## Design And Validation Review

The dedicated extraction implements DEC-0079 without the later hook/theme surface. Bundle budget, existing en/vi chat flows, standalone SSR/sanitisation/host capabilities, clean install, built ESM imports and cross-origin sample-host integration are exercised. Screenshots and browser state stay in temporary directories, never Git/package contents. Full Factory verification and final PR CI are the delivery gates; QA-0218 records their actual outcomes.

## Required Follow-Up

Owner accepted #288 and explicitly requested merge on 2026-11-02. Finish the same PR with task done, one commit and passing exact-head checks before merge. TASK-0224 remains later work; tag/package publication and production deployment are not authorised.

Final validation review: full Factory rerun passed 8/8; final icon compatibility correction then passed complete root build/lint/tests (152 frontend, 4 React, 94 SDK). No blocking findings remain. QA-0218 preserves the initial setup failures and final evidence; exact-head CI and owner acceptance remain separate.

## Owner Approval And Merge Finalisation

On 2026-11-02 the owner accepted the reviewed delivery and explicitly requested merging #288 ("Ok merge"). TASK-0223 moves to done on that same PR and is squashed to one commit. Finalisation preserves the reviewed implementation tree; only lifecycle/review/QA/plan records change. Original head 46e001a6 passed 20 CI checks (one expected GHCR skip), including full Factory, all Playwright shards, Docker and the host gate. Rewritten-head checks must pass before Ready/merge. This supersedes earlier pending-acceptance/merge statements; no package or tag publication is approved.
