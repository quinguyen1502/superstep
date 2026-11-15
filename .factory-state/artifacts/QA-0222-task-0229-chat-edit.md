# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0222
- Task ID: TASK-0229
- QA Owner: Codex (advisory local QA)
- Created/Updated: 2026-11-03
- Outcome: pass (local acceptance); exact-head CI gates delivery

## Validation Scope

Accepted DEC-0084 editing and shared branch foundation. Reference: TASK-0229, REQ-0082, PLAN-0002 and REV-0222. Native tasks remain deferred; regeneration remains TASK-0230. Shared Python/CLI/server stays 0.10.2 until release preparation; npm versions are unchanged.

## Acceptance Criteria Coverage

| Criterion | Evidence/result |
| --- | --- |
| Preserve source and exclude discarded future | Passing API regression for an early edit; Studio/public browser checks verify cancellation, branch reload and return to original. |
| Durable deduplication and atomic source snapshot | Concurrent same-intent preparation returns one branch; concurrent execution starts one run. Changed payloads conflict. Late source changes remove staged files; deleted branch tombstones cannot recreate an execution. |
| Correct prefix agent and eligibility | Before-fix regressions for removed/readded targets and an earlier pending root now pass; missing historical agent metadata refuses the edit. Human answers and inherited turns are rejected as targets. |
| Owned independent files/feedback | DB/fs tests pass source deletion without branch file loss, remapped IDs, readonly prefix feedback and changed file policy. Live MinIO case is locally skipped and required in CI; the existing MinIO job now includes edit tests. |
| Authentication and quotas | Studio cross-owner and anonymous cross-visitor refusal; third-party cross-subject/origin refusal, key rotation/revocation and current issuing-key audit. A dedicated daily-cap test denies execution and leaves the original unchanged. |
| SDK admission/recovery | TypeScript store changes session IDs and reads a repeated admitted intent without a second socket; loss before run_started recovers using the reserved run ID. Python sync/async cover the same prepared/finished path. Unsupported servers fail before an edit request. |
| Shared accessible/localised UI | Shared modal confirms external-effect reruns, disables unchanged save and preserves operation IDs after failed responses. Studio/cookie-public tests pass en/vi; host matrix covers React/widget/headless, files, Human approvals, history and identity. Full final-head CI remains the gate. |

## Checks Performed

- Local targeted regressions: 16 passed / 1 MinIO-only skip in superstep-0229-final-isolated.log; final routing/busy/layer set also passes in superstep-0229-final-regressions.log. Additional branch UUID hardening is covered by final verification/CI.
- Studio/cookie-public browser acceptance: two locales pass (22.7s), log /private/tmp/superstep-0229-main-e2e-final.log. Traces are off for these new scenarios.
- Shared host: final source on React 18 and 19 each passes three Node static/security tests and React, widget and headless scenarios. Logs /private/tmp/superstep-0229-host18-final-source.log and superstep-0229-host19-final-source.log. Widget edit emits exactly two new message/answer pairs (root and Human response), excluding inherited history.
- Strict en/vi handbook and media checks pass; final content rerun recorded in superstep-0229-handbook-{en,vi,images}-final.log.
- Full declared Factory profile passes all eight commands in /private/tmp/superstep-0229-verify-final.log; canonical verification/latest.yaml reports passed. The final UI error fallback is covered by a fresh shared React build and all 19 unit tests in superstep-0229-react-final.log, followed by both host matrices. Factory validation, artifact-ID checks and git diff --check gate pushing the completed implementation.

## UX And Accessibility Coverage

Labelled edit buttons/textarea, clear source-preservation description and external-action confirmation, ordinary save/cancel controls, read-only inherited actions, a source-navigation button and localised errors. All new controls use shadcn/theme tokens; session deletion uses exact-name confirmation without changing DELETE. Captures cover English/Vietnamese and light/dark/custom theme contexts; no image, archive, auth state or trace is committed.

## Initial Failures And Resolution

- Concurrent preparation initially returned stale rather than the winning intent; the repository now rereads after losing the source CAS. Duplicate execution assertions remain intact.
- Browser assertions initially matched file metadata along with message text; the text assertion now targets its bubble and separately verifies the file. Widget cases scope the intended root and explicitly choose language after navigation, preserving existing shared history/locale behaviour.
- A test initially compared an internal app-key audit ID with its public key_id; it now resolves the key record and verifies the correct internal issuer plus cross-user refusal.
- The first complete profile passed seven commands but two new public functional tests used shared IP budgets and did not reach their initial message. Functional fixtures now isolate transport counters, with a separate explicit daily-quota denial assertion. Production rate-limit policy was not disabled or weakened.
- Source review found genuine prefix-agent and pending-root admission defects; before-fix logs superstep-0229-agent-before2.log and superstep-0229-busy-before.log reproduce them. Final regressions pass without replaying old effects or exposing checkpoint/state input.

## Evidence

Ignored browser outputs under frontend/test-results; inspected copies under /private/tmp/superstep-0229-visual: studio-edit-vi.png (light), react-edit-en-custom.png (custom font/theme), widget-edit-confirm-vi-dark.png and widget-edit-confirm-en.png (dark). Synthetic accounts/provider text only. CI uploads UI artifacts through existing bounded-retention paths; no credential-bearing traces are added. Persistent evidence is this QA record, the reproducible tests and the linked PR checks; temporary captures are not required repository assets.

## Gaps And Residual Risk

Local browser is Chrome; CI covers React 18/19 and the full existing Playwright suite. No real provider/customer data, Safari/Firefox/device tests or native delivery claim. Live S3 behaviour is gated by CI MinIO, not claimed from the local skip. Forks duplicate storage and run the currently saved workflow; confirmation does not undo earlier external effects. An admitted but unsaved run remains unknown/non-replayable after a process loss. Historical agent context may expire and make an old edit unavailable; starting a new conversation remains possible. Schema 0053 adds lineage/readonly/idempotency metadata; release migration/backup validation is still required before publishing 0.11.0.

## Required Follow-Up

Record exact pushed-head CI on existing #292, including live MinIO; obtain owner implementation/merge acceptance, then integrate TASK-0229 before TASK-0230. No release tag or package publication is implied.

## QA Decision

Local acceptance passes with no unresolved local failure. CI remains a delivery gate, with live MinIO verified remotely. Keep the PR Draft/task in review pending owner implementation acceptance; do not claim overall REQ-0082 completion.

## Owner Acceptance And Finalisation (2026-11-03)

Owner explicitly approved implementation/merge of #292 and continuing TASK-0230 ("Approve"). Reviewed source head b80a0a1a passes all 22 CI checks with two expected deploy/publication skips, including live MinIO (46 passed), SQLite (1221 passed/26 skipped), PostgreSQL/Redis (1187 passed/60 skipped), all three E2E shards and React 18/19 host matrices. No unresolved blocking finding or QA failure remains. Finalisation changes lifecycle records only; final single-commit checks must pass before the authorised merge. This supersedes the earlier pending-owner/CI statements. No native completion, release tag or package publication is implied.
