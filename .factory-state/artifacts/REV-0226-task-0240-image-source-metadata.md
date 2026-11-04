# Review

## Metadata

- Project: superstep
- Review ID: REV-0226
- Task ID: TASK-0240
- Reviewer: Codex (advisory)
- Created/Updated: 2026-11-04
- Outcome: no blocking findings; approved for QA

## Review Scope

Two YAML lines bind a fixed local image-source branch to the already selected publish checkout before git-context metadata. No checkout SHA, source file, scanner, permission, package version, release tag or publishing policy changes.

## Reference Artifacts

TASK-0240, TASK-0239/REV-0225/QA-0225, accepted DEC-0033/DEC-0084, release integration #297.

## Findings

### Blocking

No blocking source findings. Old develop publish fails at metadata inference before pushing; the source-bound local ref fixes the observed failure without substituting the workflow commit SHA.

### Non-Blocking

The branch is local to a fresh ubuntu-latest publication job. Real GitHub publisher execution remains an exact-delivery gate after integration; dry metadata checks perform no registry writes.

## Standards And Architecture Alignment

Smallest local-ref fix in the existing workflow. Source validation and main-only dispatch remain central; explicit semver values and git SHA context are retained. Default read-only permissions and publish-only package write remain unchanged. No API/UI/backend/dependency/framework changes or generated binary/evidence files in Git.

## Design Alignment

No user-facing change; runtime/packages and immutable v0.11.0 source remain unchanged.

## Validation Review

The actual pinned metadata-action bundle is exercised against shallow SHA-only Git fixtures matching actions/checkout. Detached HEAD without refs reproduces the error. Creating image-source succeeds for develop and manual v0.11.0 cases; exact tags, OCI revision and unchanged commit/tree are asserted. This directly covers the publication-only path missed by the earlier PR smoke checks. See QA-0226.

## Assumptions

Explicit owner release/continue authorises this necessary operational correction and required integration/main merges for the same 0.11.0 release. No separate human review of this diff is claimed or future release/credential scope added.

## Required Follow-Up

Run exact final-head CI, carry done on the same task PR, merge into develop, then finish the existing #297 main integration. Verify real develop publication and immutable-tag recovery before publishing the Draft GitHub Release.

## Review Decision

Advisory approved for QA; no blocking implementation finding. Actual publication must still be verified.

## Release Finalisation

The actual pinned-action regression and local scope/security review pass. Task moves to done on the same task PR under the owner's existing explicit release/continue authorisation for this necessary operational repair. Final lifecycle-only amendment preserves both workflow lines as tested; exact final-head checks must pass before merge. No separate human review or successful registry publication is inferred. Main integration and verified actual image delivery remain required.
