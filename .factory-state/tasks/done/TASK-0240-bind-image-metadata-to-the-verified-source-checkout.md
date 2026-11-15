# Task

## Metadata

- Project: superstep
- Task ID: TASK-0240
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-04
- Requirement IDs: REQ-0082
- Architecture IDs: DEC-0033, DEC-0084
- Phase: authorised 0.11.0 release recovery

## Objective

Fix the metadata-action detached HEAD failure discovered when publishing the checked TASK-0239 source on develop. Keep the resolved SHA and explicit semver binding, while giving git-context metadata a local symbolic ref at that same commit.

## Scope

- Bind a fixed local branch to the already verified publish checkout before metadata-action; no change to HEAD commit or source files.
- Test the pinned real metadata action for detached failure, develop tags, manual v0.11.0 recovery tags, selected SHA labels and source immutability.
- Review/QA and one task PR into develop; the open release-integration PR #297 then picks up this required fix. Runtime/package versions, published tags, scanner gates and permissions stay unchanged.

## Out Of Scope

New product features, dependency/version changes, tag rewrites, new credentials/registries, relaxed scans/permissions and unrelated implementation.

## Inputs And Related Artifacts

- .factory-state/tasks/done/TASK-0239-recover-image-release-after-trivy-download-dns-failure.md
- .factory-state/artifacts/REV-0225-task-0239-image-release-recovery.md
- .factory-state/artifacts/QA-0225-task-0239-image-release-recovery.md
- .factory-state/decisions/DEC-0033-integration-branch-develop.md
- .factory-state/decisions/DEC-0084-chat-edit-regenerate.md
- .github/workflows/image.yml
- Review: .factory-state/artifacts/REV-0226-task-0240-image-source-metadata.md
- QA: .factory-state/artifacts/QA-0226-task-0240-image-source-metadata.md

## Acceptance Criteria

- git-context metadata succeeds after checkout of the verified SHA, retaining exactly that commit/tree.
- Develop publication emits only develop and selected-source SHA tags. Manual recovery emits v0.11.0-derived version/latest tags and selected-source SHA, with OCI revision identifying the source rather than the newer workflow commit.
- Actual pinned metadata action is exercised locally without registry writes; credentials never appear in output. Existing source validation, main-only dispatch and required smoke/scanner gates remain unchanged.
- Actionlint/Factory/diff/ID checks and exact PR CI pass before the required release merges. Build outputs remain outside Git.

## Validation Plan

Real pinned metadata-action fixture regression, actual Git commit/tree/symbolic-ref assertions, actionlint, existing source-admission fixture/deploy checks, Factory structure/verification/IDs/diff and full exact PR CI. No extra product tests are invented for the local-ref operation.

## Assumptions And Approval

Owner explicitly instructed “Release it” and “Continue”. This necessary mechanical correction is within the same ongoing 0.11.0 release/integration authorisation, with no extra product scope or release target. Review is advisory; no separate human review of this diff is claimed. No publication is marked complete before verified image availability.

## Activity Log

- Allocated TASK-0240/REV-0226/QA-0226 after fetch all refs. Branch starts from develop f2e9fa22 (TASK-0239 integrated after 22 checks/one expected skip).
- Develop Image run 41744133935 publish API job 126294665101 logs “Cannot infer ref from detached HEAD” at metadata-action; login succeeds, no registry image is pushed. Three sibling matrix jobs cancel via fail-fast. Prior PR image checks do not execute publication-only metadata, exposing this validation gap. Keep release PR #297 open; do not merge the failed head.
- factory ready must pass before source work. The fix will retain the selected SHA and explicit semver values and bind a local symbolic ref solely for the git metadata reader.

- factory ready exits 0 before source implementation. Proceed with fixed local-ref metadata binding and real-action validation.

- Actual pinned metadata action regression now reproduces SHA-only detached failure and passes after local-ref binding for develop f2e9fa22 and immutable release 7520f6a1. Exact tags/OCI revisions and unchanged source SHA/tree are asserted; fixture receipts stay outside Git. Advisory REV/QA-0226 find no blocking issue. Source patch is two YAML lines only; normal final CI/publication gates remain.

## Same-PR Release Finalisation

The owner explicitly instructed release and continuation of this concrete 0.11.0 delivery. Local actual-action review/QA passes for the necessary two-line operational correction; that standing authorisation covers its required release merges, with no extra product/version/credential scope. Finalise task done on the existing task PR before merge, preserving the validated workflow bytes. Exact final-head CI remains mandatory and no registry publication is claimed until real workflows and public manifests pass. No separate owner review of this diff is claimed.
