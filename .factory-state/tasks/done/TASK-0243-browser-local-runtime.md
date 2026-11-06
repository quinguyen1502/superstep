# Task

## Metadata

- Project: superstep
- Task ID: TASK-0243
- Title: Isolated local Playwright runtime and nine bounded browser tools
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: M (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Isolated local Playwright runtime and nine bounded browser tools (including upload, download and evaluate JS), satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Add the isolated non-root Playwright worker image/process and bounded command transport; pin browser/package compatibility and resource limits (including action/page budget hooks).
- Implement navigate, snapshot, click, fill, structured extract, screenshot, **upload**, **download** and **evaluate_js** using the same shared command vocabulary that recipes will call.
- Bound new ops: upload only from authorised attachment/workspace file ids (never arbitrary host paths); download size and allowed types enforced; evaluate_js runs only in page context (no Node/shell) and returns untrusted data that cannot expand whitelist/access or skip approval.
- Attach page/session generation references, explicit cleanup, idle/max expiry and safe failure statuses. Persist only authorised protected screenshot/download references; no shell or unrestricted host-filesystem tools.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0242-browser-egress-proxy-policy.md`.

## Expected Outputs

- Local runtime, isolated worker/deployment preparation, action handlers, artifact access/retention and fixture tests.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0241 — Browser contracts and scoped connection metadata
- TASK-0242 — Enforce browser egress and connection-level proxy policy
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- A disposable fixture can be navigated, observed, filled, queried, captured, uploaded-to, downloaded-from and evaluated-against with bounded results; stale element/page references fail visibly.
- Upload from a disallowed path, oversize/disallowed download and evaluate_js escaping page context are denied with specific errors; results of evaluate_js are marked untrusted.
- No browser runs in the API process or sees host filesystem/socket mounts or unrelated secrets; memory/process/time/size limits are enforced.
- Terminal/cancel/expiry/error paths close resources; mock/dry runs launch no real worker/browser/network.
- Protected screenshots/downloads cannot be obtained by another principal or through an unrestricted public URL; retention is explicit; public chat filtering defaults apply at the presentation layer.

## Validation Plan

- Planned tests/test_browser_runtime.py plus real local fixture/worker smoke, resource-limit and cleanup checks.
- Regressions layers/envelope and protected-artifact/storage access checks; verify offline behavior by forbidding worker/network calls.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0240 → TASK-0243 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0243-browser-local-runtime`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.

## Reconciliation (2026-11-06)

After merging develop (TASK-0241 #303, TASK-0242 #304, Accepted plan #299): use the
Accepted nine-tool contract (upload/download/evaluate gated by connection allow_*),
required whitelist + Browserless provider naming from upstream, mutating-approval
default OFF (navigate/snapshot/extract/screenshot never wait; click/fill/upload/
download/evaluate may wait when require_mutating_approval is on). Local Playwright
runtime remains this task; Browserless proof stays TASK-0244.

## Delivery (2026-11-06)

Owner authorised browser implementation. Reconciled with Accepted DEC-0085; browser tests 100 passed / 1 skipped; required GitHub checks green on final head before merge.
