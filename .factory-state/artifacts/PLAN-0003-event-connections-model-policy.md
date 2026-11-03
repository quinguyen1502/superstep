# Plan

## Metadata

- Plan ID: PLAN-0003
- Requirement: REQ-0083
- Status: Implementation breakdown of owner's 2026-11-01 request to add the three generic feature groups; merges require separate approval.
- Architecture: DEC-0081
- Design: DES-0001
- Date: 2026-11-01
- Integration branch: develop

## Delivery order

| Task | Scope | Dependencies |
| --- | --- | --- |
| TASK-0231 | LLM primary/fallback model policy, config/trace/export behavior; planning baseline | none |
| TASK-0232 | Authenticated event binding, Telegram metadata and signed JSON events | planning baseline |
| TASK-0233 | Managed tool adapters via existing MCP contract, Telegram/Sheets connections and write outcomes | planning baseline; event context where used |
| TASK-0234 | Expense workflow example, integrated tests and bilingual setup guide | 0231, 0232, 0233 |

One branch/commit/Draft PR per task. The owner asked for the complete feature set, so implementation may continue on explicitly documented stacked task branches while awaiting merge approval. A stacked branch records its parent and PR relationship in its task; final landing rebases onto develop, contains only that task's diff, and waits for all required checks. No branch is merged without explicit human approval. No release/deployment or live bot cutover is implied.

## Design defaults

- Model fallback is opt-in, at most one configured alternate, no silent fallback on permission errors/cancellation, no mixing failed-primary tokens into fallback text.
- Legacy linked-account/command triggers remain unchanged. New event admission is explicit and owner-controlled; mapped metadata is bounded data, not implicit studio authority.
- Connection adapters reuse existing MCP discovery/call and owner-bound ports. Telegram reuses channel secrets; Google starts with service-account auth. No new graph type per service, no new dependency anticipated.
- Unknown non-idempotent external outcomes require reconciliation or an explicit blocked status; ledger reuse is not a claim of external exactly-once delivery.
- No real credentials in templates/tests/logs. Real settings and production cutover happen after review.

## Verification

- Meaningful focused tests for policy, auth, mapping, concurrency, replay, unknown outcomes and compatibility.
- Full Factory profile and validation on each task PR; migration/layer/envelope checks; frontend build/lint/tests, changed-form browser checks and screenshots.
- Mocked complete expense flow; strict en/vi handbook builds and media validation.

## Later

- SDK work from PLAN-0002 remains in backlog and is not started by this plan.
- General OAuth provider onboarding, polling sources, a connector marketplace, native vendor graph nodes, n8n import and expense approvals are not part of this implementation.
