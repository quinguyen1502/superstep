# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0086
- Status: Accepted for delivery — owner instruction on 2026-11-05
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Source: Owner discussion on browser tools, autonomous browsing, dynamic URLs, portable exports and connection-level proxies; followed by “Tiến hành ghi nhận yêu cầu và break task đi”.

## Summary

Let existing Superstep Agent nodes operate a real browser through scoped tools, and let workflows invoke reusable browser recipes through existing generic tool/MCP interfaces. Browser connections own infrastructure, network/proxy settings and optional login profiles. URLs are runtime arguments, including values supplied through chat, workflow state or search results. Python and TypeScript exports must execute the supported behavior outside Superstep.

## Problem Or Opportunity

HTTP/API tools cannot interact with JavaScript applications or portal workflows without an API. A fixed script alone cannot adapt to an unknown page layout. A separate hidden browser agent would duplicate Superstep's Agent loop and obscure approvals, trace and cost. The owner needs both adaptive navigation and repeatable recipes without a vendor-specific canvas taxonomy.

## Scope

### In Scope

- **Connections:** reuse existing owner/org managed connection and tool discovery surfaces; support an isolated local Playwright worker and a capability-checked remote browser connection. No browser process runs in the API process.
- **Proxy settings under Browser connection → Network / Proxy:** direct, operator-provided system default, or connection-specific proxy; address/protocol/authentication, encrypted credentials, explicit provider capability validation and stable routing for a live session. System default is explicit operator configuration, not accidental inheritance of host proxy variables. Search/Fetch do not silently inherit the browser proxy.
- **Agent tools:** bounded navigate, snapshot, click, fill, structured extraction and screenshot operations, managed by the existing Agent/model. Browser tools on the same session run in order; unrelated tools retain current parallel behavior.
- **Runtime inputs:** fixed values, workflow bindings and model-filled tool arguments. No mandatory design-time start URL. Missing information asks the user through the existing chat/Human mechanism or returns a declared incomplete-input state. Search finds candidate URLs; it does not invent a missing identity or grant network permission.
- **Web discovery/read:** reuse an existing MCP/HTTP search provider where available, with a small normalised search contract and one explicitly configured adapter for validation. Add bounded guarded fetch/extraction for read-only tasks. No mandatory paid provider and no browser launch for fetch-only work.
- **Recipes:** bounded typed action sequences with per-call arguments such as `url` and `order_id`; invoke through existing MCP nodes/Agent tool slots, or existing workflow-as-tool composition. Share runtime and action semantics with autonomous tools; no second orchestration language.
- **Sessions:** private to the effective execution principal, run, Agent/tool group and connection; retained between calls in that group, with expiry, cancellation, terminal cleanup, fencing and explicit expired-session recovery. No promised live-browser survival across worker/browser crashes or across separate chat turns.
- **Security/reliability:** enforced network boundary covering destinations, redirects, subresources, DNS changes, browser networking and selected proxy paths; owner/org access checks; scoped login state; conservative approval and unknown-outcome handling for possible effects.
- **Exports:** Python, TypeScript and project packages for Agent browser tools and recipes, including runtime helpers, dependencies/browser setup, dynamic bindings, network/proxy policy, session serialization and approvals. Secrets are externally supplied, not exported. Explicit refusal for a configured unsupported capability, never silent omission or MCP placeholders.
- **Experience:** current Settings/managed connections, Agent/MCP settings and run trace/chat; screenshots as protected artifacts, clear statuses, offline fixtures/mock, bilingual handbook and an example workflow.
- **Stealth:** optional provider-specific capability, disabled unless explicitly selected; unsupported settings fail clearly. Document that stealth is best-effort bot-detection mitigation, not a general firewall, access-control or CAPTCHA bypass guarantee.

### Out Of Scope

- A new vendor-specific Browser canvas node, a second built-in browser Agent loop, a browser marketplace, visual recorder or automatic conversion of arbitrary browsing history into a reliable recipe.
- Delegating whole tasks to Browser Use Cloud/Skyvern or another hosted browser Agent in this delivery; the remote provider in scope supplies a browser, not the decision loop.
- Automatic proxy rotation during a session, purchasing proxy services, proxy resale, unrestricted runtime proxy URLs supplied by chat/model, or automatic downgrade to direct networking after proxy failure.
- Guaranteed anti-bot/CAPTCHA bypass, challenge-solving subscriptions, automatic MFA handling, production logins/credential setup, OAuth consent flows, a full remote-desktop/live-browser product or general local-user Chrome control.
- Arbitrary JavaScript/evaluate, shell execution, uploads/downloads, payments or destructive website actions as initial browser operations. New persisted login profiles use operator-provisioned, origin-scoped state; an interactive profile capture product is deferred.
- Unrestricted private-network browsing, public endpoint exposure, release, deployment, account cutover, merging or implementation authorised by this planning-only request.

