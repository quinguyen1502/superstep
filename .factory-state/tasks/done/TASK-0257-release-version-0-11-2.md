# Task

## Metadata

- Project: superstep
- Task ID: TASK-0257
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-05
- Requirement IDs: owner-authorised 0.11.2 release of TASK-0256
- Architecture IDs: DEC-0033, DEC-0079

## Objective

Prepare and publish the owner-approved 0.11.2 patch after TASK-0256 is integrated, using the existing checked develop/main/tag/registry release process.

## Owner Approval And Dependency

The owner explicitly instructed “Merge and release 0.11.2”. This authorises necessary task/release develop/main merges, immutable version tags, GitHub Release and configured PyPI/npm/GHCR publication. It does not authorise unrelated features, live provider/bot cutover or native delivery.

This task is deliberately **stacked on unmerged TASK-0256 PR #305**, source e1caf171, to prepare metadata while its final CI runs. The branch is factory/task-0257-release-0-11-2; release integration is blocked until #305 merges. Verify the release-only diff against integrated develop and rebase if it introduces changes; an integration merge of the identical e1caf171 tree needs no source rewrite. Do not claim publication from source status alone.

## Acceptance Criteria

- Shared server/frontend/Python SDK/CLI/installer metadata and release tests agree on 0.11.2; React toolkit/pin/lock agree on 0.1.2 for its shared UI fixes. TypeScript SDK stays 0.2.0 and its existing tag is not republished.
- Changelog and release notes accurately describe editor/quick actions/realtime history fixes, no migration/dependency and display-only socket snapshot limits. Keep deferred native scope and manual-device gaps explicit.
- Release metadata only: runtime, workflow, schema, dependency selections and migrations remain identical to approved TASK-0256.
- Factory readiness passes before source edits. Version/lock consistency, SDK release/install tests, build/lint/unit/pack checks and structural/ID checks pass; full exact-head remote checks gate develop/main merges.
- Existing tags remain immutable. New v0.11.2 and sdk-react-v0.1.2 tags point to the checked integrated main commit.
- Keep GitHub Release Draft until actual PyPI superstep 0.11.2, npm @superstep/react 0.1.2 and all four configured GHCR image publications are verified. Record receipts on GitHub Release/Actions, not evidence binaries in Git.

## Inputs And Related Artifacts

- vision.md, project.md, roadmap.md, project-specs.md (preserve approval statuses)
- .factory-state/tasks/done/TASK-0256-editor-usability-followups.md; PR #305
- .factory-state/artifacts/REV-0231-task-0256-editor-usability-followups.md
- .factory-state/artifacts/QA-0231-task-0256-editor-usability-followups.md
- .factory-state/tasks/done/TASK-0255-publish-version-0-11-1.md (prior release process)
- .factory-state/decisions/DEC-0033-integration-branch-develop.md
- .github/workflows/sdk-publish.yml, .github/workflows/image.yml
- .factory-state/tooling/tool-policy.yaml
- .factory-state/artifacts/REV-0232-task-0257-release-0-11-2.md
- .factory-state/artifacts/QA-0232-task-0257-release-0-11-2.md

## Validation Plan

Reuse unchanged TASK-0256 runtime full 8/8 (finish rerun backend 452.87s) and its reviewed-head remote CI; assert runtime/workflow/migration trees remain identical. Run exact root build/lint/test and Python SDK tests, pack/build smoke, metadata/lock/version guards, Factory structure/IDs/diff. Fresh source and main CI execute all configured full checks again before authorised merges. Verify actual new-tag package/image workflows, registry versions/digests and release state before reporting completion.

## Activity Log

- Release-only metadata audit/build/lint/280 npm units, Python SDK 229 passed / 8 skipped, React pack dry-run and Python sdist→wheel build pass. Runtime/workflow/schema/dependency-selection trees match approved TASK-0256. REV-0232 approves and QA-0232 passes the source handoff with mandatory fresh CI and publication gates. Under the explicit owner release instruction, move source task to done on this same release PR; full additional Factory run and remote checks still gate integration, registry receipts gate the actual publication claim. Do not bypass failed checks.
- Factory ready exits 0 with this approved todo before source edits. Move to doing; context is release metadata and verified publication only, dependent on #305. No product source has changed at task-start. Next: align versions/pin/lock/release tests and notes, then validate and open the release-only PR. Full owner release instruction already authorises continuation beyond task-start.
- Fresh fetch and factory ids next TASK REV QA --all-refs allocated TASK-0257 / REV-0232 / QA-0232. Original 0.11.2/PyPI and React 0.1.2/npm versions/tags do not exist. Create approved todo and run factory ready before release source edits. The owner's full release instruction authorises the subsequent preparation, verification and publication steps without another start confirmation, as in TASK-0255.
