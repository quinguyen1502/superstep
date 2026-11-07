# Task

## Metadata

- Project: superstep
- Task ID: TASK-0250
- Title: Agent/recipe configuration and filtered browser trace/chat UI
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

Agent/recipe configuration and filtered browser trace/chat UI, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Add browser tool grants, per-argument sources and recipe settings in existing Agent/MCP config; preserve Settings/Data/Execution tabs.
- Extend existing run trace and chat presentation for ordered actions, bounded observations, protected screenshots, missing input, approval, challenge, expired and unknown states.
- Explain provider/proxy/session state without debug endpoints, secret URLs or unrestricted page/form content; reuse shared React presentation when applicable.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, arbitrary script/files, live provider/account setup, deployment, release and merge.
- New browser node/tab taxonomy, live provider setup, release and merge.

## Inputs And Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision proposal: `.factory-state/decisions/DEC-0085-browser-tools.md`.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`; DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081 referenced by the requirement/architecture.
- Dependency artifact: `.factory-state/tasks/review/TASK-0247-browser-url-web-tools.md`.
- Dependency artifact: `.factory-state/tasks/doing/TASK-0248-browser-recipes.md`.
- Dependency artifact: `.factory-state/tasks/review/TASK-0249-browser-connection-settings-ui.md`.

## Expected Outputs

- Editor/recipe controls, filtered trace/chat states, locale/docs snippets and UI evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0247 — Dynamic URL bindings, search/fetch and missing-context flows
- TASK-0248 — Reusable typed browser recipes through existing tool surfaces
- TASK-0249 — Connection, proxy and profile configuration UI
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- No Browser-specific canvas node/tab taxonomy or second Agent/model control is introduced. Data/execution fields live in their conventional tabs.
- URL-from-chat, workflow binding, search-first, ask-for-context and recipe invocation can be configured and inspected with current surfaces.
- Public chat sees only permitted safe results/approval context; no raw session handles, remote endpoints, cookies, secret queries or private screenshots leak.
- Keyboard/mobile/en/vi/light/dark state matrix and existing trace alignment/parallel-tool presentation remain correct.

## Validation Plan

- Frontend/React presentation tests, root npm test/build/lint; planned browser-agent-tools.spec.ts, browser-recipes.spec.ts and browser-trace.spec.ts.
- Exercise approval allowed/rejected/expired, session loss, unknown outcome and public-output filtering; use local fixtures and synthetic identities.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised full-chain implementation and controlled fixtures on 2026-11-05; this task explicitly stacks on unmerged prerequisites.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner chain instruction accepts scope and start; owner review and merge approval remain pending.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0247 → TASK-0250 before publication after a fresh all-ref allocation; owner authorised commit/push only.

## Handoff Notes

- Future branch: `factory/task-0250-browser-agent-recipe-trace-ui`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.

- 2026-11-06 preparation: explicit stack on TASK-0249 47a9b2bc / Draft #314, scoped REV-0239/QA-0239 (ten real Chrome cases, full declared checks running on source 14b1560a). TASK-0248 final #313 / 50a536ce has full passed checks; this branch includes its source 27cdf07d/base 07d22fce but not final metadata/Vi follow-up. Parent sync awaits explicit permission after automatic merge-review rejection, with no merge performed. Other prerequisites #312/#311/#310/#309/#308/#304/#303/#299 remain unmerged. No source changed for TASK-0250.

- 2026-11-06 task-start: factory ready exited 0 before source. Existing Agent/MCP and workflow settings will expose URL sources, recipe contracts/selectors and execution limits using General/Settings/Data/Execution tabs; owner-only trace observations/artifacts and filtered visitor states use current seams. No implementation source changed at task-start. Owner full-chain instruction authorises implementation and checks next.

- 2026-11-06 implementation: existing Agent/MCP Data URL sources and recipe Start contract/action selectors, inherited limits and owner-protected browser trace detail. Root browser_recipe survives editor save/reload. Browser-containing run intermediate events are marked and filtered server-side for live/persisted visitor chat; legacy envelopes and later state echoes are covered. Browser review prompts are not persisted into chat turns; raw final worker envelopes reduce to facts. Existing shared React chat renders safe statuses. No schema/dependency/new node/tab/model loop. New UI removal uses exact-name confirmation; source uses shared API/i18n/tokens.
- 2026-11-06 scoped evidence: final related backend 76 passed/1 optional PostgreSQL skip (24.55 s), then waiting-event metadata/approval/layers 27 passed (13.19 s). Root npm test passed (frontend 167, React 22, TypeScript SDK 102). Build/lint passed; new helper/presentation/API blob tests pass. Chrome initial full locale/theme matrix 8 passed (59.1 s); expanded mobile/recipe-tool/search/fetch + trace regression run 11 passed (1.4 min), plus existing Agent node regressions 2 passed before an interrupted harness run. Final lookup error-path rerun pending. Visual wide/narrow en/vi/light/dark images inspected outside Git at /private/tmp/superstep-browser-ui-shots-20261106. Full declared eight-command profile and scoped review/QA still pending.
- 2026-11-06 predecessor update: TASK-0249 source 14b1560a passed all eight commands; latest docs 17da46fc published to #314. This branch retains reviewed 47a9b2bc and does not incorporate later metadata; no git merge has been performed. Parent-sync permission remains pending after automatic merge-review rejection. Owner review/merge approval pending.

- 2026-11-06 scoped delivery: source 8dc9291d committed; final recipe/lookup UI rerun passed (2 cases, 26.9 s). REV-0240 / QA-0240 scoped conditional pass; full eight-command Factory verification running on committed source. Task remains review, owner approval pending; no merge performed.

- 2026-11-06 final verification: all eight declared commands passed clean source 8dc9291d (backend 488.43 s). REV-0240/QA-0240 updated to scoped pass; owner approval pending. Draft PR #315: https://github.com/quinguyen1502/superstep/pull/315. No source changed after the full run; no merge performed.
- 2026-11-07: Owner asked to correct this task's lifecycle. PR #315 is already merged. Review REV-0240 and QA QA-0240 were recorded before that merge. Status is done. No product source changed with this move.
