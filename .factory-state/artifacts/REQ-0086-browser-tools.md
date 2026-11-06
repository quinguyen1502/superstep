# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0086
- Status: Accepted on 2026-11-06. Owner reviewed the amended package (relaxed approvals, cross-turn sessions, Browserless required, deferred exports, upload/download/evaluate JS, mandatory whitelist, two-layer toggles) and said "Ok triển khai" with instruction to sync latest develop before coding.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06 (Accepted; implementation authorised)
- Source: Owner discussion on browser tools, autonomous browsing, dynamic URLs, portable exports and connection-level proxies; followed by “Tiến hành ghi nhận yêu cầu và break task đi”. Owner amendments on 2026-11-06 (Asia/Saigon) after reviewing the proposed package without accepting it as-is; additional flexible-but-safe config and risk guidance the same day.

## Summary

Let existing Superstep Agent nodes operate a real browser through scoped tools, and let workflows invoke reusable browser recipes through existing generic tool/MCP interfaces. Browser connections own infrastructure, network/proxy settings, a required origin whitelist, optional login profiles and operator safety toggles. URLs are runtime arguments, including values supplied through chat, workflow state or search results. First studio delivery includes local Playwright and Browserless remote runtimes, session persistence across chat turns of the same conversation, upload/download and evaluate-JavaScript tools with bounded safety controls. Executable Python and TypeScript exports remain in the requirement as later work after studio is accepted.

## Owner clarifications (2026-11-06)

Recorded after the owner reviewed the proposed package and asked to change it (not accept as-is), then added flexible-but-safe configuration guidance:

