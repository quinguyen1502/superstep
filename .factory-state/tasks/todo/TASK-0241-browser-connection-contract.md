# Task

## Metadata

- Project: superstep
- Task ID: TASK-0241
- Title: Browser contracts, whitelist, toggles and scoped connection metadata
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: M (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Browser contracts, required origin whitelist, safety toggles and scoped connection metadata, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Specify versioned bounded worker commands, tool schemas (nine operations including upload/download/evaluate_js), trusted run/conversation/session context, provider/proxy capabilities (local Playwright and Browserless), required origin whitelist shape and safe result/observation envelopes from ARCH-0002.
- Extend existing managed connection/profile metadata with **mandatory non-empty origin/domain whitelist**, safety toggles (mutating-approval default OFF; allow JS/upload/download; download limits; session idle/max; action/page budget), owner/org CRUD/discovery, encrypted secret handling and feature gating; add SQLAlchemy/Alembic revisions only where needed.
- Resolve exact session transport, proposed idle default (30 minutes), hard max, profile provisioning shape and initial supported proxy protocol/auth matrix in reviewable contract notes. Preserve existing MCP transports and unrelated managed adapters. Document always-on rules (private IP block, untrusted page content, secret redaction, no public Settings, kill-switch) as non-togglable.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, unrestricted host filesystem/shell, live provider/account setup, deployment, release and merge. Upload/download/evaluate JS are in first delivery with the bounds in REQ-0086; interactive profile capture and deferred exports remain out of this task unless listed below.
- Starting implementation under this planning-only request.

## Inputs And Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision proposal: `.factory-state/decisions/DEC-0085-browser-tools.md`.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`; DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081 referenced by the requirement/architecture.
- Dependency artifacts: none; begin only after owner acceptance of the requirement/design/plan.

## Expected Outputs

- Versioned contract, DTO/service/repository changes, migration if needed and contract/auth tests.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- None within PLAN-0006.
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- Connections can be configured/discovered without a single fixed target URL; saving without a non-empty origin whitelist is rejected; proxy is direct, explicit operator default or connection-specific, with credentials kept outside workflow/model metadata.
- Safety toggles persist with documented defaults (mutating approval OFF; allow JS/upload/download off until enabled; idle 30 minutes proposed); always-on rules are not exposed as disable switches.
- Wrong principal/org, invalid schema, unsupported capability and secret edit/keep/remove cases are rejected through the shared envelope/catalog.
- Command/session identity and ordered-call context cannot be supplied or overridden by chat/model arguments; profile origin restrictions and result statuses are explicit.
- A reviewed capability table names what local/Browserless/proxy combinations the next tasks must prove; provisional support is not advertised as verified; Browserless is required for the studio remote gate.

## Validation Plan

- Planned tests/test_browser_connections.py and tests/test_browser_contract.py; regressions tests/test_mcp.py, tests/test_managed_tools.py, tests/test_layers.py, tests/test_api_envelope.py and tests/test_db_migrations.py.
- Validate SQLite/Postgres migration round trips if schema changes; validate schema parity and secret redaction with fake repositories.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0238 → TASK-0241 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0241-browser-connection-contract`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
