# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0006
- Status: Accepted on 2026-11-06. Studio tasks TASK-0241–0250 and TASK-0253 are merged. TASK-0251 merged in PR #321. TASK-0252 merged in PR #323. On 2026-11-07 the owner recorded the live-export drivers and asked for TASK-0261 and TASK-0262. Those tasks are in todo. Task-start is not authorised. AC8 fixture evidence is on develop. AC11 stays open until the live-driver tasks merge.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-07 (TASK-0252 merged; TASK-0261 and TASK-0262 planned)
- Related Requirements: REQ-0086
- Related Design: DES-0004
- Related Architecture: ARCH-0002, DEC-0085
- Discovery: DISC-0002
- Tasks: TASK-0241 through TASK-0253, plus TASK-0261 and TASK-0262 (studio first milestone merged; TASK-0251 and TASK-0252 merged; live-driver tasks in todo)
- Workflow: large-task-workflow for the overall cross-cutting feature; each task has its own independently reviewable delivery and medium/large scoped evidence as appropriate.

## Owner amendments (2026-11-06)

The owner reviewed REQ-0086 / DEC-0085 / DES-0004 / ARCH-0002 / PLAN-0006 and asked to **change** the plan (not accept as-is). Clarifications dated 2026-11-06 (Asia/Saigon). Statuses are **Accepted** (2026-11-06). DEC-0085 is Accepted; implementation is authorised.