## Stakeholders Or Users

- Builder: attach browser tools to the current Agent; compose a stable recipe; bind values without copying credentials into a workflow.
- Chat user: provide a URL or a goal, answer missing-context questions and receive a grounded result or explicit incomplete/error state.
- Operator: configure browser infrastructure, proxy and access policy; bound resources and manage encrypted login state.
- Developer: export executable workflow behavior with explicit external setup.

## Current Context

- DISC-0002 records inspected paths and research. Current MCP clients use one short session per call; generic managed operations assume a result ledger rather than a live page state.
- MCP export helpers are placeholders; `McpService.check_export` rejects managed connections. This requirement needs a browser-specific export capability without weakening existing refusals for other managed adapters.
- Parallel Agent slots, approval waits, child runs, effect ledger, queue fencing and central error/locale handling already exist.
- The interactive mockup is concept evidence, not approved production layout. It does not yet include the proxy section and does not prove runtime, security or export behavior.

## Desired Behavior

1. Builder selects a browser connection and grants individual browser tools to the existing Agent. Connection setup does not ask for a website URL.
2. A chat URL becomes a tool argument; a workflow-bound URL comes from the declared state field. If only a known organisation/task is available, a configured search tool supplies candidate URLs; insufficient context produces a question.
3. Agent observes actual page state, selects actions, receives bounded results and repeats in the same scoped session until the goal, limit or a declared stop state is reached.
4. A recipe receives `url` and other typed inputs on each call and executes its reviewed sequence. A changed layout fails visibly instead of silently changing the recipe into an autonomous Agent.
5. Proxy/provider/profile selections apply throughout the session and are visible without exposing secrets. A capability or policy failure stops before the prohibited action.
6. Supported exported projects reproduce these contracts with credentials supplied independently and without requiring a live Superstep instance.

## Business Rules

- Connection reference and execution authority come from saved, authorised workflow configuration. A model/chat URL is data, not permission to change connection, proxy, profile, allowlist or credentials.
- Shared org connections do not imply shared live cookies/tabs. Session isolation includes the existing visitor/app-user execution identity when present, not merely the workflow owner's ID.
- Default session lifetime is one Agent invocation or one standalone recipe call; child calls and resumptions must have an explicit binding. Share no session between unrelated runs or parallel owners.
- A live session has one ordered command stream and a pinned proxy/provider/profile configuration. A lock alone must not make same-round `navigate`/`click` execution order depend on thread scheduling.
- Observe results carry session/page generation references. Stale references and a lost session require re-observation; a ledger replay of an earlier snapshot does not restore page state.
- Browser `click`, fill and keyboard-driven submission cannot be reliably classified as read-only from arbitrary page text. Default potential-effect operations require the existing approval mechanism unless an explicit reviewed bounded action policy permits them. The model/page cannot grant that exemption. Initial exposed tools exclude arbitrary script and generic keyboard submission.
- External outcome distinguishes confirmed, failed-before-effect and unknown. Unknown possible effects never retry automatically, including after timeout, fencing, recovery or time travel. Rejecting approval is returned to the model.
- Page/search content is untrusted data. Do not follow page instructions to reveal credentials, expand access or approve another action.
- Profiles/cookies and proxy/provider secrets are encrypted and origin-scoped; no raw cookies, remote CDP tokens, secret-bearing URLs, page form values or arbitrary screenshots in public chat/trace/export output.
- Domain policy applies to all browser-generated connections; securing only `page.goto` or the MCP endpoint is insufficient. A proxy/provider that cannot enforce the required destination policy is unsupported for this mode.
- Delete/revoke/unlink of connections, profiles or recipes uses the shared typed-name confirmation and existing API conventions. Public chat never gains Settings access.

## Constraints

