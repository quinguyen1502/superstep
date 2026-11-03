# Review

## Metadata

- Project: superstep
- Review ID: REV-0224
- Task ID: TASK-0238
- Reviewer: Codex (advisory)
- Created/Updated: 2026-11-03
- Outcome: no blocking findings; local full verification/acceptance pass; exact-head CI gates delivery

## Review Scope

Diff against merged develop d2119965: shared 0.11.0 backend/Python SDK/CLI/frontend version and lock metadata, installer pin and existing version-specific release-test expectations; consolidated release notes, en/vi chat version guidance and sample-host version guidance. Related Factory records document feature integration and preparation. No product behaviour, dependencies, schema migration code, tag or publication changes.

## Reference Artifacts

TASK-0238; REQ-0082; PLAN-0002 (accepted owner release grouping); accepted DEC-0084; PLAN-0003; TASK-0211 previous release evidence; integrated TASK-0229/0230 and REV/QA-0222/0223; QA-0224; existing sdk-publish/image workflows and tool policy.

## Findings

### Blocking

No blocking findings. Review confirms:

- Backend manifest, Python version module/installed SDK and CLI, frontend manifest/lock metadata and installer default agree on 0.11.0. Existing release tests assert the new explicit target and installer arguments. No runtime dependency graph change is introduced.
- TypeScript SDK 0.2.0 and React 0.1.0 keep the approved independent scheme. Registry inspection returns SDK 0.1.0 and no public React package metadata, so no occupied target is observed. Application/API contract versioning is not conflated.
- Release notes cover actual integrated chat API/auth/SDK/toolkit/widget/edit/regenerate, generic tools/events/model fallback and prior fixes. Expense content is explicitly a portable example, not a new app module. Native tasks stay deferred and overall REQ-0082 stays incomplete. Historical 0.10.2-and-earlier changelog bytes are preserved.
- Python wheel builds from the sdist, contains chat/types/locale/changelog assets, imports from an independent install target and reports CLI 0.11.0. npm tarballs import as standalone artifacts with ESM/CJS chat and React exports, styles and both locales, without workspace SDK/React fallbacks.
- Synthetic schema-0049 data is backed up, upgraded to 0054 twice and restored/upgraded from the backup. Original history, attachment bytes and rating survive; new lineage defaults are valid and the original backup remains readable.

### Non-Blocking

Release readiness does not complete native work or validate real provider credentials/live cutover. Existing revision/tool semantics can repeat deliberate actions, use extra branch storage and retain unknown outcomes as non-replayable; docs remain explicit. Release/main merge, tags, registry publication and deployment await explicit owner release instructions on this candidate.

## Standards And Architecture Alignment

Only approved release metadata/docs and existing version assertions change. No backend layer/API/error/I18n architecture changes; no new dependency, migration, UI control/delete/template field or hard-coded colour. Generated schemas remain unchanged and are checked by the full suite. Package outputs and QA fixtures stay outside Git. Existing shared-version and independent-npm decisions are preserved.

## Design Alignment

The shipped behaviour is the previously accepted, integrated feature set. English/Vietnamese guidance now states the 0.11.0 minimum for revisions; no interface flow/style changes require new screenshots. Prior edit/regenerate captures remain outside Git.

## Validation Review

Full declared profile passes all eight commands. Strict en/vi handbook/media, metadata/pin/lock checks, wheel/sdist build/install, npm artifact imports/assets and old-schema backup/upgrade/restore pass. See QA-0224 for evidence/digests. Dependency validation passes with the expected manifest-fingerprint warning from version-only changes; editable Python metadata was refreshed and npm dependency versions did not change. Fresh exact-head CI must validate all normal install/image/E2E matrices before acceptance.

## Assumptions

Owner authorised shared 0.11.0 preparation after #292/#293 integration; source is a candidate, not a published release. No registry/tag/deploy action is inferred from the Merge instruction for #293.

## Required Follow-Up

Open one Draft task PR and wait for all exact-head CI. Obtain owner acceptance/merge and a separate explicit instruction before release/main merge or publication. Keep native tasks deferred.

## Review Decision

Advisory approved for QA: no blocking findings; local acceptance passes. Exact-head CI and owner acceptance remain delivery gates.

## Owner Acceptance And Finalisation

Owner “Phát hành đi” accepts PR #294 and explicitly authorises integration/main release merges and configured release tags/publication on this validated candidate. Reviewed e8b2112990b8869b83f029e04be2a8440d16fadc passed all 22 checks plus two expected skips. No blocking findings; advisory approved. TASK-0238 moves to done on the same PR. Lifecycle-only finalisation preserves all validated runtime/package sources; exact rewritten-head CI gates merge. Native scope remains deferred and publication success is not inferred from approval.
