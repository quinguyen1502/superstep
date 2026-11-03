# Task

## Metadata

- Project: superstep
- Task ID: TASK-0236
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-02
- Requirement IDs: REQ-0084
- Design IDs: DES-0002
- Architecture IDs: DEC-0082

## Objective And Scope

Expose Slack, WhatsApp, Email and Microsoft Teams sending actions as managed adapters, using existing approval-channel credentials and fixed destinations. Share authorisation with Telegram, preserve owner/org rules, durable conservative outcomes and offline dry runs. Add bilingual settings/docs and browser evidence. JSON webhook is inbound-only; Telegram/Sheets already exist.

No new graph types, inbound platform expansion, approval-template reuse, service credential provisioning, live sends or deployment.

## Related Artifacts

- `.factory-state/artifacts/REQ-0084-managed-http-channel-actions.md`
- `.factory-state/artifacts/DES-0002-managed-http-channel-actions.md`
- `.factory-state/decisions/DEC-0082-managed-http-channel-actions.md`
- `.factory-state/artifacts/PLAN-0004-managed-http-channel-actions.md`
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, TASK-0233 and TASK-0235.
- `.factory-state/artifacts/REV-0213-task-0236-managed-channel-actions.md`
- `.factory-state/artifacts/QA-0213-task-0236-managed-channel-actions.md`

## Acceptance Criteria

- Existing MCP/Agent discovery and calls send bounded text/subject through the chosen channel to its configured destination; no model-chosen targets or secrets.
- Personal/org/indirect org-channel rules match Telegram. A removed/unavailable channel fails safely at execution.
- Known results replay without another send; uncertain/failed sends are never blindly repeated; dry runs do no network/SMTP work.
- Provider payload/auth/acknowledgement, error/timeout/malformed/partial SMTP outcomes covered with fake providers; existing Telegram/Sheets/MCP/channel tests pass.
- en/vi forms/docs explain WhatsApp service window and submission-vs-delivery semantics. Screenshots in both themes/locales, typed-name deletion unchanged.

## Validation Plan

- Focused channel-action/managed/approval/MCP/layer/envelope tests, frontend build/lint/unit and browser creation/discovery/use/screenshots.
- Full Factory verification, both handbook builds/media, IDs/diff, advisory review and QA.

## Dependencies And Assumptions

- Explicit stack on TASK-0235 under PLAN-0004; record actual parent when starting. Owner explicitly selected the approval-channel registry as the service list.
- No new dependency/migration anticipated. Existing SMTP/pinned HTTP helpers are authoritative.

## Activity Log

- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of every evidence screenshot. Existing review/QA passed; this PR carries TASK-0236 to done with human approval and is squashed to one task commit. All evidence images are removed from the branch; historical screenshot paths in review/QA are intentionally retired while textual checks and handbook images remain. Rebase onto latest develop and final-head integration CI gate merge. No release or live provider cutover authorised.

- 2026-11-02: Full Factory profile passed all eight checks on c3ff1f0 (backend 450.07 s); source CI #283 passed (7m8s). Parent #282 final verification head also green. REV-0213/QA-0213 passed locally; final record-only commit adds no implementation change. Task remains review pending human approval; no merge/deployment/live sends.
- 2026-11-02: Rebased onto TASK-0235 verification follow-up 0f323e8; final source c3ff1f0. Draft #283 targets factory/task-0235-managed-http-api (#282). Full profile running on that committed source; no implementation edits during verification. All-ref allocation advances to REV/QA-0214 and TASK-0237 with this branch owning 0213; IDs against origin/develop remain unique.
- 2026-11-02: Default SMTP-off browser regression ten passed (1.5m), including session/notification expectations; explicit SMTP-on fixture four passed (1.4m). Final handbook en/vi/media and validation/ID/diff passed. Rebase onto TASK-0235 verification-only follow-up before full profile; no source dependency on expense example #281.
- 2026-11-02: Implemented channel actions and shared authorisation/quota/Message-ID policies. Backend combined 135 passed; final relevant 66 passed. Frontend build/lint/149 tests passed. Combined browser 13 passed, final SMTP-on four passed (16 adapter workflows); 16 new screenshots. Advisory review passed; full/default fixture checks pending. Move to review for this task's Draft PR; owner approval not inferred.
- 2026-11-02: factory ready exited 0 on clean dedicated branch before source edits. Explicit parent TASK-0235/#282 at a267226; that task's full verification runs in an isolated checkout. Begin existing-channel actions, using the same shared owner/org admission as Telegram.
- 2026-11-02: Planned from owner clarification: use services in approval channels. Implementation follows TASK-0235 in a separate branch/Draft PR; no merge approval inferred.

## Handoff Notes

- Branch factory/task-0236-managed-channel-actions; Draft https://github.com/quinguyen1502/superstep/pull/283, parent #282 at 0f323e8. Land after #278 → #279 → #280 → #282, retarget/rebase onto develop and run integration matrices. Expense example #281 is independent. Owner approval required before merge.
