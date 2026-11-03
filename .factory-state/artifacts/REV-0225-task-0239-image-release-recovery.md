# Review

## Metadata

- Project: superstep
- Review ID: REV-0225
- Task ID: TASK-0239
- Reviewer: Codex (advisory)
- Created/Updated: 2026-11-04
- Outcome: advisory approved; reviewed-head CI passes; release authorisation applies to necessary operational recovery

## Review Scope

Existing .github/workflows/image.yml: verified installation of the already pinned scanner; one source-resolution job; main-only release recovery dispatch; identical resolved SHA across smoke/build/publish; version/SHA metadata. No runtime/package/dependency/version source changes.

## Reference Artifacts

TASK-0239, TASK-0238, QA-0224, accepted DEC-0033/DEC-0084, release PR #295 and image run 41736387584.

## Findings

### Blocking

No blocking source findings. The release itself remains blocked on image publication until the fix is accepted, integrated and run for immutable v0.11.0.

### Non-Blocking

Dispatch must use the fixed workflow from main after integration while checking out the old release SHA. Running the original tag workflow again still uses its failed upstream installer. No existing tag/package is moved or republished. Recovery reuses all existing smoke and both fixable-CRITICAL gates; skip-setup-trivy skips only third-party installation after the same binary was verified locally in the job.

## Standards And Architecture Alignment

Single image workflow, source binding shared by both consumers, read-only default/source/test permissions and package write only in publish. Manual input is passed through env and regex validated, never interpolated into shell. Only stable existing tags in main history with matching backend/Python/frontend versions may dispatch. PR events never publish. Concurrent manual/tag runs share a group. No framework changes, new dependency, backend/UI/API change, credential or evidence archive in Git.

Official Trivy v0.69.3 asset SHA256 is hard-coded and verified before extraction/execution; curl has bounded retries/timeouts. Pinned scan action and thresholds remain unchanged. Metadata action uses git context for the checked-out SHA and explicit validated tag values, avoiding workflow-ref/main labels on old release builds.

## Design Alignment

No user-facing design change. Native scope stays deferred and the existing release tag/source remains immutable.

## Validation Review

Actionlint v1.7.12 passes; official archive checksum passes; real v0.11.0 resolves to main 7520f6a1. Isolated Git checks accept integrated matching tags and reject malformed/missing/mismatched/unmerged tags, preserving PR source and publish/scan boundaries. All 12 deploy configs pass. QA-0225 records runtime continuity, registry receipts and remaining CI/manual-run gates.

## Assumptions

Owner's release/continue instruction authorises necessary recovery implementation. The owner explicitly requested release and continuation; the required bounded pipeline fix/integration to complete that same release falls within that authorisation. No unrelated feature, credential, registry, future release or tag rewrite is authorised. No separate owner review of this diff is claimed.

## Required Follow-Up

Exact PR CI, owner acceptance, same-PR move to done and fresh final checks before merge. Integrate fixed workflow into main, dispatch image.yml from main with release_tag=v0.11.0, verify four public image digests, then publish the existing Draft GitHub Release. Retain all existing registry/source tags.

## Review Decision

Advisory approved for QA, no blocking implementation finding. Actual image publication remains a release gate.

## Final Review And Delivery Gate

Head 12c0ee08 passes all 22 checks/one expected skip. Actual Linux image CI verifies the pinned archive, Trivy version and both scans; all smoke/CLI tests pass. Canonical full profile passes in Factory CI. No blocking review finding. TASK-0239 is done under the existing explicit release/continue instruction; lifecycle-only finalisation changes no workflow/product source. Wait for final-head CI before merging this same PR, then integrate the fix to main and run immutable v0.11.0 recovery. Earlier pending-separate-acceptance statements were an assistant assumption; no extra approval gate is imposed on this already authorised release operation. Actual four-image publication and final GitHub Release remain to be verified.

## Final CI Test Review

04dba764 CI exposes the app-key nested-modal focus race a second time during release validation (en/dark; prior vi/dark). The same PR makes the existing test await focus ownership before both Escapes and hidden state after the second one. These are observable readiness assertions; there are no sleeps, extra retries, relaxed expectations or production changes. All secret protection, exact-name revocation and parent-dialog-visible assertions remain. Local isolated 12-case repetition passes in 1.2 minutes. Advisory review finds no blocking issue; this bounded test synchronisation belongs to the active release CI repair, and final amended-head checks still gate merge.

- Final focus guard polls a boolean for activeElement inside the secret modal; failed expectations cannot dump the secret input DOM/value. Final guard passes the same 12 isolated en/vi light/dark cases in 59.0 seconds (superstep-0239-app-keys-safe-repeat.log). Existing product behaviour, secret capture policy and all rotation/revocation assertions remain unchanged; final amended-head CI gates merge.