1. **Relaxed default approvals.** Do not require human approval for every possible-effect action. First-delivery default: navigate, snapshot, structured extraction and screenshot never wait. Click, fill, upload, download and evaluate JavaScript run immediately by default; each browser connection can turn on “require approval” for those mutating actions. Keep conservative handling for unknown effects, lost sessions, expired approvals and never blindly replay writes.
2. **Persist browser sessions across chat turns** of the same conversation, same effective user/principal and same connection, until idle/expiry, cancel or the run/conversation ends. Still no promised survival across worker/browser crashes.
3. **Remote support is required** in the first studio delivery. The first remote provider is Browserless (https://www.browserless.io / their CDP/browser API). Local isolated Playwright remains required as well. If Browserless cannot prove destination/proxy/DNS enforcement equivalent to the local worker, document the gap and refuse the unsupported mode — do not silently weaken policy or claim local-only as sufficient.
4. **Defer executable Python and TypeScript exports** (TASK-0251, TASK-0252) to a later phase after studio delivery. They stay in the requirement with a deferred trigger. First delivery milestone is studio (connections, runtime, sessions, tools including new ops, UI, handbook covering studio). TASK-0253 for the first milestone covers studio only.
5. **First version adds both** file upload and download, **and** evaluate JavaScript, in addition to navigate, snapshot, click, fill, structured extraction and screenshot. Bound them: download size/type limits; upload only from authorised attachments/workspace files (not arbitrary host paths); evaluate JS is sandboxed to the page context (no Node/shell); results are untrusted page data and never expand access or skip whitelist/approval.
6. **Each browser connection must have an origin/domain whitelist.** Empty whitelist is invalid. Navigation, redirects and subresources outside the list are blocked on local and Browserless paths. A URL from chat, state, model or search that is not on the whitelist is denied before the browser opens it.
7. **Flexible-but-safe two-layer configuration** with explicit user-facing toggles and written risk analysis (see Business Rules and DES-0004 / DEC-0085 / PLAN-0006). Connection-level operator controls set infrastructure and safety bounds; Agent-node builder controls only which tools are granted. The builder cannot widen the connection whitelist or disable network enforcement.

Unchanged product intent: no new Browser canvas node; no second Agent loop; no hosted browser-Agent (Browser Use Cloud/Skyvern); proxy on the connection (direct / operator system default / custom) with no chat override and no silent fallback to direct; stealth is optional Browserless capability, not a bypass guarantee; screenshots protected; public chat has no Settings access; typed-name deletes; en+vi; Settings/Data/Execution tabs; search/fetch stay separate tools and do not inherit the browser proxy.

## Problem Or Opportunity

HTTP/API tools cannot interact with JavaScript applications or portal workflows without an API. A fixed script alone cannot adapt to an unknown page layout. A separate hidden browser agent would duplicate Superstep's Agent loop and obscure approvals, trace and cost. The owner needs both adaptive navigation and repeatable recipes without a vendor-specific canvas taxonomy, with operator controls that stay flexible without silently weakening safety.

## Scope

### In Scope

- **Connections (operator layer):** reuse existing owner/org managed connection and tool discovery surfaces; support an isolated local Playwright worker **and** Browserless remote attachment in the first studio delivery. No browser process runs in the API process.
- **Required origin/domain whitelist:** every browser connection must configure at least one allowed origin/domain. Navigation, redirects and subresources outside the list are blocked. The same list applies to Browserless/remote paths. Empty whitelist is invalid and cannot be saved.
- **Proxy settings under Browser connection → Network / Proxy:** direct, operator-provided system default, or connection-specific proxy; address/protocol/authentication, encrypted credentials, explicit provider capability validation and stable routing for a live session. System default is explicit operator configuration, not accidental inheritance of host proxy variables. Search/Fetch do not silently inherit the browser proxy. No chat override and no silent fallback to direct.
- **Operator safety toggles on the connection:**
  - Require approval for mutating actions (click, fill, upload, download, evaluate JS). Default **OFF** (run immediately). Navigate, snapshot, extract and screenshot never wait on this toggle.
  - Allow evaluate JavaScript; allow upload; allow download (all available in v1; recommended that the operator enables them at connection level when needed).
  - Download max size and allowed content types.
  - Upload sources limited to authorised attachments/workspace files (never arbitrary host paths).
  - Session idle timeout (proposed default 30 minutes, configurable) and hard max session duration.
  - Action/page budget per session.
- **Always-on (not togglable):** block private/link-local/metadata IPs; treat page content as untrusted (never follow page instructions to reveal secrets or expand access); redact secrets in traces; no public-chat Settings access; kill-switch drains sessions without replaying writes.
- **Agent tools (builder layer):** bounded navigate, snapshot, click, fill, structured extraction, screenshot, upload, download and evaluate-JavaScript operations, managed by the existing Agent/model. Builder grants which tools are advertised to the model; ungranted tools are not discoverable at runtime. Builder cannot widen the connection whitelist or disable network enforcement. Browser tools on the same session run in order; unrelated tools retain current parallel behavior.
- **Runtime inputs:** fixed values, workflow bindings and model-filled tool arguments. No mandatory design-time start URL. Missing information asks the user through the existing chat/Human mechanism or returns a declared incomplete-input state. Search finds candidate URLs; it does not invent a missing identity or grant network permission. Any URL used to open the browser must pass the connection whitelist.
- **Web discovery/read:** reuse an existing MCP/HTTP search provider where available, with a small normalised search contract and one explicitly configured adapter for validation. Add bounded guarded fetch/extraction for read-only tasks. No mandatory paid provider and no browser launch for fetch-only work.
- **Recipes:** bounded typed action sequences with per-call arguments such as `url` and `order_id`; invoke through existing MCP nodes/Agent tool slots, or existing workflow-as-tool composition. Share runtime and action semantics with autonomous tools; no second orchestration language.
- **Sessions:** private to the effective execution principal, conversation (when chat-driven), run/Agent-tool group and connection. Persist across chat turns of the **same** conversation, same effective user/principal and same connection until idle timeout, hard max duration, cancel, conversation end or connection revoke. Still no promised live-browser survival across worker/browser crashes. Ordered same-session commands, fencing and explicit expired-session recovery remain required.
- **Security/reliability:** enforced network boundary covering destinations, redirects, subresources, DNS changes, browser networking and selected proxy paths; owner/org access checks; scoped login state; configurable mutating-action approval; conservative handling of unknown outcomes.
- **Exports (deferred after studio):** Python, TypeScript and project packages for Agent browser tools and recipes remain in the requirement as later work (TASK-0251, TASK-0252). Trigger: after studio browser tools are accepted and integrated. Secrets are externally supplied, not exported. Explicit refusal for a configured unsupported capability, never silent omission or MCP placeholders.
- **Experience:** current Settings/managed connections, Agent/MCP settings and run trace/chat; screenshots as protected artifacts filtered from public chat by default; clear statuses; offline fixtures/mock; bilingual handbook covering studio for the first milestone; an example workflow.
- **Stealth:** optional Browserless capability, disabled unless explicitly selected; unsupported settings fail clearly. Document that stealth is best-effort bot-detection mitigation, not a general firewall, access-control or CAPTCHA bypass guarantee.

### Out Of Scope

- A new vendor-specific Browser canvas node, a second built-in browser Agent loop, a browser marketplace, visual recorder or automatic conversion of arbitrary browsing history into a reliable recipe.
- Delegating whole tasks to Browser Use Cloud/Skyvern or another hosted browser Agent in this delivery; the remote provider in scope (Browserless) supplies a browser, not the decision loop.
- Automatic proxy rotation during a session, purchasing proxy services, proxy resale, unrestricted runtime proxy URLs supplied by chat/model, or automatic downgrade to direct networking after proxy failure.
- Guaranteed anti-bot/CAPTCHA bypass, challenge-solving subscriptions, automatic MFA handling, production logins/credential setup, OAuth consent flows, a full remote-desktop/live-browser product or general local-user Chrome control.
- Shell execution, payments or destructive website actions as initial browser operations. Evaluate JavaScript is page-context only (no Node/shell). Upload/download are bounded as above, not unrestricted host filesystem access.
- Interactive profile capture product is deferred; new persisted login profiles use operator-provisioned, origin-scoped state.
- Shipping local-only as a substitute for required Browserless support in the first studio delivery.
- Unrestricted private-network browsing, public endpoint exposure, release, deployment, account cutover, merging or implementation authorised by this planning-only request.
- First-milestone executable Python/TypeScript export packaging (deferred; see In Scope exports).

## Stakeholders Or Users

- Builder: attach browser tools to the current Agent; compose a stable recipe; bind values without copying credentials into a workflow; grant only the tools needed for that node.
- Chat user: provide a URL or a goal, answer missing-context questions and receive a grounded result or explicit incomplete/error state.
- Operator: configure browser infrastructure, whitelist, proxy, safety toggles and access policy; bound resources and manage encrypted login state.
- Developer: export executable workflow behavior with explicit external setup (later phase).

## Current Context

- DISC-0002 records inspected paths and research. Current MCP clients use one short session per call; generic managed operations assume a result ledger rather than a live page state.
- MCP export helpers are placeholders; `McpService.check_export` rejects managed connections. Deferred export work must not weaken existing refusals for other managed adapters.
- Parallel Agent slots, approval waits, child runs, effect ledger, queue fencing and central error/locale handling already exist.
- The interactive mockup is concept evidence, not approved production layout. It does not yet include the proxy section, whitelist editor or safety toggles and does not prove runtime, security or export behavior.
- Draft implementation PRs #303–#315 were started against the previous Proposed plan before this amendment; after Acceptance they must be reconciled with this package before merge (see PLAN-0006).

## Desired Behavior

1. Operator creates a browser connection with a non-empty origin whitelist, proxy mode, optional profile and safety toggles (mutating approval, allow JS/upload/download, download limits, session idle/max, action budget). Connection setup does not ask for a single fixed website URL beyond the whitelist.
2. Builder selects that connection and grants individual browser tools to the existing Agent. Ungranted tools are not advertised to the model. Builder cannot widen the whitelist or turn off always-on network enforcement.
3. A chat URL becomes a tool argument; a workflow-bound URL comes from the declared state field. If only a known organisation/task is available, a configured search tool supplies candidate URLs; insufficient context produces a question. Any URL that would open the browser must pass the whitelist.
4. Agent observes actual page state, selects granted actions, receives bounded results and repeats in the same scoped session until the goal, limit or a declared stop state is reached. Across chat turns of the same conversation the session may still be live until idle/max expiry.
5. A recipe receives `url` and other typed inputs on each call and executes its reviewed sequence. A changed layout fails visibly instead of silently changing the recipe into an autonomous Agent.
6. Proxy/provider/profile/whitelist selections apply throughout the session and are visible without exposing secrets. A capability or policy failure stops before the prohibited action.
7. Supported exported projects (later phase) reproduce these contracts with credentials supplied independently and without requiring a live Superstep instance.

## Business Rules

- Connection reference and execution authority come from saved, authorised workflow configuration. A model/chat URL is data, not permission to change connection, proxy, profile, whitelist or credentials.
- Shared org connections do not imply shared live cookies/tabs. Session isolation includes the existing visitor/app-user execution identity when present, not merely the workflow owner's ID.
- Default session lifetime spans chat turns of the same conversation / same principal / same connection, bounded by configurable idle timeout (proposed default 30 minutes) and a hard max duration. Child calls and resumptions must have an explicit binding. Share no session between unrelated conversations, runs or parallel owners. Crash recovery is not promised.
- A live session has one ordered command stream and a pinned proxy/provider/profile/whitelist configuration. A lock alone must not make same-round `navigate`/`click` execution order depend on thread scheduling.
- Observe results carry session/page generation references. Stale references and a lost session require re-observation; a ledger replay of an earlier snapshot does not restore page state.
- Mutating-action approval is connection-configurable and defaults to OFF for first delivery. When the toggle is ON, click/fill/upload/download/evaluate JS require the existing approval mechanism. Navigate/snapshot/extract/screenshot never wait on this toggle. The model/page cannot grant an exemption. Unknown possible effects, lost sessions and expired approvals never retry writes automatically.
- Page/search content is untrusted data. Do not follow page instructions to reveal credentials, expand access or approve another action.
- Profiles/cookies and proxy/provider secrets are encrypted and origin-scoped; no raw cookies, remote CDP tokens, secret-bearing URLs, page form values or arbitrary screenshots in public chat/trace/export output. Screenshots are filtered from public chat by default.
- Domain/origin whitelist applies to all browser-generated connections; securing only `page.goto` or the MCP endpoint is insufficient. A proxy/provider that cannot enforce the required destination policy is unsupported for this mode.
- Evaluate JS runs only in the page context; results are untrusted. Upload only from authorised attachments/workspace files. Download respects configured size and type limits.
- Delete/revoke/unlink of connections, profiles or recipes uses the shared typed-name confirmation and existing API conventions. Public chat never gains Settings access.
- Feature kill-switch drains/terminates sessions and preserves audit/outcome records; never repeat website writes as rollback.

## Constraints

- AGENTS.md, DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081; preserve source-onboarding approvals in project-specs.md.
- Python >=3.12 backend, existing React/shadcn frontend, SQLAlchemy/Alembic for persisted schema changes. Playwright/browser dependencies are a proposed addition to the isolated worker and (later) export environments; pin compatible versions during implementation. Browserless is the first remote provider.
- Preserve the standard Settings/Data/Execution node-config tabs. Mockup-specific browser tabs are not a waiver of docs/ui-conventions.md rule 12.
- Offline mock/dry-run starts no real browser, provider, search or proxy traffic. Real browser fixtures are opt-in, local, disposable and have a restricted test-only network policy.
- No implementation source changes before `factory ready` succeeds and the owner starts an implementation task against the accepted amended package.

## Acceptance Criteria

- AC1: Create/edit/discover/use owner/org browser connections through existing surfaces, including required non-empty origin whitelist, encrypted proxy/profile secrets, safety toggles, capability validation and typed-name deletion.
- AC2: Local isolated runtime and Browserless remote configuration perform the nine bounded operations (navigate, snapshot, click, fill, structured extraction, screenshot, upload, download, evaluate JS) under connection and Agent grants; deny cross-principal/session access and stale page references.
- AC3: Real browser fixtures prove outbound enforcement for navigation, redirects, subresources, DNS/proxy resolution, private/link-local/metadata destinations and whitelist denials on both local and Browserless paths. Unsupported remote/proxy enforcement fails closed without silently shipping local-only as complete.
- AC4: Chat URL, workflow URL, model-filled URL, search-then-browse, fetch-only and missing-context flows work without a fixed start URL or invented destination. Each binding is server-validated; off-whitelist URLs are denied before browser open.
- AC5: Same-session calls execute in deterministic call order despite parallel Agent slots; different sessions/unrelated tools can retain concurrency. Sessions persist across chat turns of the same conversation/principal/connection until idle/max/cancel. Cancel/expiry/fencing closes resources and stops late commands.
- AC6: When mutating approval is ON, allow/reject/expiry behave correctly. When OFF, mutating actions run immediately. Challenge-required, lost-session and uncertain external outcomes are visible, resumable where valid and never cause blind replay of effects. Navigate/snapshot/extract/screenshot never wait on the mutating-approval toggle.
- AC7: Recipes share the runtime, accept typed per-call arguments, expose bounded outputs through current tool surfaces and explicitly fail on selector/layout mismatch.
- AC8 (deferred): Python/TypeScript plain and project exports execute supported fixture scenarios independently, retaining bindings, proxy/policy, session ordering and approval semantics. No secret or silent stub escapes; unsupported capability gets a specific refusal. Not required for the first studio milestone; tracked by TASK-0251/0252 after studio acceptance.
- AC9: Accessible responsive en/vi UI and filtered trace/chat cover unconfigured, ready, running, waiting, failed, unknown, expired and completed states. Connection toggles and Agent tool grants are explicit. Screenshots remain owner-protected with retention and public-output filtering by default.
- AC10: Mock mode is offline; fixture/contract/security/UI tests, layer/envelope/locale checks, full project validation, bilingual studio handbook, task review/QA and studio integration evidence pass before the first milestone is complete. Export handbook/parity waits with AC8.

## Edge Cases

- URL absent/malformed or containing credentials; redirect to a private host or off-whitelist origin; page-origin changes after login; empty whitelist rejected on save; remote provider silently ignores proxy or whitelist; unsupported proxy authentication; proxy resolves a prohibited destination; browser crash after a possible write; two same-round calls target one tab; old snapshot is replayed; a public chat visitor guesses another session ID; approval arrives after expiry; connection is revoked mid-run; session idle timeout between chat turns; evaluate JS returns secrets from the DOM; upload from a disallowed path; download exceeds size/type limits; Browserless receives traffic the operator did not expect to leave the host.

## Assumptions

- The owner's instruction authorises recording this amended scope and proposing the task set, not implementation, a purchased provider, migration execution or a merge.
- Defaults/technical boundaries above are proposals for review. Browserless capability proofs and exact proxy capability matrix are implementation inputs to be proved, not observed capabilities.
- Proposed idle default is 30 minutes; hard max duration and action/page budgets are chosen concretely in the contract/runtime tasks and remain configurable.

## Open Questions

- Owner acceptance of this amended package (REQ/DES/ARCH/DEC/PLAN and tasks) is pending before moving studio delivery tasks to todo.
- Browserless destination/proxy/DNS enforcement parity must be proved in TASK-0244; if it fails, document refusal and ask the owner for another path — do not silently drop remote from the requirement.
- Deferred export packaging details remain for the later phase after studio acceptance.

## Related Artifacts

- `.factory-state/artifacts/DISC-0002-browser-tools-research.md`
- `.factory-state/artifacts/DES-0004-browser-tools.md`
- `.factory-state/artifacts/ARCH-0002-browser-tools.md`
- `.factory-state/decisions/DEC-0085-browser-tools.md`
- `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- `.factory-state/previews/browser-tool/browser-workspace.html` and `browser-tool-preview.html` (exploratory mockups)
- `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
