# Review

## Metadata

- Project: superstep
- Review ID: REV-0210
- Task ID: TASK-0233
- Reviewer: Codex self-review (advisory; owner review pending)
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: approved for QA

## Review Scope

Own diff above TASK-0232: managed adapter/settings and operation ledger migration 0052, Telegram/Sheets service adapters, MCP discovery/call/ports, normal MCP effect ledger/fencing, export refusal, configuration/operation UI and bilingual documentation.

## Reference Artifacts

- REQ-0083, DES-0001, DEC-0081, PLAN-0003, TASK-0233.
- docs/backend-architecture.md and docs/ui-conventions.md.

## Findings

### Blocking

- No blocking implementation findings. Final full profile remains required before Ready/completion.

### Non-Blocking

- Service-account auth is the initial Google path; end-user OAuth is not included.
- Sheets reserves an extra operation-id column and scans up to 100,000 rows. Operators must retain that column and use a new tab before the bound.
- Pending/unknown writes are deliberately conservative: even a crash before sending can stay blocked. A missing lookup result never authorises a second append. Telegram cannot reconcile by operation key.
- Standalone exports explicitly reject managed references, including Agent slots/child graphs, rather than dropping operation tracking.

## Standards And Architecture Alignment

Service adapters implement vendor behavior; engine ports remain vendor-neutral. SQLAlchemy repository stores intent atomically before external calls; migration covers every schema addition. Secrets use existing encryption. Fixed targets, schemas and runtime owner/org admission prevent model-selected arbitrary destinations. A private MCP connection cannot bypass the runner's org-channel restriction. SSRF pinning and configured private-address override are shared with MCP. Pending/unknown outcomes only allow read-only reconciliation; confirmed results cannot be overwritten by later uncertain outcomes.

## Design Alignment

Existing Settings MCP form/card and node/Agent tool selectors reused; configuration metadata drives fields. shadcn/theme/locales and shared typed-name deletion retained. External operation key is visible for manual checks. Screenshots and browser coverage include both locales/themes; no canvas node type added.

## Validation Review

Focused managed/layers/envelope/migration suite: 28 passed. Prior MCP/effects/Agent regression: 52 passed, one optional skip. Final frontend build/lint and 149 unit tests passed; five final Playwright tests passed in 47.2 s, including existing stdio MCP. Both handbook builds/media checks passed. Final full profile will run on an isolated committed checkout before completion.

## Assumptions

- No live provider calls or real service credentials. Browser Google creation/discovery is offline; browser Telegram uses a local fake API; Google HTTP/auth/outcome tests mock the transport and validate signed JWTs.

## Required Follow-Up

- Complete final full verification, owner review on the same Draft PR, and TASK-0234 expense integration.

## Review Decision

Approved for QA; final full profile passed all eight checks on isolated d1f9eb4. Advisory only, owner approval pending on Draft PR #280.


## Landing Approval

Owner approved implementation and merge of #280 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
