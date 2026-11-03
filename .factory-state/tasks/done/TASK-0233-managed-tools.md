# Task

## Metadata

- Project: superstep
- Task ID: TASK-0233
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Expose managed service actions through the existing MCP tool contract, with Telegram and Google Sheets adapters and explicit write outcomes.

## Scope

### In Scope

- Small service-side adapter registry with schema discovery/call; existing MCP nodes and Agent slots consume the same tool contract, with no vendor-specific graph types.
- Telegram actions reference existing channel secrets; Google Sheets service-account auth uses encrypted connection secrets and existing cryptography/PyJWT/httpx dependencies.
- Managed connection configuration UI, argument validation and scope enforcement.
- Stable operation ids, confirmed/failed/unknown outcomes and reconciliation for Sheets; no blind retry of uncertain non-idempotent effects. Reuse existing effect ledger/queue where applicable.
- Migrations, translated errors/docs and tests.

### Out Of Scope

- General OAuth marketplace, arbitrary plugins, a full Sheets UI, automatic live credential setup or real external writes.

## Inputs

- REQ-0083, DEC-0081 and existing MCP/Channel services.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`

## Expected Outputs

- Managed connection adapters/API/UI, durable outcome semantics and one tested Draft PR with review/QA.

## Constraints

- No new dependency anticipated. All vendor network/auth logic stays outside the graph compiler. Encrypted owner-bound credentials; tests mock outbound APIs. Never claim external exactly-once behavior without endpoint support.

## Dependencies

- Planning baseline TASK-0231 and any event context used from TASK-0232; explicitly stack if those PRs are not merged, per PLAN-0003.

## Acceptance Criteria

- Existing MCP and Agent tool selection discover and call managed adapters with validated arguments and owner/org access checks; secrets never enter workflow JSON or tool metadata.
- Telegram actions use the selected existing channel; Sheets writes map values and return row/result metadata through the generic tool interface.
- Known completed operations are reused; uncertain writes are reconciled or blocked from blind repetition, including timeout/crash tests. Test-mode behavior cannot send real messages or append rows.
- Existing MCP HTTP/stdio behavior remains compatible. Delete uses typed-name confirmation; en/vi UI/docs and screenshots included.

## Validation Plan

- Focused adapter/auth/permission/outcome/Agent/MCP tests, migration/layer/envelope tests, frontend checks and browser regression.
- Full Factory verification, validation, IDs and diff check.

## Assumptions

- Service-account auth for a shared sheet is the initial Google connection; provider-specific end-user OAuth remains a future adapter.

## Open Questions

- None blocking local implementation; live setup waits for review.

## Activity Log

- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of every evidence screenshot. Existing review/QA passed; this PR carries TASK-0233 to done with human approval and is squashed to one task commit. All evidence images are removed from the branch; historical screenshot paths in review/QA are intentionally retired while textual checks and handbook images remain. Rebase onto latest develop and final-head integration CI gate merge. No release or live provider cutover authorised.

- 2026-11-02: CI exposed shared-IP state in the existing public-chat rate-limit test. Isolated its limiter with monkeypatch (no application change); public-chat/user-token regression 35 passed. Re-run CI on this same PR; owner approval remains pending.
- 2026-11-02: Full Factory profile passed all eight checks on isolated d1f9eb4 (backend 460.68 s), after combined-order regression passed 31 tests. Initial full-run failure was a permission-test fixture leaving a synthetic org-visible MCP server; cleanup now restores scope in finally. Draft PR #280 is stacked on #279. QA-0210 passed; owner approval pending. No implementation source changed after the final verification. TASK-0234 continues on the documented stack.
- 2026-11-01: Before first push, rebased the task onto the parent's QA-complete 83a6ff8 (#279); only roadmap lifecycle wording conflicted and was combined. Parent's source is identical to the previously verified event implementation. Full verification will use this final rebased commit in its own checkout.
- 2026-11-01: Implementation and advisory review/QA recorded in REV-0210/QA-0210. Migration 0052 adds managed settings and durable operation intents. Final focused managed/layer/envelope/migration 28 passed; MCP/effects/Agent regression 52 passed (one optional skip); frontend build/lint and 149 tests passed; five final browser tests passed (47.2 s), twelve screenshots; bilingual handbook/media checks passed. Full profile will run on an isolated committed snapshot while TASK-0234 proceeds. Standalone exports explicitly refuse managed connections. Read-only reconciliation is bounded to 100,000 sheet rows; Telegram unknown sends stay blocked. Owner merge approval pending.
- 2026-11-01: Explicit stack on TASK-0232 at 6b9657b (parent branch factory/task-0232-event-bindings), above #278 per PLAN-0003. TASK-0232 final full check runs in an isolated checkout to keep its evidence independent. Working tree clean at branch creation. Reuse MCP transport/discovery/argument forms and owner-bound ports; add managed adapter/settings columns plus an operation ledger migration. Telegram uses a selected existing channel, scoped to a fixed chat; Sheets uses a fixed spreadsheet/tab with data columns plus an operation-id column. Pending/unknown writes never auto-repeat; Sheets can reconcile by that operation id, Telegram remains explicitly blocked when outcome is unknown. No live credentials or external writes in tests.
- 2026-11-01: Planned under owner-authorised REQ-0083.

## Handoff Notes

- Branch `factory/task-0233-managed-tools`; record actual base/stack before implementation.
