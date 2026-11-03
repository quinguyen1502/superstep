# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0225
- Task ID: TASK-0239
- QA Owner: Codex (advisory)
- Created/Updated: 2026-11-04
- Outcome: local and reviewed-head CI acceptance pass; final-head CI and actual manual release remain delivery gates

## Validation Scope

Pinned scanner installation and immutable-tag image recovery after upstream DNS failure. References: TASK-0239, REV-0225, TASK-0238/QA-0224, main release #295.

## Acceptance Criteria Coverage

| Criterion | Result/evidence |
| --- | --- |
| Pinned verified scanner | Official GitHub release metadata and actual 46 MiB Linux amd64 archive both have SHA256 1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75; archive contains trivy. Workflow checks this before extraction/execution; both existing scans retain CRITICAL, ignore-unfixed and exit-code 1. Linux execution is a PR-image CI gate; local host is macOS. |
| Validated immutable source | Actual v0.11.0 resolves to 7520f6a1997247aec9d163f83ef2a43c9dc9d6f0 and shared versions 0.11.0. Temporary Git fixtures reject a tag outside main history and a tag with mismatched package versions. Invalid, leading-zero, injected-newline and missing tags reject. Both test and publish checkout the same resolved SHA. |
| Publishing boundaries | Manual source job is main-only; publish needs both source and passed smoke/scan job, never runs for pull_request; only publish has packages write. Metadata uses checked-out git context and selected semver; major 0 tag remains disabled. PR source-path check passes. End-to-end manual publish awaits approved main integration. |
| Syntax/configs | Checksum-verified temporary actionlint v1.7.12 passes image.yml. All 12 existing deploy configs pass; diff and Factory structure/verification/ID checks are required before push. |
| Full continuity | No runtime/package/dependency/version source changes from released 0.11.0. Prior canonical full profile 8/8 and main CI 41736279298 pass for those identical sources. Exact PR CI will run the canonical profile and all applicable runtime/browser/image checks on this workflow change. |

## Checks Performed

- /private/tmp/superstep-0239-check-source.py reports PASS for real immutable source, fixture history/version/injection checks and unchanged publish/scan boundaries. Fixtures remain outside Git.
- /private/tmp/superstep-0239-tools/actionlint .github/workflows/image.yml exits 0; downloaded official actionlint v1.7.12 darwin-arm64 asset SHA256 aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f verified.
- Trivy official metadata: https://api.github.com/repos/aquasecurity/trivy/releases/tags/v0.69.3; direct GitHub asset download succeeds and its SHA256 matches. No get.trivy.dev installer is used by the repaired workflow.
- Image release 41736387584 attempts 1/2 fail in scanner installation with curl code 6; attempt 3 diagnostic also fails. Upstream installer commit 4918c342 uses get.trivy.dev, which cannot resolve; github.com and ghcr.io resolve. Smoke/CLI before that step pass; no vulnerability rejection is inferred.

## Published 0.11.0 Delivery Receipt

Release PR #295 merged main 7520f6a1 after 46 checks and two expected skips (push retry closes fixture slug collision and E2E focus timing failures without product edits). Main CI 41736279298 and handbook 41736279288 pass. Tags v0.11.0, sdk-ts-v0.2.0 and sdk-react-v0.1.0 all point to that same main commit. No tag is moved.

- PyPI 0.11.0 publication 41736387636 succeeded after the owner's explicit release instruction and authorised environment review. Public wheel downloads, has 37 files and SHA256 616e95bdb76b67936ac7546235c1de1d3d74ef8c0b20e61e0f8dc7c562af9927, identical to QA-0224's local candidate. Chat core/stream/token modules, version and typing are present.
- npm SDK 0.2.0 publication 41736388682 and React 0.1.0 publication 41737221886 succeed. Public anonymous metadata and downloaded tarball integrity checks pass; 82 SDK files, 100 React files, required exports/CSS/messages/types present. The two additional files in the earlier local 102-file React receipt were stale, unused chat-edit-dialog build outputs; fresh CI packaging correctly excludes them. No runtime export references those files.
- Receipt script /private/tmp/superstep-0.11.0-verify-published.py and /private/tmp/superstep-0.11.0-published/packages.json record public artifact URLs and SHA/integrity. Archives are outside Git. Initial npm processing/one local TLS timeout resolved on a read-only retry; nothing was republished.
- Public demo /api/health reports version 0.11.0, ok/run_bus_ok/attachment_storage_ok true. GitHub Release v0.11.0 is still Draft; GHCR 0.11.0 is not claimed published.

