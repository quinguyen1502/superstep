# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0223
- Task ID: TASK-0230
- QA Owner: Codex (advisory)
- Created/Updated: 2026-11-03
- Outcome: local acceptance passes; reviewed source CI passes; final metadata-head CI gates delivery

## Validation Scope

Accepted DEC-0084 regeneration on merged TASK-0229, with shared branch/admission/file/recovery guarantees. References: TASK-0230, REQ-0082, PLAN-0002, DEC-0084 and REV-0223. Native tasks and version/tag/publication work remain outside this delivery.

## Acceptance Criteria Coverage

| Criterion | Result/evidence |
| --- | --- |
| Latest terminal answer only, original preserved | API tests reject older/root/inherited/foreign turns, stale tips and arbitrary input; successful regeneration keeps prefix/source unchanged. Terminal error/cancelled/expired/timeout cases pass. |
| Fresh Human/reviewer interaction | A retained-prefix case asks Human again and saves a new response in a fresh run; the inbox case creates a new reviewer request after the original approval. Waiting sources are refused. |
| Durable admission, ownership and quotas | Shared edit/regenerate parameter matrix covers concurrent preparation/claim, conflicting body/action IDs, tombstones, visitor/app subject/origin isolation, key rotation/revocation/current issuer and daily-cap denial without a run. |
| Independent files and cleanup | DB/fs copies survive source deletion; current root-file policy is rechecked and late source changes clean staged files. Both actions run the same live-S3 parameter case in existing MinIO CI; local S3 cases are skipped. |
| SDK compatibility/recovery | TS revision tests 8/8 pass, including unsupported servers, lost admission, duplicate/no-second-socket and a continued branch with a later Human wait. Python chat tests 52/52 pass across sync/async, including admitted-intent reads after newer messages and unsupported servers. |
| Shared UI and localisation | React tests 20/20 pass, including confirmation/cancel/latest-only/failed-response intent reuse. Studio/cookie-public en/vi browser acceptance passes edit+regenerate, reload and source navigation. React 18/19 each pass toolkit/widget/headless flows with Human/files/identity and no inherited widget events. |
| Contracts/docs/migrations | Generated OpenAPI/socket types include regeneration, flags and optional source_action. Layer/envelope contract tests pass in targeted runs. Strict en/vi handbook and image references pass. Alembic 0054 is exercised by test/bootstrap migration; final PostgreSQL/image CI remains required. |

## Checks Performed

- Combined backend target run: 41 passed / 2 MinIO-only skips in /private/tmp/superstep-0230-backend-target2.log; later final regeneration set (including reviewer and cross-action payload regression) 7 passed in superstep-0230-regenerate-target3.log.
- TypeScript focused revision tests: 8 passed in superstep-0230-sdk-recovery-after.log. Before-fix log superstep-0230-sdk-recovery-before.log reproduces 2 continued-branch recovery failures.
- Python chat tests: 52 passed in superstep-0230-python-chat.log. Shared React tests: 20 passed in superstep-0230-react-tests.log.
- Studio/public en+vi: 2 passed, 36.5s, superstep-0230-main-e2e.log.
- React 19 and 18 host matrices: each passes 3 Node tests and toolkit/widget/headless browser scenarios, superstep-0230-host19.log and superstep-0230-host18.log.
- Handbook builds and media: superstep-0230-handbook-{en,vi,images}.log, all pass.
- The first full profile passed seven commands; backend had 1225 passed/23 skipped and one stale generated AsyncAPI-description failure in test_public_openapi. Canonical generation synchronised it; 25 contract/API/regeneration/layer/envelope tests then pass in superstep-0230-contract-synced.log. The unchanged OpenAPI JSON was already correct. Final full profile passes 8/8 commands in superstep-0230-verify-final.log; canonical verification/latest.yaml is passed. Reviewed source f0474eb7 passes all 22 CI checks with two expected deploy/publication skips. Live MinIO passes all 55 tests, including both actions. Finalisation updates validation/review records only; exact metadata-head CI remains required.

## UX And Accessibility Coverage

