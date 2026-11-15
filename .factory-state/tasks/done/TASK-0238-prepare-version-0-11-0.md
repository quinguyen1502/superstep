# Task

## Metadata

- Project: superstep
- Task ID: TASK-0238
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-03
- Requirement IDs: REQ-0082, REQ-0083, REQ-0084, REQ-0085
- Design IDs: none (release preparation)
- Architecture IDs: DEC-0084, DEC-0077, DEC-0078, DEC-0079
- Phase: shared 0.11.0 release preparation

## Objective

Prepare a concrete, validated 0.11.0 release candidate from integrated develop after TASK-0229/0230, preserving the owner-approved shared Python SDK/CLI/server version and independent TypeScript/React package scheme.

## Scope

### In Scope

- Synchronise server, Python SDK/CLI, frontend/lock metadata and installer pin to 0.11.0.
- Consolidate current release notes and en/vi usage/release compatibility context; preserve historical approvals and release notes.
- Verify package contents and installed-runtime versions, generated schemas, migration/backup preservation from v0.10.2, full declared checks and CI.
- One Draft task PR into develop for owner review of the concrete candidate.

### Out Of Scope

- New product features, native TASK-0227/0228, live provider credentials or n8n import.
- Release/main merge, version tags, registry publication, deployment or live bot cutover; those need explicit release instructions on the validated candidate (DEC-0084).

## Inputs And Related Artifacts

- `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md` (Owner Priority And 0.11.0 Amendment; approved preparation after integration)
- `.factory-state/decisions/DEC-0084-chat-edit-regenerate.md` (Accepted)
- `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- `.factory-state/tasks/done/TASK-0211-version-0-10-2.md` (previous release evidence)
- `.factory-state/tasks/done/TASK-0229-chat-edit-message.md`, `.factory-state/tasks/done/TASK-0230-chat-regenerate-answer.md`
- `.github/workflows/sdk-publish.yml`, `.github/workflows/image.yml`, `.factory-state/tooling/tool-policy.yaml`

- Review: `.factory-state/artifacts/REV-0224-task-0238-prepare-0-11-0.md`
- QA: `.factory-state/artifacts/QA-0224-task-0238-prepare-0-11-0.md`

## Expected Outputs

- Reviewable 0.11.0 source/package candidate and release notes, review/QA records and green exact-head CI; no publication implied.

## Constraints

- Factory ready must pass before source work; generated state belongs in .factory-state, no framework changes.
- No evidence screenshots, archives, wheels, tarballs or credentials in Git. Build/QA outputs go outside the repo.
- API v1 contract version remains independent of application/package versions; public changes stay additive.
- Preserve TypeScript/React independent versions unless actual published-version evidence requires an approved adjustment. Native deferral means REQ-0082 remains Accepted/incomplete.

## Dependencies

- TASK-0229 merged #292 at 42333ffc
- TASK-0230 merged #293 at d2119965

## Acceptance Criteria

- Backend/Python SDK/CLI/frontend and installer runtime pin agree on 0.11.0; lock metadata and packaged/installed versions match.
- Release notes accurately include merged generic integrations and chat phases 1–3/edit/regenerate. Expense content is clearly an example template; native delivery remains deferred.
- Installable SDK wheel/npm artifacts contain required chat/locale/style/type assets and exclude secrets, tests and screenshots; install smoke succeeds from built artifacts.
- Back up a v0.10.2-schema SQLite fixture, upgrade through current migrations and verify preserved history/file data plus backup readability; existing PostgreSQL/image CI passes.
- Full Factory profile, strict en/vi handbook/media, schema checks and all applicable exact-head CI pass; review and QA have no blocking findings.

## Validation Plan

Canonical full tool-policy profile; factory structure/dependency/verification/ID checks; generated-contract checks; wheel/sdist/npm pack and installed CLI/SDK smoke; migration/backup fixture; strict en/vi handbook/media; full CI (SQLite/PostgreSQL/Redis/MinIO, E2E, React 18/19, images).

## Assumptions And Approval

Owner prioritised 0.11.0 and shared versioning, accepted DEC-0084/PLAN-0002 preparation order, then explicitly instructed Merge on #293 after being asked to integrate regeneration and prepare 0.11.0. This authorises preparation of a reviewable candidate; it does not authorise release/tag/publication. No new architecture or dependency is proposed.

## Open Questions

None for preparation. Release publication stays a separate owner action on the validated result.

## Activity Log

- 2026-11-03: Allocated TASK-0238 after git fetch --all --prune and factory ids next TASK --all-refs. Branch factory/task-0238-prepare-0-11-0 starts from merged develop d2119965. TASK-0230 final single-commit f4f52c19 passed 22 checks/two expected skips before the authorised merge. No source changes yet; validate readiness next.

## Handoff Notes

One task/PR; native work remains deferred. Preserve server/Python shared 0.11.0 and independently approved npm schemes. Present the complete validated candidate before asking for any release/publication instruction.

- factory ready exits 0 before source implementation. Proceed with version/pin/release-note preparation and artifact/migration checks; no extra product feature work.

- Final local full profile passes 8/8. Wheel/sdist build and independent install/CLI, npm ESM/CJS/React consumer/assets, actual backend health, version/pin/lock checks, v0.10.2 backup/upgrade/restore and strict en/vi handbook/media all pass. See REV/QA-0224 for local receipts and residual release gates. Enter Draft review; exact-head CI and owner acceptance remain required. No tag/upload/deploy or native work performed.

- Draft PR #294: https://github.com/quinguyen1502/superstep/pull/294. Final version audit also updates the sample host README from its historical current-0.10.2/Unreleased note to the concrete 0.11.0 version scheme. Runtime/package sources are unchanged from the locally validated candidate; final exact-head CI remains required.

## Owner Acceptance And Release Authorisation

The owner explicitly instructed “Release it” after reviewing the 0.11.0 summary and candidate PR #294. This accepts the concrete implementation, authorises merging #294 into develop, the develop-to-main release PR, version tags, GitHub Release and configured PyPI/npm/GHCR publication. This supersedes the earlier preparation-only scope and pending-owner statements; no native delivery or live provider/bot cutover is added.

Reviewed head e8b2112990b8869b83f029e04be2a8440d16fadc passed 22 CI checks with two expected PR-only deployment/publication skips. CI: https://github.com/quinguyen1502/superstep/actions/runs/41665808750; Factory: 41665808411; handbook: 41665808446; image: 41665808202; CLI: 41665808230. Local full 8/8 and package/migration receipts remain valid because finalisation only changes lifecycle records. The task moves to done on the same one-commit PR, with fresh exact-head CI required before merge. Release/tag publication outcomes must be verified separately and reported accurately.
