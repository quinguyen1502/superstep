# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0006
- Status: Accepted for delivery — TASK-0241–0243 in review; remaining tasks await dependencies
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Related Requirements: REQ-0086
- Related Design: DES-0004
- Related Architecture: ARCH-0002, DEC-0085
- Discovery: DISC-0002
- Tasks: TASK-0241 through TASK-0253 (13 tasks)
- Workflow: large-task-workflow for the overall cross-cutting feature; each task has its own independently reviewable delivery and medium/large scoped evidence as appropriate.

## Objective

Deliver browser connections, primitive tools for the existing Agent, reusable typed recipes, dynamic URLs, connection-level proxy/profile policy and executable Python/TypeScript exports. Read/search-only work remains separate from browser automation. No new vendor-specific canvas node or hidden browser Agent loop.

## Context Reviewed

- `vision.md`, `project.md`, `roadmap.md`, `project-specs.md`, `AGENTS.md`, `.factory/AGENTS.md`.
- `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- `.factory-state/artifacts/DES-0004-browser-tools.md`.
- `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- `.factory-state/decisions/DEC-0085-browser-tools.md`.
- `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`, DEC-0081 and current managed/MCP/Agent/effect/export seams recorded in discovery.
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, current package/check configuration and the unrelated active TASK-0224 context (left unchanged).
- Exploratory mockup `.factory-state/previews/browser-tool/browser-workspace.html`; production UI must follow standard config tabs, and proxy setup was discussed after that prototype.

## Work Breakdown

| Task | Purpose | Size | Dependencies |
| --- | --- | --- | --- |
| [TASK-0241](../tasks/review/TASK-0241-browser-connection-contract.md) | Browser contracts and scoped connection metadata | M | none |
| [TASK-0242](../tasks/review/TASK-0242-browser-egress-proxy-policy.md) | Enforce browser egress and connection-level proxy policy | L | TASK-0241 |
| [TASK-0243](../tasks/review/TASK-0243-browser-local-runtime.md) | Isolated local Playwright runtime and bounded browser tools | M | TASK-0241, TASK-0242 |
| [TASK-0244](../tasks/backlog/TASK-0244-browser-remote-profiles.md) | Remote browser capabilities and origin-scoped login profiles | M | TASK-0241, TASK-0242, TASK-0243 |
| [TASK-0245](../tasks/backlog/TASK-0245-browser-run-sessions.md) | Run-bound sessions, ordered Agent calls and lifecycle integration | L | TASK-0243, TASK-0244 |
| [TASK-0246](../tasks/backlog/TASK-0246-browser-approval-recovery.md) | Browser approvals, stale sessions and uncertain-effect recovery | L | TASK-0245 |
| [TASK-0247](../tasks/backlog/TASK-0247-browser-url-web-tools.md) | Dynamic URL bindings, search/fetch and missing-context flows | M | TASK-0241, TASK-0245, TASK-0246 |
| [TASK-0248](../tasks/backlog/TASK-0248-browser-recipes.md) | Reusable typed browser recipes through existing tool surfaces | M | TASK-0241, TASK-0245, TASK-0246 |
| [TASK-0249](../tasks/backlog/TASK-0249-browser-connection-settings-ui.md) | Connection, proxy and profile configuration UI | M | TASK-0241, TASK-0242, TASK-0244 |
| [TASK-0250](../tasks/backlog/TASK-0250-browser-agent-recipe-trace-ui.md) | Agent/recipe configuration and filtered browser trace/chat UI | M | TASK-0247, TASK-0248, TASK-0249 |
| [TASK-0251](../tasks/backlog/TASK-0251-browser-python-export.md) | Executable Python and project export for browser tools/recipes | L | TASK-0247, TASK-0248, TASK-0246, TASK-0244 |
| [TASK-0252](../tasks/backlog/TASK-0252-browser-typescript-export.md) | Executable TypeScript and project export with browser parity | L | TASK-0251 |
| [TASK-0253](../tasks/backlog/TASK-0253-browser-e2e-handbook.md) | Integrated browser acceptance, example workflow and bilingual handbook | M | TASK-0250, TASK-0251, TASK-0252 |

Each linked task records its scope, outputs, dependencies, acceptance criteria and validation, and explicitly names the requirement/design/architecture/decision/discovery paths. All are currently **backlog**, not implementation authorisation.

## Sequence And Checkpoints

