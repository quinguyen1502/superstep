# Task

## Metadata

- Project: superstep
- Task ID: TASK-0242
- Title: Enforce browser egress and connection-level proxy policy
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Enforce browser egress and connection-level proxy policy, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Implement the effective local browser egress boundary, not only URL-input checks: validated resolution/connection for navigations, redirects and page-generated requests.
- Apply explicit direct/default/custom proxy policy with encrypted auth; keep one route for a live session, validate endpoint and destination resolution, and refuse unsupported protocol/auth or remote-DNS enforcement.
- Document/prove how browser networking, WebSocket/service-worker paths and a selected upstream proxy cannot escape the policy; no broad private-network flag derived from runtime arguments.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, arbitrary script/files, live provider/account setup, deployment, release and merge.

## Inputs And Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision proposal: `.factory-state/decisions/DEC-0085-browser-tools.md`.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`; DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081 referenced by the requirement/architecture.
- Dependency artifact: `.factory-state/tasks/review/TASK-0241-browser-connection-contract.md`.

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

- Controlled browser fixtures demonstrate denial of private/loopback/link-local/metadata destinations through navigation, redirects, subresources and proxy-resolved hosts, including DNS changes.
- All allowed browser traffic follows the selected route; proxy failure cannot fall back to direct and credentials are not logged.
- Policy checks cover actual connection/resolution at the egress boundary. Unsupported routes fail before browser use; checking only the MCP endpoint or page.goto is insufficient.
- Production and narrow fixture-only network policies are separate; a chat URL cannot activate the fixture exception.

## Validation Plan

- Planned tests/test_browser_network_policy.py and a controlled DNS/proxy/browser fixture suite; regressions shared net/HTTP/MCP tests identified from the current tree at implementation.
- Run the real isolated Chromium egress suite with hostile redirect/subresource/proxy cases; record packet/proxy evidence with synthetic targets and no live secrets.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised the chain and selected local Docker on 2026-11-05.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner start accepted; merge remains unapproved.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0239 → TASK-0242 before publication after a fresh all-ref allocation; owner authorised commit/push only.

## Handoff Notes

- Future branch: `factory/task-0242-browser-egress-proxy-policy`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.

- 2026-11-05: Owner instructed proceeding with PLAN-0006 and selected local Docker. Explicit stack on TASK-0241 commit ea29f822 (review/QA REV-0229 / QA-0229, not merged). The branch `factory/task-0242-browser-egress-proxy-policy` carries the published planning package and TASK-0241; do not merge independently of prerequisites. Scope remains one reviewable egress gateway + isolated adversarial fixture delivery; no product browser runtime activation.

- 2026-11-05: `factory ready` passed before source edits. TASK-0241 Draft PR #303 is the declared stack prerequisite. Task-start complete; implementing effective egress gateway and disposable browser fixture, with product runtime still disabled.

- 2026-11-05: Implemented guarded Unix-socket gateway, all-answer public-IP policy, pinned numeric direct/proxy routes, explicit operator proxy approvals/default, bounded HTTP framing/concurrency/time/bytes and no fallback. Shared URL syntax extracted without changing metadata behavior. `docs/browser-egress.md` documents topology and limits.
- 2026-11-05: Final real Chromium proof passed direct/custom/operator-default (13/14/14 denials, 14 numeric proxy CONNECTs), including secure-origin SW blocking, redirect/subresource/DNS/proxy failure cases and no direct network. 179 targeted backend regressions passed; REV-0230 / QA-0230 recorded. Product runtime remains unavailable; no merge/release/deployment.
