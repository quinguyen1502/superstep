# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0226
- Task ID: TASK-0240
- QA Owner: Codex (advisory)
- Created/Updated: 2026-11-04
- Outcome: real-action local regression passes; exact final-head CI/publication remain gates

## Validation Scope

Pinned docker/metadata-action dc802804100637a589fabce1cb79ff13a1411302 with a shallow SHA-only checkout and the fixed local symbolic ref. References: TASK-0240, REV-0226, TASK-0239 and release #295/#297.

## Acceptance Criteria Coverage

| Criterion | Result/evidence |
| --- | --- |
| Observed failure reproduced | Official pinned action entrypoint dist/index.cjs runs against a shallow checkout with no branch/tag refs, as on the publisher runner. The original context fails with Cannot infer ref from detached HEAD. A full clone can infer a ref and is not a sufficient regression fixture. |
| Develop metadata | After git switch --create image-source at f2e9fa22ccc1192911f248a82a2b36e7eff85641, the actual action emits only develop and sha-f2e9fa2 tags; OCI revision equals that source SHA. |
| Immutable release recovery | At original v0.11.0 source 7520f6a1997247aec9d163f83ef2a43c9dc9d6f0, the action emits 0.11.0, 0.11, latest and sha-7520f6a, with that exact OCI revision. No major-0 or develop tag appears. A deliberately different simulated workflow SHA is never substituted. |
| Source/permissions unchanged | HEAD SHA and tree are identical before/after local branch binding; fixture tracked/untracked state remains clean. Existing source validation, checkout pin, main-only dispatch, scanners and permissions are unchanged. No registry login/push occurs in local metadata validation. |
| Syntax/declared continuity | Actionlint passes. Existing source-admission/deploy/Factory/ID/diff checks run before push; exact PR CI runs all applicable canonical/runtime/browser/image checks. Runtime/package sources are identical to the already passing 0.11.0 release/main validation. |

## Checks Performed

- /private/tmp/superstep-0240-check-metadata.py uses the pinned official action bundle and shallow local Git fixtures. It captures output and redacts any credential before writing logs or printing failures. The current GitHub credential is used only for the action's read-only repository metadata request; no secret appears in receipts or Git.
- /private/tmp/superstep-0240-metadata-check/receipt.json records both exact tag sets and source revision. detached.log reproduces the failure; develop.log/release.log show successful real-action output. Fixtures/logs stay outside Git.
- Trivy install/scan and the app-key E2E focus fix from TASK-0239 are unchanged. Actual Trivy/checksum/two scans pass in its CI; the final E2E guard passed 12 local repeated cases and final #296 CI before integration.

## UX And Accessibility Coverage

No product/UI change and no new screenshots. Local Git branch binding only affects publisher metadata, preserving existing images, tags and package versions.

## Defects

The earlier git-context implementation assumed it could infer a ref from SHA-only checkout. Publication-only CI exposed the missing symbolic ref. This two-line fix covers the real failing path with the pinned action, rather than relying only on workflow syntax or PR smoke tests.

## Gaps Or Untested Areas

Local action execution does not push registry images. Exact PR CI, real develop matrix publication, main integration and stable immutable-tag recovery must still succeed. No published image/GitHub Release completion is claimed yet.

## Residual Risk

External GitHub/registry availability remains required. The fixed local branch is created in a fresh hosted publisher checkout; it does not move the source SHA or remote refs. Selected-source semantics, scanner thresholds and immutable published tags remain intact.

## Assumptions

The owner explicitly requested release/continuation, authorising this bounded operational correction and the needed release merges; no unrelated features, credentials or future release targets are authorised.

## Required Follow-Up

Complete exact final-head checks and merge on the same task PR, then finish #297. Verify real publisher metadata/tags, run image.yml from main with release_tag=v0.11.0, inspect all four public manifests/digests and publish the existing Draft GitHub Release.

## QA Decision

Local acceptance passes with advisory review and no blocking source finding. Final CI and actual publication remain mandatory delivery gates.

## Release Finalisation

The actual pinned-action regression and local scope/security review pass. Task moves to done on the same task PR under the owner's existing explicit release/continue authorisation for this necessary operational repair. Final lifecycle-only amendment preserves both workflow lines as tested; exact final-head checks must pass before merge. No separate human review or successful registry publication is inferred. Main integration and verified actual image delivery remain required.