1. **Contracts and authority:** TASK-0241. Confirm the command/session/secret/binding schema, provider/proxy capability matrix and proposed defaults; review required migrations. None of these definitions activates a browser on the API host.
2. **Network gate and runtime:** TASK-0242, TASK-0243, TASK-0244. Prove controlled browser egress/proxy behavior using a minimal disposable browser test harness before enabling the product runtime. The harness does not depend on product runtime completion. Local and controlled-remote fixture paths must enforce the same security policy; refuse unprovable vendor/proxy combinations.
3. **Run semantics and behavior:** TASK-0245, TASK-0246, then TASK-0247 and TASK-0248. Preserve same-session call order and principal isolation, approval/outcome/recovery semantics, then dynamic URL/search/fetch and recipes. Existing non-browser concurrency remains compatible.
4. **User experience:** TASK-0249 follows the stable connection/provider contract. TASK-0250 integrates tool grants, bindings, recipes and trace/chat with standard Settings/Data/Execution tabs. Work can be reviewed independently of export changes after dependencies land.
5. **Portable code:** TASK-0251, then TASK-0252. Execute exported fixture workflows outside Superstep, including policy/proxy/session/approval behavior; syntax or placeholder code is not sufficient. Exports are part of this requirement, not an unspecified later phase.
6. **Integration:** TASK-0253. Consolidate AC traceability, disposable example, en/vi handbook, actual worker/proxy/remote/export/UI evidence and full declared checks. Completion requires every task's review/QA and integration evidence.

Critical path: contracts → egress → local runtime → remote capability/profile gate → run sessions → approval/recovery → bindings/recipes → Python export → TypeScript export → integrated acceptance. Settings/UI can follow their explicit dependencies; no sub-agent or concurrent implementation is started by this plan.

## Requirement Traceability

| Criterion | Primary tasks | Completion evidence |
| --- | --- | --- |
| AC1 connection/proxy/profile CRUD and discovery | TASK-0241, TASK-0244, TASK-0249 | Schemas/auth/secret/migration and UI tests |
| AC2 bounded isolated tools and session access | TASK-0243, TASK-0244, TASK-0245 | Real local/remote fixtures and cross-principal checks |
| AC3 effective egress and proxy resolution | TASK-0242, TASK-0244, TASK-0251, TASK-0252 | Adversarial browser/proxy/DNS fixtures and exported policy parity |
| AC4 runtime URL/search/fetch/missing context | TASK-0247, TASK-0250 | Chat/state/search/fetch and missing-input cases |
| AC5 call order, concurrency, bounds and cleanup | TASK-0245, TASK-0251, TASK-0252 | Same-session ordered calls plus independent-tool overlap |
| AC6 approvals, expiry, recovery and unknown effects | TASK-0246, TASK-0250, TASK-0251, TASK-0252 | Crash-after-effect, stale-ref and approval expiry/rejection tests |
| AC7 reusable recipes and explicit layout failure | TASK-0248, TASK-0250, TASK-0251, TASK-0252 | Versioned typed inputs/results and fixture selector changes |
| AC8 executable exports without secrets/stubs | TASK-0251, TASK-0252 | Plain/project execution outside Superstep |
| AC9 accessible bilingual UI and private artifacts | TASK-0243, TASK-0249, TASK-0250 | Access/retention/public filtering and keyboard/theme/locale evidence |
| AC10 integrated evidence, docs and review/QA | TASK-0253 and all delivery tasks | Full declared checks and final requirement traceability |

## Validation Strategy

- Planning-only checks: Factory structural validation, all-ref artifact ID uniqueness, reference/dependency checks and whitespace review. Record actual results below; no product tests are claimed for Markdown artifacts.
- Runtime delivery: schema/permissions/secrets/migrations, browser-generated egress adversarial fixtures, proxy routing/remote-DNS denial, non-root resource bounds, scoped cookies/artifacts, ordered calls and fencing.
- Reliability delivery: effect/ledger/queue regressions plus lost-session, expired approval, stale observation, time-travel and unknown external-write behavior.
- Export delivery: actual isolated Python/Node fixture-project execution with the same supported scenarios as Studio; guard against secret leakage, missing policy, proxy fallback and silent stubs.
- UI delivery: root `npm test`, `npm run build`, `npm run lint`; relevant Playwright e2e, en/vi and light/dark, narrow layout, keyboard/dialog focus and existing trace alignment. Evidence images stay outside Git or in CI artifacts.
- Final delivery: declared backend suite including layer/envelope/migrations; `factory verify run --profile full`, `factory validate`, `factory ready` and ID checks, with actual command/runtime/dependency evidence recorded per task. New fixture/test module names in tasks are planned, not observed existing commands.

## Risks And Recovery

- Remote/proxy support cannot be claimed from CDP availability alone. A capability proof can require refusal or a reviewed plan amendment; no weakened target policy as an expedient.
- Unknown browser effects and expired live sessions cannot be repaired by generic retry or result-cache replay. Conservative stop/re-observe/approval behavior is required.
- Stateful operations cannot use the generic managed result ledger blindly. Trusted run context, page generations and effect intent are explicit contract concerns.
- Browser outputs can contain private data; screenshot storage, query/form redaction, chat filtering and retention are delivery work.
- A task marked L must be split further before task-start if its reviewed scope is too broad for one independent PR. Any added task ID follows a new fetch/all-ref allocation.
- Feature-gated rollout starts only after integrated runtime, policy and export gates pass. Disabling the feature terminates/drains sessions and preserves audit/outcome records; never repeat website writes as rollback.