## UX And Accessibility Coverage

No UI change; existing bilingual product flows and screenshot policy remain unchanged. No evidence images/archives enter Git.

## Defects

Upstream download-host DNS failure blocks the old immutable-tag workflow. This scoped workflow fix avoids that host and permits recovery against the unchanged release source; exact CI/manual execution remain required.

## Gaps Or Untested Areas

Local macOS cannot execute the downloaded Linux binary. PR image CI must exercise checksum/install/version and both real scans. Manual tag dispatch/publication cannot be claimed before owner acceptance and main integration. No live provider data or native delivery.

## Residual Risk

GitHub asset/registry outages remain external dependencies; bounded retries and fixed checksums fail closed. Building an existing immutable tag may resolve newer unpinned system dependencies, as a normal workflow rerun already can; source/tag/package versions are never changed. Verify actual image digests and publication results before publishing the GitHub Release.

## Assumptions

Explicit release/continue authorises recovery work. Owner merge approval is still required on this concrete new PR, with task done carried on the same PR.

## Required Follow-Up

Wait for exact PR CI, obtain acceptance, finalise/merge this PR and integrate the repair to main. Dispatch image.yml from main for v0.11.0; verify all four public GHCR manifests/digests; publish Draft GitHub Release and update the release PR receipt.

## QA Decision

Local acceptance passes with documented remote/manual gates. Keep task in review until owner acceptance and exact PR CI; no completed Docker/GitHub release claim yet.

## Exact Reviewed-Head CI And Finalisation

PR #296 head 12c0ee08be2d776ebebe0fbf9e6f5e88e389929b passes 22 checks and one expected publication skip. CI 41739423358, canonical full Factory 41739423354 and CLI 41739423356 pass. Image 41739423491 passes source resolution, all smoke/CLI tests, official archive SHA256, actual Linux Trivy 0.69.3 execution and both required scans. This closes the earlier Linux/scanner/full-profile validation gaps.

Owner's explicit release and continuation instruction authorises this necessary bounded operational recovery/integration for the same 0.11.0 source, with no new product scope/credentials/targets. Separate owner review of the diff is not claimed; earlier pending-extra-acceptance text was an assistant assumption. Task is done on the same one-commit PR after advisory review/QA. Final metadata amendment preserves the validated workflow; fresh final-head CI gates merge. Main integration, manual recovery of immutable v0.11.0 and four public manifest/digest checks must still succeed before the Draft GitHub Release is published. No tag/package rewrite.

## Final CI Failure And Verified Test Synchronisation

Head 04dba764 image/scanner gates pass, but CI 41740910992 E2E shard 3 job 126281895395 fails app key rotation en/dark: #chat-settings disappeared after the second Escape. This repeats the previously observed vi/dark timing failure. The test acted on modal visibility before its focus scope was ready. The fix waits for the nested modal to own focus before each Escape and for the second secret dialog to close. Existing key counts, disabled state, exact-name revocation, secrecy and parent-visible expectations are retained. No product code, timeout, retry or screenshot policy changes.

Targeted local command runs chat-app-keys.spec.ts with --repeat-each=3 --workers=1 against unique API/UI/mock/SMTP ports 18390/15390/18391/18392, temporary DB and system Chrome; all 12 en/vi light/dark cases pass in 1.2 minutes. Log /private/tmp/superstep-0239-app-keys-repeat.log; output artifacts stay outside Git. Final amended-head CI must pass; the earlier failing head is not claimed green.

Public npm tarballs also pass an independent Node consumer smoke at /private/tmp/superstep-0.11.0-published-consumer, using extracted actual registry SDK/React packages rather than workspace @superstep symlinks. ESM/CJS edit/regenerate/prepareRegenerate, store.regenerate, React Chat/Provider/MessageList/Composer/useChat and mintChatToken imports pass.

- Final focus guard polls a boolean for activeElement inside the secret modal; failed expectations cannot dump the secret input DOM/value. Final guard passes the same 12 isolated en/vi light/dark cases in 59.0 seconds (superstep-0239-app-keys-safe-repeat.log). Existing product behaviour, secret capture policy and all rotation/revocation assertions remain unchanged; final amended-head CI gates merge.
