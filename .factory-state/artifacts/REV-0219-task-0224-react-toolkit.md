# Review

## Metadata

- Project: superstep
- Review ID: REV-0219
- Task ID: TASK-0224
- Reviewer: Codex (advisory source review; owner approval remains separate)
- Created: 2026-11-02
- Updated: 2026-11-03
- Outcome: owner accepted; approved for Ready finalisation

## Review Scope And References

REQ-0082, PLAN-0002, DEC-0079, TASK-0224, docs/ui-conventions.md and the branch diff from develop 7c7348bc. Public hook/components, shared shadcn primitives/confirmation, CSS/locales, standalone Vite example, CI/Docker and tag-only publishing configuration. No backend/schema/Python implementation change.

## Findings

### Blocking

No unresolved blocking findings.

Resolved before delivery: Rating initially required a narrower presentation turn than the SDK returns. Its public prop now accepts the SDK turn directly, with a compiled declaration-consumer probe. Session loading now disables submission; identity/session changes close destructive dialogs and clear stale draft/error state. Regression tests cover these cases.

Resolved lifecycle details: StrictMode replay retains the live resource; real unmount/identity changes release its store/socket and abort work. A Human answer shows its live reply without inventing another visitor turn. File removal cancellation settles its promise, previews are released, and file/rating deletion uses the canonical exact-name dialog with unique IDs.

Resolved CSS details: generated preflight, typography and selectors are rooted at .superstep-chat; variables/keyframes are namespaced and host cascade layer ordering is untouched. Radix portals stay within the provider. Ambient host data-color-scheme does not activate a provider's dark variant. Button/InputGroupButton forward refs for React 18 asChild consumers.

Release preparation includes repository metadata matching the source repository, required by npm provenance (https://docs.npmjs.com/generating-provenance-statements/). The tag guard is executed with a matching and mismatching version. No tag or package is published.

### Non-Blocking

- Browser coverage is Chrome with React 18.3.1 and the workspace React 19; no device/Safari/Firefox claim.
- Host CSS can still inherit into the provider; this is scoped CSS, without a Shadow DOM. Restored Human history has the saved prompt, with text/approve/reject controls; structured fields/options render when present in the streamed question.
- The first local full profile exposed an unchanged backend wall-clock test failure. It is recorded in QA-0219; its assertion is preserved and the isolated/full reruns pass.
- Existing lint warnings and forward-export warnings remain non-fatal; the strict UI class guard passes.

## Standards And Architecture Alignment

The hook binds the existing SDK/store instead of duplicating transport or business logic. Studio remains on the same presentation components. Locale resources/theme tokens are generated from canonical frontend dictionaries/CSS. New strings have en/vi parity; UI controls use shadcn variants and theme tokens. Shared errorText formats coded errors. No new server error code, schema, raw SQL or backend layer change.

The UI checklist has been run: no forbidden colours/hex strings, no custom replacement for shadcn controls, typed confirmation for new removals, no node/template config changes, strict class guard, row-alignment checks in both themes/languages and screenshots outside Git.

## Validation Review

QA-0219 records actual local results, the initial timing failure and its passing rerun, public-contract compilation, React 18/19 browser acceptance, package contents and the metadata-only finalisation checks. Exact-head CI and owner acceptance remain delivery gates on the Draft PR.

## Review Decision And Follow-Up

Advisory approval for QA and owner review. No implementation blocker remains. Keep TASK-0224 in review and its PR Draft until human acceptance; no merge, release tag, npm publication or deployment is authorised by this task.


## Fresh-Checkout Bootstrap Follow-Up (2026-11-03)

The first pushed head passed Factory/backend/SDK/Docker and React-host checks, but its general e2e startup bypassed the package build. A fresh npm ci checkout reproduces a Vite overlay: provider.tsx cannot resolve messages.generated.js (and SDK build outputs are also absent). Existing local dist files had masked this gap. The old main CI run is cancelled while the fix is prepared.

Frontend predev now owns SDK/toolkit build and asset generation; root dev, dev.sh and the Playwright web-server use that same lifecycle. No duplicate root predev or direct-Vite bootstrap remains. Cold-start browser probe changes from overlay=true/email=false to overlay=false/email=true with no page errors, starting from absent SDK/toolkit dist and generated locale files. Logs: /private/tmp/superstep-0224-bootstrap-before.log and superstep-0224-bootstrap-after.log. Dependency versions are unchanged; Factory source fingerprints are refreshed. Canonical root build/lint/tests pass on the clean bootstrap-fix commit; the 16 targeted chat regressions also pass from absent build/generated outputs (1.6m); exact-head CI remains the delivery gate.

The first cold-start 16-case run was 14/16: a shared-IP read budget returned HTTP 429 during the English daily-cap case, and the app-key case attempted scrolling while the settings dialog was unstable. UI fixture now disables only STUDIO_PUBLIC_CHAT_RATE_READ; backend test_page_loads_are_limited_per_ip still passes with its explicit threshold, production defaults and daily-cap assertions are unchanged. The app-key test waits for settled motion and asserts the dialog remains visible before scrolling, preserving every key/secret/revocation/alignment assertion. Both failing cases passed twice (4/4), then all 16 chat regressions passed together. Logs: /private/tmp/superstep-0224-bootstrap-root.log, superstep-0224-bootstrap-retry-final.log, superstep-0224-bootstrap-chat-final.log and superstep-0224-read-rate-security.log. No screenshot/trace/auth material is added to Git. Updated-head CI is required before acceptance.


## Owner Acceptance And Ready Finalisation (2026-11-03)

The owner accepted the implementation ("Approve") after PR #289 head b0c21ab65da49d28e120c57fb13b2d28b19614c7 completed 21 successful CI checks and one expected GHCR publication skip. This includes the full Factory profile, both backend databases, all three general Playwright shards, React 18/19 host acceptance, SDKs and image/security smoke checks. Earlier setup/timing failures remain documented above and are resolved by the recorded corrections/reruns.

TASK-0224 moves to done on the same PR for a rebased, single-commit Ready delivery. This supersedes the earlier pending-human-acceptance/Draft-only statements; the implementation tree is preserved. Required validation and CI remain gates on the rewritten head and their actual final results are reported on #289. No merge, release tag, npm publication or deployment is approved.
