# Task

## Metadata

- Project: superstep
- Task ID: TASK-0255
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-05
- Requirement IDs: REQ-0082, REQ-0083
- Architecture IDs: DEC-0084, DEC-0079
- Phase: owner-authorised 0.11.1 publication

## Objective

Finalise the owner-authorised v0.11.1 release metadata and validated publication handoff for the integrated patch, including React toolkit 0.1.1. After the source PR lands, execute and verify the existing main/tag/GitHub Release/PyPI/npm/GHCR sequence under the same owner instruction.

## Scope

- Finalise the changelog release date and record explicit publication approval.
- One task PR into develop, then the checked develop-to-main release PR.
- Tag integrated main with v0.11.1 and sdk-react-v0.1.1; verify GitHub Release and configured package/image publication.
- Keep TypeScript SDK 0.2.0 unchanged; do not re-publish existing tags.

No product feature, dependency, migration, native SDK, hosted deployment target or live provider/bot cutover is added.

## Inputs And Related Artifacts

- .factory-state/tasks/done/TASK-0254-keep-chat-feedback-actions-aligned-on-mobile.md
- .factory-state/artifacts/REV-0227-task-0254-chat-feedback-mobile-layout.md
- .factory-state/artifacts/QA-0227-task-0254-chat-feedback-mobile-layout.md
- .factory-state/tasks/done/TASK-0238-prepare-version-0-11-0.md
- .factory-state/decisions/DEC-0084-chat-edit-regenerate.md (preserve Accepted status)
- .github/workflows/sdk-publish.yml, .github/workflows/image.yml
- .factory-state/tooling/tool-policy.yaml
- Review: .factory-state/artifacts/REV-0228-task-0255-publish-0-11-1.md
- QA: .factory-state/artifacts/QA-0228-task-0255-publish-0-11-1.md

## Acceptance Criteria

- Application/Python SDK/CLI/frontend/installer metadata agrees on 0.11.1, React on 0.1.1; TypeScript SDK stays 0.2.0. No runtime source change from approved TASK-0254 is introduced.
- Changelog/release notes name final patch contents accurately and preserve the deployment-specific public-chat diagnostic gap and deferred native scope.
- Review/QA, Factory structural/ID/diff checks and all applicable exact-head PR checks pass before authorised merges.
- The prepared publication sequence requires tags to point to integrated main and keeps existing tags immutable.
- The handoff explicitly gates success on verification of PyPI superstep 0.11.1, npm @superstep/react 0.1.1 and configured GHCR app/API/web 0.11.1 images; source Ready/done is not a publication claim.
- GitHub Release notes are prepared accurately and publication remains gated on actual delivery verification. No screenshot/wheel/archive/secret is added to Git.

## Validation Plan

Reuse approved TASK-0254 full local 8/8 and 23 green final-head checks for unchanged runtime. Check release metadata, Factory readiness/structure/IDs and diff, then await fresh configured PR/main checks. Verify tag workflow results and registry metadata/digests, with installed/artifact smoke when needed. Do not bypass failing checks or force-move published tags.

## Owner Approval

After explicitly approving and merging PR #300, the owner instructed “Attach the task and release” in direct response to the untagged/unpublished status. In context this authorises tagging and publishing the v0.11.1 patch, including necessary release metadata/integration/main merges and configured registry workflows. No extra confirmation is required for that sequence. Prior preparation-only restrictions are superseded for this release only.

## Activity Log

- Fresh fetch completed. Allocated TASK-0255 / REV-0228 / QA-0228 with factory ids next --all-refs. Branch starts from integrated develop 9e117dcc. PR #300 head 8dcc452f passed 23 checks/two expected skips and was merged under owner approval. No runtime edits are planned.

- Factory ready exits 0 with this approved todo task before release metadata source edits. Move to doing under task-start; the owner’s release instruction already authorises the full implementation/validation/merge/publication sequence, so no additional start confirmation is required. Source task completion is the checked handoff; external publication is verified separately before claiming the user’s release request complete.

- Release metadata audit passes: shared 0.11.1, React 0.1.1, TypeScript 0.2.0; runtime/workflow trees match integrated TASK-0254 exactly. Advisory REV-0228 finds no source blocker; QA-0228 records handoff pass and external publication gates. Owner release authority covers this bounded finalisation and its merges. Move source task to done on the same one-commit PR; publication itself remains pending and must be verified before reporting the user request complete.
