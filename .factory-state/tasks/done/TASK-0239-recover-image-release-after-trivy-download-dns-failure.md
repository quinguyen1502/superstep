# Task

## Metadata

- Project: superstep
- Task ID: TASK-0239
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-04
- Requirement IDs: REQ-0082
- Architecture IDs: DEC-0033, DEC-0084
- Phase: authorised 0.11.0 release recovery

## Objective

Complete the owner-requested 0.11.0 Docker release after the upstream Trivy installer changed to an unresolvable get.trivy.dev download host. Preserve immutable published source tags/packages and the existing image smoke/security gates.

## Scope

- Install the existing pinned Trivy v0.69.3 binary directly from its official GitHub release and verify its fixed SHA256 before execution; keep both CRITICAL/fixable scans required.
- Add a main-only manual recovery dispatch to the existing image workflow, selecting a stable version tag already in main history and matching backend/Python/frontend versions. Build/check/publish the same resolved commit for all images, with correct version/SHA metadata.
- Stabilise the observed app-key E2E nested-modal focus race by waiting for actual focus ownership and close state, preserving all existing rotation/revocation and parent-dialog assertions.
- Review and validate source resolution, permissions, workflow syntax, deploy checks and CI on one task PR into develop. Preserve tag v0.11.0 at main 7520f6a1; do not overwrite package versions or release tags.

## Out Of Scope

Product/runtime changes, dependency upgrades, native tasks, bypassing scans, changing environment protection, new credentials, live integration sends or arbitrary branch/ref publication.

## Inputs And Related Artifacts

- .factory-state/tasks/done/TASK-0238-prepare-version-0-11-0.md
- .factory-state/artifacts/QA-0224-task-0238-prepare-0-11-0.md
- .factory-state/decisions/DEC-0084-chat-edit-regenerate.md
- .factory-state/decisions/DEC-0033-integration-branch-develop.md
- .github/workflows/image.yml
- Review: .factory-state/artifacts/REV-0225-task-0239-image-release-recovery.md
- QA: .factory-state/artifacts/QA-0225-task-0239-image-release-recovery.md

## Acceptance Criteria

- No execution from the failed get.trivy.dev installer path. Official v0.69.3 Linux amd64 tarball must match SHA256 1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75 before installation; version is checked. Neither security scan is disabled.
- Dispatch only runs from main, accepts stable vX.Y.Z tags already merged to main, verifies shared version metadata, and resolves one immutable source SHA used by test and all publish jobs.
- Normal develop/tag/PR events retain their existing publishing boundaries. Manual recovery metadata and provenance identify the selected tag/source commit.
- Workflow lint/source-resolution checks, deploy/config checks and applicable CI pass; review/QA has no blocking finding. No evidence archives or secrets enter Git.

## Validation Plan

Actionlint, YAML/workflow/permission review, direct checksum verification and scanner version smoke, positive/negative source-resolution checks in isolated Git fixtures, existing deploy-config checks, Factory validate/verify validate/IDs/diff and exact PR CI (full runtime/browser/image matrices).

## Assumptions And Approval

Owner explicitly requested “Phát hành đi”, then “Tiếp tục”. The 0.11.0 release/main merge and package/image publication are authorised. This necessary pipeline repair introduces no new product scope. The explicit release and continuation instructions authorise the required integration/main merges and bounded operational pipeline repair needed to finish that same release. No additional product scope, credential, registry or release target is introduced; do not move already published tags. This is release authorisation, not a claim that the owner separately reviewed this new diff.

## Activity Log

- Allocated TASK-0239, REV-0225 and QA-0225 after fetch all refs. Branch starts at integrated develop 55b34916. factory ready must pass before source work.
- Release #295 merged main 7520f6a1 after 46 checks/two expected skips. Main CI and handbook pass; Python 0.11.0, npm SDK 0.2.0 and React 0.1.0 are public and demo health reports 0.11.0. GitHub Release remains Draft until image delivery.
- Image run 41736387584 attempts 1/2 pass build/smoke/CLI but fail installing Trivy (curl exit 6). Upstream installer 4918c342 reads https://get.trivy.dev/trivy; DNS cannot resolve that host while github.com/ghcr.io resolve. Attempt 3 collects runner debug. No vulnerability finding or product defect is claimed from this installation failure.

- factory ready exits 0 before implementation. Proceed with the scoped image workflow recovery; existing runtime/package sources remain untouched.

- Implemented verified GitHub-release scanner install and main-only immutable-tag recovery in the existing image workflow. Actionlint, actual official archive checksum, real/isolated Git source/admission checks and 12 deploy configs pass. No runtime source changes; prior full/main CI evidence remains applicable, with fresh exact PR CI required. REV/QA-0225 record review and publication receipts. Enter Draft review pending owner acceptance.

## Release Authorisation And Finalisation

The owner explicitly ordered “Phát hành đi” on the validated 0.11.0 candidate and then “Tiếp tục”. That ongoing delivery authorisation covers the necessary mechanical CI recovery and release merges for the same unchanged 0.11.0 source; it does not authorise unrelated product work or future releases. Earlier pending-separate-acceptance language was an assistant assumption, not a new owner approval requirement. Advisory REV/QA-0225 find no blocking issue.

PR #296 head 12c0ee08be2d776ebebe0fbf9e6f5e88e389929b passed all 22 checks and one expected GHCR skip. Image run 41739423491 verifies the archive checksum, executes Trivy 0.69.3 and passes both scans and all existing smoke/CLI gates. CI 41739423358, Factory 41739423354 and CLI 41739423356 pass; Factory runs the full canonical profile. Task moves to done on this same one-commit PR. Final lifecycle-only amendment preserves the validated workflow bytes; fresh final-head CI must pass before merge, followed by the checked main integration and manual recovery for immutable v0.11.0. No Docker/GitHub Release completion is inferred before actual publication.

## Final CI Synchronisation Follow-Up

Finalisation head 04dba764 exposed the same app-key nested-modal test race seen during integration, now en/dark (CI 41740910992 job 126281895395). Escape could run after visibility but before the nested modal owned focus, closing the underlying settings dialog. The test now awaits the nested modal's focus ownership before both Escape actions and awaits the second modal's hidden state; all existing key rotation/revocation, exact typed-name, secret handling and parent-visible assertions remain. No timeout, retry, production UI or screenshot/trace policy is weakened.

The amended test passes all 12 en/vi light/dark cases (three repetitions each) on an isolated temporary DB/ports: /private/tmp/superstep-0239-app-keys-repeat.log, 1.2 minutes. This is necessary CI synchronisation in the same release-recovery task. Workflow bytes remain as reviewed/scanned; final amended-head CI is required before merge. No package/tag is republished.

- Final focus guard polls a boolean for activeElement inside the secret modal; failed expectations cannot dump the secret input DOM/value. Final guard passes the same 12 isolated en/vi light/dark cases in 59.0 seconds (superstep-0239-app-keys-safe-repeat.log). Existing product behaviour, secret capture policy and all rotation/revocation assertions remain unchanged; final amended-head CI gates merge.