1. **Relaxed default approvals.** Navigate, snapshot, structured extraction and screenshot never wait. Click, fill, upload, download and evaluate JS run immediately by default; each connection can turn on “require approval” for those mutating actions. Unknown effects / lost sessions / expired approvals never blindly replay writes. (AC6, TASK-0246, DEC point 6.)
2. **Persist browser sessions across chat turns** of the same conversation, same effective user/principal and same connection until idle/expiry, cancel or conversation/run end. No promised survival across worker/browser crashes. Proposed idle default 30 minutes, configurable, plus hard max. (REQ sessions, DEC point 5, DES, ARCH, TASK-0245.)
3. **Remote required in first studio delivery.** First remote provider is **Browserless** (https://www.browserless.io / CDP/browser API). Local Playwright remains required. If Browserless cannot prove destination/proxy/DNS/whitelist enforcement equivalent to local, document the gap and refuse the unsupported mode — do not silently weaken policy or claim local-only as enough. (TASK-0244, checkpoints.)
4. **Defer executable Python and TypeScript exports** (TASK-0251, TASK-0252) to a later phase after studio delivery. Trigger: “after studio browser tools are accepted and integrated.” First milestone is studio. TASK-0253 first-milestone handbook/e2e covers studio only; export handbook waits with 0251/0252. AC8 marked deferred. Exports leave the first-delivery critical path.
5. **Add upload, download and evaluate JavaScript** to the first version alongside the original six operations, with bounds (download size/type; upload from authorised attachments/workspace only; JS page-context only; results untrusted). (REQ in/out of scope, DES, ARCH, TASK-0243.)
6. **Mandatory origin/domain whitelist** per connection (empty invalid). Applies to navigation, redirects and subresources on local and Browserless paths; URLs from chat/state/model/search that would open the browser must pass it. (TASK-0241/0242/0247/0249.)
7. **Flexible-but-safe two-layer config** with explicit toggles and written risk analysis (see DEC-0085 risk table and DES-0004). Connection/operator: whitelist, proxy, runtimes, profile, mutating-approval toggle (default OFF), allow JS/upload/download, download limits, session idle/max, action/page budget; always-on private-IP block, untrusted page content, secret redaction, no public Settings, kill-switch. Agent/builder: which of the nine tools are granted; cannot widen whitelist or disable network enforcement. Recommended defaults: whitelist required; mutating approval OFF but visible; JS/upload/download only when connection allows and builder grants; session persist ON with 30m idle; screenshots filtered from public chat by default; stealth off unless chosen.

Unchanged intent: no new Browser canvas node; no second Agent loop; no Browser Use Cloud/Skyvern; proxy on connection with no chat override / no silent direct fallback; stealth optional best-effort; screenshots protected; public chat no Settings; typed-name deletes; en+vi; Settings/Data/Execution; search/fetch separate and do not inherit browser proxy.

### Draft implementation PRs started early

Draft PRs **#303–#315** (TASK-0241–0250 implementations) were opened against the **previous Proposed** plan before this amendment. They are **not** acceptance of DEC-0085 and must be **reconciled** with this amended package after the owner accepts it (whitelist, Browserless requirement, session-across-turns, nine tools, approval defaults, deferred exports, two-layer toggles). This planning amendment does not edit those implementation PRs and does not authorise merging them.

## Objective

Deliver browser connections, primitive tools for the existing Agent (nine operations), reusable typed recipes, dynamic URLs, connection-level proxy/profile/whitelist/safety-toggle policy, Browserless + local runtimes and studio UI/handbook. Read/search-only work remains separate from browser automation. No new vendor-specific canvas node or hidden browser Agent loop. Executable Python/TypeScript exports remain required later work after studio acceptance.

## Context Reviewed

- `vision.md`, `project.md`, `roadmap.md`, `project-specs.md`, `AGENTS.md`, `.factory/AGENTS.md`.
- `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- `.factory-state/artifacts/DES-0004-browser-tools.md`.
- `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- `.factory-state/decisions/DEC-0085-browser-tools.md`.
- `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`, DEC-0081 and current managed/MCP/Agent/effect/export seams recorded in discovery.
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, current package/check configuration.
- Exploratory mockup `.factory-state/previews/browser-tool/browser-workspace.html`; production UI must follow standard config tabs and include whitelist editor + safety toggles even though the prototype omits them.
- Owner amendments and flexible-but-safe config guidance dated 2026-11-06 (Asia/Saigon).

## Work Breakdown

| Task | Purpose | Size | Dependencies | Milestone |
| --- | --- | --- | --- | --- |
| [TASK-0241](../tasks/todo/TASK-0241-browser-connection-contract.md) | Browser contracts, whitelist, toggles and scoped connection metadata | M | none | Studio |
| [TASK-0242](../tasks/todo/TASK-0242-browser-egress-proxy-policy.md) | Enforce browser egress, whitelist and connection-level proxy policy | L | TASK-0241 | Studio |
| [TASK-0243](../tasks/todo/TASK-0243-browser-local-runtime.md) | Isolated local Playwright runtime and nine bounded browser tools | M | TASK-0241, TASK-0242 | Studio |
| [TASK-0244](../tasks/todo/TASK-0244-browser-remote-profiles.md) | Browserless remote capabilities and origin-scoped login profiles | M | TASK-0241, TASK-0242, TASK-0243 | Studio (remote required) |
| [TASK-0245](../tasks/todo/TASK-0245-browser-run-sessions.md) | Conversation/run-bound sessions, ordered Agent calls and lifecycle | L | TASK-0243, TASK-0244 | Studio |
| [TASK-0246](../tasks/todo/TASK-0246-browser-approval-recovery.md) | Configurable mutating approvals, stale sessions and uncertain-effect recovery | L | TASK-0245 | Studio |
| [TASK-0247](../tasks/todo/TASK-0247-browser-url-web-tools.md) | Dynamic URL bindings, whitelist checks, search/fetch and missing-context flows | M | TASK-0241, TASK-0245, TASK-0246 | Studio |
| [TASK-0248](../tasks/todo/TASK-0248-browser-recipes.md) | Reusable typed browser recipes through existing tool surfaces | M | TASK-0241, TASK-0245, TASK-0246 | Studio |
| [TASK-0249](../tasks/todo/TASK-0249-browser-connection-settings-ui.md) | Connection, whitelist, proxy, toggles and profile configuration UI | M | TASK-0241, TASK-0242, TASK-0244 | Studio |
| [TASK-0250](../tasks/todo/TASK-0250-browser-agent-recipe-trace-ui.md) | Agent/recipe configuration and filtered browser trace/chat UI | M | TASK-0247, TASK-0248, TASK-0249 | Studio |
| [TASK-0253](../tasks/todo/TASK-0253-browser-e2e-handbook.md) | Studio integrated acceptance, example workflow and bilingual handbook | M | TASK-0250 | Studio first milestone |
| [TASK-0251](../tasks/done/TASK-0251-browser-python-export.md) | Executable Python and project export for browser tools/recipes | L | TASK-0247, TASK-0248, TASK-0246, TASK-0244 | Merged in PR #321 (REV-0242, QA-0242) |
| [TASK-0252](../tasks/done/TASK-0252-browser-typescript-export.md) | Executable TypeScript and project export with browser parity | L | TASK-0251 | Merged in PR #323 (REV-0244, QA-0244) |
| [TASK-0261](../tasks/todo/TASK-0261-browser-python-live-export.md) | Live Playwright/Browserless page in the Python export | M | TASK-0251 | Todo. Task-start waits |
| [TASK-0262](../tasks/todo/TASK-0262-browser-typescript-live-export.md) | Live Playwright/Browserless page in the TypeScript export | M | TASK-0261, TASK-0252 | Todo. Starts after TASK-0261 merges |

Each linked task records its scope, outputs, dependencies, acceptance criteria and validation, and explicitly names the requirement/design/architecture/decision/discovery paths. Studio first-delivery tasks are merged. TASK-0251 and TASK-0252 are merged. TASK-0261 and TASK-0262 are the live-driver split and are not started.

## Deferred / later

| Item | Reason deferred | Trigger to pick it up |
| --- | --- | --- |
| TASK-0251 executable Python/project export | Merged in PR #321. | Done |
| TASK-0252 executable TypeScript/project export | Merged in PR #323. | Done |
| TASK-0261 live Python export page | Specified by DEC-0085 decision 10. In todo. | Owner says task-start |
| TASK-0262 live TypeScript export page | Same contract as TASK-0261. In todo. | TASK-0261 on develop, then owner says task-start |
| Export sections of handbook / AC8 evidence | Python and TypeScript fixture notes merged with TASK-0251 and TASK-0252. Live-driver handbook notes travel with TASK-0261 and TASK-0262. | TASK-0261 and TASK-0262 |
| Interactive profile capture / live-view login product | Operator-provisioned profiles suffice for v1 | Owner request after studio |
| Hosted browser-Agent (Browser Use Cloud/Skyvern) | Browserless supplies browser only | Separate requirement if demanded |
| Asymmetric remote providers beyond Browserless | Browserless is the first required remote | Browserless proof fails or owner names another provider |
| SSE or other non-WebSocket chat transports for browser UI | Not requested | Client need |

## Sequence And Checkpoints

1. **Contracts and authority:** TASK-0241. Confirm the command/session/secret/binding schema, **required whitelist**, safety-toggle defaults, provider/proxy capability matrix (local + Browserless) and proposed idle/budget defaults; review required migrations. None of these definitions activates a browser on the API host.
2. **Network gate and runtime:** TASK-0242, TASK-0243, TASK-0244. Prove controlled browser egress/proxy/**whitelist** behavior using a minimal disposable browser test harness before enabling the product runtime. Local **and** Browserless fixture paths must enforce the same security policy; refuse unprovable vendor/proxy combinations. Shipping local-only does not close the remote checkpoint.
3. **Run semantics and behavior:** TASK-0245, TASK-0246, then TASK-0247 and TASK-0248. Preserve same-session call order, **cross-turn conversation persistence**, principal isolation, configurable approval/outcome/recovery semantics, then dynamic URL/search/fetch (with whitelist) and recipes. Existing non-browser concurrency remains compatible.
4. **User experience:** TASK-0249 follows the stable connection/provider/whitelist/toggle contract. TASK-0250 integrates tool grants, bindings, recipes and trace/chat with standard Settings/Data/Execution tabs.
5. **Studio integration (first milestone):** TASK-0253. Consolidate studio AC traceability (AC1–AC7, AC9, studio parts of AC10), disposable example, en/vi studio handbook, actual worker/proxy/Browserless/UI evidence and full declared checks. AC8/export handbook are out of this milestone.
6. **Portable code:** TASK-0251 and TASK-0252 are merged. TASK-0261, then TASK-0262, add the live Playwright/Browserless page from DEC-0085 decision 10. The `memory` fixture contract stays. Upload, download, and screenshot bytes stay refused.

**Studio critical path:** contracts → egress/whitelist → local runtime (nine tools) → Browserless/profile gate → conversation sessions → approval/recovery → bindings/recipes → UI → studio acceptance. Settings/UI follow their explicit dependencies. Exports are **not** on the first-delivery critical path.

## Requirement Traceability

| Criterion | Primary tasks | Completion evidence |
| --- | --- | --- |
| AC1 connection/whitelist/proxy/profile/toggle CRUD and discovery | TASK-0241, TASK-0244, TASK-0249 | Schemas/auth/secret/migration and UI tests |
| AC2 nine bounded isolated tools and session access (local + Browserless) | TASK-0243, TASK-0244, TASK-0245 | Real local/Browserless fixtures and cross-principal checks |
| AC3 effective egress, whitelist and proxy resolution | TASK-0242, TASK-0244 | Adversarial browser/proxy/DNS/whitelist fixtures on both providers |
| AC4 runtime URL/search/fetch/missing context + whitelist denial | TASK-0247, TASK-0250 | Chat/state/search/fetch and missing-input/off-whitelist cases |
| AC5 call order, cross-turn persistence, concurrency, bounds and cleanup | TASK-0245 | Same-session ordered calls, multi-turn reuse, independent-tool overlap |
| AC6 configurable approvals, expiry, recovery and unknown effects | TASK-0246, TASK-0250 | Approval ON/OFF, crash-after-effect, stale-ref and expiry/rejection tests |
| AC7 reusable recipes and explicit layout failure | TASK-0248, TASK-0250 | Versioned typed inputs/results and fixture selector changes |
| AC8 executable exports without secrets/stubs | TASK-0251, TASK-0252 | Fixture evidence is on develop: PR #321 and PR #323. |
| AC11 live export page | TASK-0261, TASK-0262 | Not started. One page per alias for Playwright and Browserless. `memory` stays the fixture driver. |
| AC9 accessible bilingual UI and private artifacts | TASK-0243, TASK-0249, TASK-0250 | Access/retention/public filtering, toggles/grants, keyboard/theme/locale evidence |
| AC10 integrated studio evidence, docs and review/QA | TASK-0253 and studio delivery tasks | Full declared checks and studio requirement traceability; export evidence waits |

## Validation Strategy

- Planning-only checks: Factory structural validation, all-ref artifact ID uniqueness, reference/dependency checks and whitespace review. Record actual results below; no product tests are claimed for Markdown artifacts.
- Runtime delivery: schema/permissions/secrets/migrations/whitelist/toggles, browser-generated egress adversarial fixtures, proxy routing/remote-DNS denial, Browserless capability proof, non-root resource bounds, scoped cookies/artifacts, ordered calls, cross-turn persistence and fencing.
- Reliability delivery: effect/ledger/queue regressions plus lost-session, approval ON/OFF, expired approval, stale observation, time-travel and unknown external-write behavior.
- Export delivery (**later**): actual isolated Python/Node fixture-project execution with the same supported scenarios as Studio; guard against secret leakage, missing policy, proxy fallback and silent stubs.
- UI delivery: root `npm test`, `npm run build`, `npm run lint`; relevant Playwright e2e, en/vi and light/dark, narrow layout, keyboard/dialog focus, whitelist editor and toggle copy, existing trace alignment. Evidence images stay outside Git or in CI artifacts.
- Final studio delivery: declared backend suite including layer/envelope/migrations; `factory verify run --profile full`, `factory validate`, `factory ready` and ID checks, with actual command/runtime/dependency evidence recorded per task. New fixture/test module names in tasks are planned, not observed existing commands.

## Risks And Recovery

- See DEC-0085 risk analysis table for per-toggle risks (SSRF, prompt injection, session hijack, JS eval exfiltration, upload/download abuse, screenshot PII, Browserless traffic exposure, long-lived sessions).
- Browserless/proxy support cannot be claimed from CDP availability alone. A capability proof can require refusal or a reviewed plan amendment; no weakened target policy as an expedient; local-only is not a substitute for the remote requirement.
- Unknown browser effects and expired live sessions cannot be repaired by generic retry or result-cache replay. Conservative stop/re-observe behavior is required even when mutating approval is OFF.
- Stateful operations cannot use the generic managed result ledger blindly. Trusted run/conversation context, page generations and effect intent are explicit contract concerns.
- Browser outputs can contain private data; screenshot storage, query/form redaction, chat filtering and retention are delivery work.
- A task marked L must be split further before task-start if its reviewed scope is too broad for one independent PR. Any added task ID follows a new fetch/all-ref allocation.
- Feature-gated rollout starts only after integrated studio runtime and policy gates pass. Disabling the feature terminates/drains sessions and preserves audit/outcome records; never repeat website writes as rollback.
- Early draft PRs #303–#315 must be reconciled after acceptance; do not merge them against the superseded Proposed wording.

## Approval Needs And Limits

- The owner requested recording requirements and breaking down tasks (2026-11-03), amended the Proposed package (2026-11-06), then accepted it and authorised implementation the same day ("Ok triển khai", sync latest develop first).
- REQ-0086, DES-0004, ARCH-0002 and DEC-0085 are **Accepted** on 2026-11-06. Studio tasks are promoted to todo; implementation uses one branch `factory/task-NNNN-<slug>` and one task PR into `develop`; dependencies merge first unless an owner-authorised stack is explicitly recorded.
- Draft implementation PRs #303–#315 must be reconciled with this Accepted package before merge. No release/version bump is authorised by this acceptance. Live Browserless secrets stay operator-supplied and are never printed.
- On 2026-11-07 the owner lifted the TASK-0251/0252 deferral. Both are merged: PR #321 then PR #323. REQ-0086 stays open for AC11.

## Assumptions And Open Questions

- No exact proxy protocol/auth/default timeout/download MIME list is approved by a mockup. The contract/capability tasks must make those choices concrete and testable without requiring live secrets to plan. Idle default proposal remains 30 minutes.
- Browser profiles initially accept scoped operator-provisioned state. Interactive login/live-view remains out of scope. Cross-turn session persistence **is** in scope for same conversation/principal/connection.
- Browserless is the named first remote provider; capability proof remains an implementation gate.
- No blocking information is missing for creation of this amended proposed task set; owner acceptance and scoped technical proofs gate future implementation rather than this documentation task.

## Completion Criteria

- **Studio first milestone:** AC1–AC7, AC9 and studio AC10 have linked passing evidence; studio delivery tasks (0241–0250, studio 0253) are reviewed/QA-verified, owner accepted, done and integrated through their authorised PRs.
- Executable local **and** Browserless browser fixtures, whitelist/proxy/security/recovery behavior pass. Unsupported combinations are explicit and documented. Local-only is not sufficient to close the remote requirement.
- Bilingual studio docs/example and feature-disable/recovery instructions reflect the actual delivered capabilities, including toggles and risks.
- **Exports:** the studio gate is merged. TASK-0251 and TASK-0252 are merged. TASK-0261 and TASK-0262 are in todo and are not started. AC11 stays open until the live-driver tasks merge.
- Planning completion alone did not mark the feature implemented; on 2026-11-06 the owner Accepted the amended package and authorised implementation. Feature delivery still requires studio task PRs.

## Planning Activity

- 2026-11-03: Read Factory/project context and related managed/Agent/export/network evidence. Fetch succeeded; IDs allocated against all refs. Wrote one requirement, discovery, design, architecture, proposed decision, this plan and 13 backlog task artifacts.
- 2026-11-03: Planning validation passed for all 19 new requirement/design/architecture/decision/discovery/plan/task artifacts: required task sections, backlog status, explicit path references, plan links, whitespace and acyclic task dependencies. `factory ids check --all-refs` passed against the working tree and 95 refs; `git diff --check` passed.
- 2026-11-03: `factory validate` exited 1 because this worktree lacks `node_modules` and the local backend/SDK/handbook virtualenv outputs and installed packages required by the existing dependency manifest. No artifact-structure error was reported. This is an environment-validation limitation, not a browser delivery blocker, and does not justify installing dependencies during documentation-only work. Full validation/ready remains required before future implementation; no product tests/full verification were run or claimed here.
- 2026-11-04: Owner requested publication (“Push đi”). Prepared this planning-only branch from develop 94c44366, preserving current release/SDK changes. Re-fetched and allocated against all refs in an isolated worktree; unpublished DEC-0084 and TASK-0238–0250 were renumbered to DEC-0085 and TASK-0241–0253 after collisions with merged work. All internal links, dependencies, future branch names and roadmap entries were updated together. Proposed statuses/backlog lifecycle are retained; no implementation or merge approval inferred.
- 2026-11-04: Publication checks passed: unique IDs across working tree plus 83 refs; 19 artifact/task references and dependency DAG; whitespace; both mockup fragment scripts parsed by Node. The 23-file publication includes roadmap and three exploratory HTML previews. No application implementation test or dependency installation is claimed for this documentation-only commit.

## Owner Delivery Authorisation — 2026-11-05

The owner instructed: “Pull develop về branch hiện tại, và tiến hành chuỗi task này.” This accepts the proposed browser delivery scope and starts PLAN-0006 in dependency order. This supersedes earlier planning-only/pending-start statements; source onboarding approval statuses are unchanged. Implementation, fixture validation and task PRs are authorised; merges, production/provider setup, release and deployment are not. Task branches may stack on the published planning package; dependent implementation tasks require predecessor review/QA and an explicitly documented stack.

- 2026-11-05: Owner started the chain. TASK-0241 branch is based on develop 3c83262a plus published planning commit b8f3a861 carried as 3beffe55. Readiness passed before source changes. Contract implementation and metadata-only gate are recorded in `docs/browser-contract.md`; browser runtime remains unavailable until egress/session proof.

- 2026-11-06 TASK-0249: Settings UI in scoped review (REV-0239/QA-0239), full profile running; ten real Chrome cases passed. Existing branch retains TASK-0248 base 07d22fce pending explicit parent-sync permission; #313 final 50a536ce independently records predecessor full pass.

- 2026-11-06 TASK-0250: editor/recipe/private trace/chat source 8dc9291d in scoped review (REV-0240/QA-0240), full verification running. URL bindings, inherited limits, root recipe preservation/selectors, typed workflow-tool selection and backend visitor filtering use existing surfaces; owner approval pending.

- 2026-11-06 TASK-0250 final: all eight declared checks passed source 8dc9291d (backend 488.43 s), REV-0240/QA-0240 scoped pass, Draft #315. Owner approval pending; no merge.
- 2026-11-06: Owner reviewed the proposed package and requested six amendments plus flexible-but-safe two-layer configuration and risk analysis. Amended REQ-0086, DEC-0085, DES-0004, ARCH-0002, PLAN-0006, DISC-0002, roadmap and TASK-0241–0253 on the open draft PR without marking Accepted or merging. Noted draft implementation PRs #303–#315 need reconciliation after acceptance. Statuses remain Proposed; TASK-0251/0252 deferred off the studio critical path.
- 2026-11-06 (later): Owner accepted the amended package and authorised implementation ("Ok triển khai", sync latest develop first). Marked REQ-0086, DEC-0085, DES-0004, ARCH-0002 and PLAN-0006 Accepted; moved studio tasks TASK-0241–0250 and TASK-0253 to todo; left TASK-0251/0252 deferred in backlog. Draft PRs #303–#315 still require reconciliation before merge.
- 2026-11-07: Studio tasks through TASK-0253 and handbook screenshots are merged. The owner lifted the export deferral and asked for TASK-0251 and TASK-0252 through Ready pull requests. TASK-0251 implementation is on `factory/task-0251-browser-python-export`. TASK-0252 stays stacked until that pull request is Ready. Merge waits for the owner. REQ-0086 is not marked done.
- 2026-11-07: TASK-0252 TypeScript export is done on `factory/task-0252-browser-typescript-export` (REV-0244, QA-0244) and merged in PR #323.
- 2026-11-07: The owner asked for plan-tasks on the live export drivers. Created TASK-0261 and TASK-0262 in todo after `factory ids next TASK --all-refs` returned TASK-0261. No implementation branch and no task-start.