- AGENTS.md, DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081; preserve source-onboarding approvals in project-specs.md.
- Python >=3.12 backend, existing React/shadcn frontend, SQLAlchemy/Alembic for persisted schema changes. Playwright/browser dependencies are a proposed addition to the isolated worker and export environments; pin compatible versions during implementation.
- Preserve the standard Settings/Data/Execution node-config tabs. Mockup-specific browser tabs are not a waiver of docs/ui-conventions.md rule 12.
- Offline mock/dry-run starts no real browser, provider, search or proxy traffic. Real browser fixtures are opt-in, local, disposable and have a restricted test-only network policy.
- No implementation source changes before `factory ready` succeeds and the owner starts an implementation task.

## Acceptance Criteria

- AC1: Create/edit/discover/use owner/org browser connections through existing surfaces, including encrypted proxy/profile secrets, capability validation and typed-name deletion.
- AC2: Local isolated runtime and the validated remote-browser configuration perform the six bounded operations; deny cross-principal/session access and stale page references.
- AC3: Real browser fixtures prove outbound enforcement for navigation, redirects, subresources, DNS/proxy resolution and private/link-local destinations. Unsupported remote/proxy enforcement fails closed.
- AC4: Chat URL, workflow URL, model-filled URL, search-then-browse, fetch-only and missing-context flows work without a fixed start URL or invented destination. Each binding is server-validated.
- AC5: Same-session calls execute in deterministic call order despite parallel Agent slots; different sessions/unrelated tools can retain concurrency. Cancel/expiry/fencing closes resources and stops late commands.
- AC6: Approval allow/reject, challenge-required, lost-session and uncertain external outcomes are visible, resumable where valid and never cause blind replay of effects.
- AC7: Recipes share the runtime, accept typed per-call arguments, expose bounded outputs through current tool surfaces and explicitly fail on selector/layout mismatch.
- AC8: Python/TypeScript plain and project exports execute supported fixture scenarios independently, retaining bindings, proxy/policy, session ordering and approval semantics. No secret or silent stub escapes; unsupported capability gets a specific refusal.
- AC9: Accessible responsive en/vi UI and filtered trace/chat cover unconfigured, ready, running, waiting, failed, unknown, expired and completed states. Screenshots remain owner-protected with retention and public-output filtering.
- AC10: Mock mode is offline; fixture/contract/security/export tests, layer/envelope/locale/UI checks, full project validation, bilingual documentation, task review/QA and final integration evidence pass before completion.

## Edge Cases

- URL absent/malformed or containing credentials; redirect to a private host; page-origin changes after login; expired profile; remote provider silently ignores proxy; unsupported proxy authentication; proxy resolves a prohibited destination; browser crash after a possible write; two same-round calls target one tab; old snapshot is replayed; a public chat visitor guesses another session ID; approval arrives after expiry; connection is revoked mid-run.

## Assumptions

- The owner's instruction authorises recording this scope and proposing the task set, not implementation, a purchased provider, migration execution or a merge.
- Defaults/technical boundaries above are proposals for review. External provider selection and exact proxy capability matrix are implementation inputs to be proved, not observed capabilities.

## Open Questions

- Owner acceptance of the complete task set and proposed conservative approval/default network policy is pending before moving delivery tasks to todo.
- The first remote endpoint and search adapter are selected and capability-tested in the relevant tasks; no live account is needed to finish planning.
- Decide through the runtime contract task whether any initial remote/proxy combination cannot meet enforcement/export parity; document a scoped refusal or amend the proposed scope before implementation proceeds past that gate.

## Related Artifacts

- `.factory-state/artifacts/DISC-0002-browser-tools-research.md`
- `.factory-state/artifacts/DES-0004-browser-tools.md`
- `.factory-state/artifacts/ARCH-0002-browser-tools.md`
- `.factory-state/decisions/DEC-0085-browser-tools.md`
- `.factory-state/artifacts/PLAN-0006-browser-tools.md`
- `.factory-state/previews/browser-tool/browser-workspace.html` and `browser-tool-preview.html` (exploratory mockups)
- `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`

## Owner Delivery Authorisation — 2026-11-05

The owner instructed: “Pull develop về branch hiện tại, và tiến hành chuỗi task này.” This accepts the proposed browser delivery scope and starts PLAN-0006 in dependency order. This supersedes earlier planning-only/pending-start statements; source onboarding approval statuses are unchanged. Implementation, fixture validation and task PRs are authorised; merges, production/provider setup, release and deployment are not. Task branches may stack on the published planning package; dependent implementation tasks require predecessor review/QA and an explicitly documented stack.
