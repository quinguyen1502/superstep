# Task

## Metadata

- Project: superstep
- Task ID: TASK-0242
- Title: Enforce browser egress, whitelist and connection-level proxy policy
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Enforce browser egress, mandatory origin whitelist and connection-level proxy policy, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Implement the effective local browser egress boundary, not only URL-input checks: validated resolution/connection for navigations, redirects and page-generated requests, including **mandatory origin/domain whitelist** denial.
- Apply the same whitelist to Browserless/remote paths in the policy contract (enforcement proof completed with TASK-0244). Empty whitelist is invalid at the connection layer.
- Apply explicit direct/default/custom proxy policy with encrypted auth; keep one route for a live session, validate endpoint and destination resolution, and refuse unsupported protocol/auth or remote-DNS enforcement. No silent fallback to direct.
- Document/prove how browser networking, WebSocket/service-worker paths and a selected upstream proxy cannot escape the policy; always block private/link-local/metadata IPs; no broad private-network flag derived from runtime arguments.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0241-browser-connection-contract.md`.

## Expected Outputs

- Effective egress enforcement, proxy configuration/validation, adversarial fixture evidence and operator contract.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0241 — Browser contracts and scoped connection metadata
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- Controlled browser fixtures demonstrate denial of private/loopback/link-local/metadata destinations and **off-whitelist origins** through navigation, redirects, subresources and proxy-resolved hosts, including DNS changes.
- All allowed browser traffic follows the selected route; proxy failure cannot fall back to direct and credentials are not logged.
- Policy checks cover actual connection/resolution at the egress boundary. Unsupported routes fail before browser use; checking only the MCP endpoint or page.goto is insufficient.
- Production and narrow fixture-only network policies are separate; a chat URL cannot activate the fixture exception or bypass the whitelist.

## Validation Plan

- Planned tests/test_browser_network_policy.py and a controlled DNS/proxy/browser fixture suite; regressions shared net/HTTP/MCP tests identified from the current tree at implementation.
- Run the real isolated Chromium egress suite with hostile redirect/subresource/proxy cases; record packet/proxy evidence with synthetic targets and no live secrets.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0239 → TASK-0242 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0242-browser-egress-proxy-policy`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