Latest-answer labelled action; shared modal title/description and semantic external-effect warning; ordinary confirm/cancel and no editable state/input in regeneration; stable UUID across failed confirmations; source navigation; hidden inherited/older actions even with stale history flags. Theme tokens, en/vi and existing deletion confirmation remain consistent. Inspected light Studio, dark English public chat, dark Vietnamese widget and custom-theme React captures; no images or traces are committed.

## Defects And Test Corrections

- Continued-branch SDK recovery formerly started after newer messages and missed the requested saved run. Before-fix tests fail for both actions; fixed by starting before the reserved run, preserving later history/waiting state without sending execution.
- An initial reviewer test timed out because this module's client has no lifespan worker. It now uses the existing worker-drain helper and the reviewer conversation's actual persisted history, and verifies a fresh inbox request.
- One first combined Human preparation attempt lacked a successful response; diagnostics now assert the whole envelope. Isolated and combined reruns pass without changing admission guards; the later complete backend run passes the Human case (1225 other tests passed; only the independent stale generated description failed). Final full profile/exact-head CI remain delivery gates.

- The generated AsyncAPI field description was stale after broadening it to edit/regenerate; regeneration with the canonical script and a 25-test contract set fixes the check without weakening comparison.

## Evidence

Ignored frontend/test-results outputs; inspected copies /private/tmp/superstep-0230-visual/regenerate-studio-vi.png, regenerate-public-en.png, widget-regenerate-confirm-vi-dark.png and react-regenerate-confirm-en-custom.png. Synthetic data only. Persistent evidence is this record, executable tests and linked exact-head PR checks; screenshots stay outside Git as requested.

## Gaps Or Untested Areas

Local Chrome only; no Safari/Firefox/device/native delivery or real external vendor effect claim. Live S3 and full PostgreSQL matrix are remote CI gates; no assertion is made from local skips. No registry release/publication is performed.

## Residual Risk

Regeneration reruns the current workflow and can repeat API calls/writes/notifications. Intent deduplication prevents duplicate admission, not deliberate repeated actions. Claimed-but-unsaved outcomes are read/reported as interrupted, never replayed. Copies consume storage; expired historical agent context can refuse an old branch. Release preparation must verify migration/backup/version/package contents before 0.11.0 publication.

## Assumptions

The owner approved DEC-0084 and continuing TASK-0230 after #292; the new implementation PR still requires its own owner acceptance and merge approval. Shared/independent package version schemes and native deferral are preserved.

## Required Follow-Up

Finish full verification and exact-head CI (including live MinIO), then present the same Draft PR for owner acceptance. After merge, prepare 0.11.0 separately; no tag or package publication follows automatically.

## QA Decision

Local acceptance passes and reviewed source CI passes all 22 checks. Final metadata-head CI remains a delivery gate. Keep task in review/Draft for owner implementation acceptance; do not mark done or overall REQ-0082 complete.

## Final Source Validation (2026-11-03)

PR #293, source head f0474eb714212f26c502e4c34b939b2e882e8ab8: all 22 CI checks pass, with expected handbook-deploy/image-publication skips. CI run 41652900673 includes live MinIO (55 passed), SQLite/PostgreSQL/Redis, all three full E2E shards and both React hosts; Factory run 41652900672 and handbook run 41652900616 pass. Local final full profile passes 8/8; Factory structure/dependency/verification/ID and diff checks pass. A stale failed verification snapshot was accidentally included in the Draft commit and is now replaced by the actual passed report. This amendment changes delivery records only. No software/merge acceptance by the owner is claimed.

## Owner Implementation And Merge Acceptance (2026-11-03)

Owner explicitly instructed "Merge" on PR #293. Reviewed head 922ea6a840ba68b4fa47450d3e18993ba8ae4a74 passes all 22 checks with two expected deploy/publication skips: CI run 41654796986, Factory verification 41654797066, handbook 41654797008, image 41654797094 and CLI 41654797495. Local full verification passes 8/8. No unresolved blocking finding or QA failure remains. This supersedes earlier pending-owner statements. The move to done is on this same PR in its one task commit, based on latest develop 42333ffc. Finalisation changes records only; source validation is reused and exact final-head CI must pass before the owner-authorised merge. Release preparation follows integration; no release tag, registry publication or native completion is inferred.