## Approval Needs And Limits

- The owner requested recording requirements and breaking down tasks. This authorises this planning package and backlog artifacts only.
- REQ-0086, DES-0004, ARCH-0002 and DEC-0085 retain Proposed status. Owner acceptance/amendment of this package is required before task promotion/start; `factory ready` must also pass before implementation source work.
- Future implementation uses one branch `factory/task-NNNN-<slug>` and one task PR into `develop`; dependencies merge first unless an owner-authorised stack is explicitly recorded.
- The original planning turn made no branch/commit/PR. On 2026-11-04 the owner explicitly authorised commit and push of this proposed package. This publication uses a planning branch from the fetched develop and does not authorise implementation, migration execution, live provider/proxy/account setup, merge, release or deployment. Unrelated local TASK-0224 edits are excluded.

## Assumptions And Open Questions

- No exact proxy protocol/provider/default timeout is approved by a mockup. The contract/capability tasks must make those choices concrete and testable without requiring live secrets to plan.
- Browser profiles initially accept scoped operator-provisioned state. Interactive login/live-view, cross-turn session persistence and delegated hosted browser Agents remain out of scope.
- No blocking information is missing for creation of this proposed task set; owner acceptance and scoped technical proofs gate future implementation rather than this documentation task.

## Completion Criteria

- All REQ-0086 AC1–AC10 have linked passing evidence; all delivery tasks are reviewed/QA-verified, owner accepted, done and integrated through their authorised PRs.
- Executable local and controlled-remote browser fixtures, proxy/security/recovery behavior and both language exports pass. Unsupported combinations are explicit and documented.
- Bilingual docs/example and feature-disable/recovery instructions reflect the actual delivered capabilities.
- Planning completion does not mark the feature implemented or change existing approval statuses.

## Planning Activity

- 2026-11-03: Read Factory/project context and related managed/Agent/export/network evidence. Fetch succeeded; IDs allocated against all refs. Wrote one requirement, discovery, design, architecture, proposed decision, this plan and 13 backlog task artifacts.
- 2026-11-03: Planning validation passed for all 19 new requirement/design/architecture/decision/discovery/plan/task artifacts: required task sections, backlog status, explicit path references, plan links, whitespace and acyclic task dependencies. `factory ids check --all-refs` passed against the working tree and 95 refs; `git diff --check` passed.
- 2026-11-03: `factory validate` exited 1 because this worktree lacks `node_modules` and the local backend/SDK/handbook virtualenv outputs and installed packages required by the existing dependency manifest. No artifact-structure error was reported. This is an environment-validation limitation, not a browser delivery blocker, and does not justify installing dependencies during documentation-only work. Full validation/ready remains required before future implementation; no product tests/full verification were run or claimed here.

- 2026-11-04: Owner requested publication (“Push đi”). Prepared this planning-only branch from develop 94c44366, preserving current release/SDK changes. Re-fetched and allocated against all refs in an isolated worktree; unpublished DEC-0084 and TASK-0238–0250 were renumbered to DEC-0085 and TASK-0241–0253 after collisions with merged work. All internal links, dependencies, future branch names and roadmap entries were updated together. Proposed statuses/backlog lifecycle are retained; no implementation or merge approval inferred.
- 2026-11-04: Publication checks passed: unique IDs across working tree plus 83 refs; 19 artifact/task references and dependency DAG; whitespace; both mockup fragment scripts parsed by Node. The 23-file publication includes roadmap and three exploratory HTML previews. No application implementation test or dependency installation is claimed for this documentation-only commit.

## Owner Delivery Authorisation — 2026-11-05

The owner instructed: “Pull develop về branch hiện tại, và tiến hành chuỗi task này.” This accepts the proposed browser delivery scope and starts PLAN-0006 in dependency order. This supersedes earlier planning-only/pending-start statements; source onboarding approval statuses are unchanged. Implementation, fixture validation and task PRs are authorised; merges, production/provider setup, release and deployment are not. Task branches may stack on the published planning package; dependent implementation tasks require predecessor review/QA and an explicitly documented stack.

- 2026-11-05: Owner started the chain. TASK-0241 branch is based on develop 3c83262a plus published planning commit b8f3a861 carried as 3beffe55. Readiness passed before source changes. Contract implementation and metadata-only gate are recorded in `docs/browser-contract.md`; browser runtime remains unavailable until egress/session proof.
