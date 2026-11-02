# Task

## Metadata

- Project: superstep
- Task ID: TASK-0235
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-02
- Requirement IDs: REQ-0084
- Design IDs: DES-0002
- Architecture IDs: DEC-0082

## Objective And Scope

Add a configurable JSON HTTP API adapter through existing managed MCP tools. Fixed base URL/static operation paths, bounded JSON definitions and local schemas, encrypted auth headers, schema-derived arguments, pinned requests, bounded redacted results, durable conservative outcomes, offline dry runs and bilingual settings/docs.

No new canvas node, migrations, OAuth, binary/form uploads, dynamic path/URL/auth arguments, live calls or deployment.

## Related Artifacts

- `.factory-state/artifacts/REQ-0084-managed-http-channel-actions.md`
- `.factory-state/artifacts/DES-0002-managed-http-channel-actions.md`
- `.factory-state/decisions/DEC-0082-managed-http-channel-actions.md`
- `.factory-state/artifacts/PLAN-0004-managed-http-channel-actions.md`
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, existing TASK-0233/REV-0210/QA-0210.
- `.factory-state/artifacts/REV-0212-task-0235-managed-http-api.md`
- `.factory-state/artifacts/QA-0212-task-0235-managed-http-api.md`

## Acceptance Criteria

- Create/edit/discover and actual MCP/Agent calls use fixed reviewed tools with encrypted headers. GET query/JSON write input and response schemas work.
- Invalid URLs/headers/definitions/remote refs are refused; no redirect or runtime target override. Responses have byte/depth bounds and redact credentials.
- Known results replay; pending/failed/unknown outcomes never resend. HTTP 202 is unknown; malformed/oversized/schema-invalid success stays unknown. Dry runs do no external work.
- Existing MCP/managed tools remain compatible. Form labels/help in en/vi, both themes; no hard-coded colours or new delete flow.

## Validation Plan

- Focused HTTP API/security/outcome/permission/MCP regression plus layer/envelope tests with fake HTTP.
- Frontend build/lint/unit, browser configuration/discovery/use with en/vi and light/dark screenshots.
- Full Factory profile, bilingual handbook/media, factory validation/IDs/diff, advisory review and QA.

## Dependencies And Assumptions

- Explicit stack on TASK-0233/#280 at 4aa3a60 under PLAN-0004; not merged. Existing deps/runtimes from project.md and TASK-0233.
- Owner chose HTTP API and approval-channel services, authorising implementation/test delivery. Real external acceptance remains service-specific; documentation must explain response-schema policy.

## Activity Log

- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of every evidence screenshot. Existing review/QA passed; this PR carries TASK-0235 to done with human approval and is squashed to one task commit. All evidence images are removed from the branch; historical screenshot paths in review/QA are intentionally retired while textual checks and handbook images remain. Rebase onto latest develop and final-head integration CI gate merge. No release or live provider cutover authorised.

- 2026-11-02: Final source a267226 passed all eight full checks in an isolated checkout (backend 484.39 s); #282 CI passed (6m39s). Both final handbook builds/media and validation/ID/diff passed. REV-0212/QA-0212 passed locally. Verification-only follow-up; task stays in review pending owner approval.
- 2026-11-02: Implemented static HTTP definitions, encrypted auth and bounded redacted outcomes. Focused 67 passed; final HTTP/MCP/layer/envelope 50 passed. Frontend build/lint/149 tests passed. Browser eight passed, then final four HTTP variants 28.4 s. Review passed provisionally; full profile runs on the committed snapshot before final QA. Move to review for this task's Draft PR.
- 2026-11-02: factory ready exited 0 before source work. Move to doing; implement the owner-authorised scope, then validate/review/QA on the same branch.
- 2026-11-02: Owner-authorised requirement and plan recorded; clean task branch factory/task-0235-managed-http-api created from #280. No implementation source edited before factory ready.

## Handoff Notes

- Branch factory/task-0235-managed-http-api; Draft https://github.com/quinguyen1502/superstep/pull/282 targets factory/task-0233-managed-tools (#280). Retarget/rebase and run integration checks after predecessors merge. Owner approval required before merge.
