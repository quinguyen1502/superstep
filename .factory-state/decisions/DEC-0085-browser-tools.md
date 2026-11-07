# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0085
- Status: Accepted on 2026-11-06. Owner reviewed the amended package (relaxed approvals, cross-turn sessions, Browserless required, deferred exports, upload/download/evaluate JS, mandatory whitelist, two-layer toggles) and said "Ok triển khai" with instruction to sync latest develop before coding. On 2026-11-07 the owner approved decision 10 and then asked for the task split. TASK-0261 is merged in PR #329 (`10300e20`, REV-0251, QA-0251). TASK-0262 is done in PR #334 (REV-0254, QA-0254) and is not merged. AC11 stays open until PR #334 merges.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-07 (TASK-0261 merged in PR #329; TASK-0262 done in PR #334, not merged)
- Related Requirements: REQ-0086
- Related Architecture: ARCH-0002
- Related Tasks: see PLAN-0006

## Context

The owner researched browser tools, requested evolving mockups for autonomous navigation and dynamic URLs, discussed connection-level proxies, and then explicitly requested requirement capture and task breakdown. Current managed/MCP surfaces fit tool selection, but their per-call session and export behavior do not implement browser continuity or portability (DISC-0002). On 2026-11-06 the owner reviewed the proposed package, requested six product amendments plus a flexible-but-safe two-layer configuration model with explicit toggles and written risk analysis, then accepted the amended package and authorised implementation.

## Decision Proposed

1. Separate **browser connections**, **browser tools on existing Agents**, and **typed reusable recipes**. Reuse generic MCP/tool/workflow-tool surfaces; do not add a vendor-specific canvas node or a hidden second browser Agent.
2. Start URLs are optional task data. Per-tool arguments support fixed, workflow-bound and Agent-filled values; configured search/fetch remain separate tools. Missing context results in a question or explicit incomplete state. Any URL used to open the browser must pass the connection origin whitelist.
3. Proxy belongs to the browser connection, with explicit direct/operator-default/custom modes, encrypted auth, capability validation and stable routing for a live session. No runtime chat proxy override or automatic direct fallback.
4. First studio delivery requires **both** isolated local Playwright **and** Browserless (https://www.browserless.io / CDP/browser API) as the first remote provider. Provider-specific stealth is optional and never presented as a universal firewall/CAPTCHA/access bypass. If Browserless cannot prove destination/proxy/DNS enforcement equivalent to the local worker, document the gap and refuse the unsupported mode — do not silently weaken policy or treat local-only as satisfying the remote requirement.
5. Bind session identity and command order to the trusted conversation (when chat-driven), principal, run/Agent group and connection. **Persist the live browser session across chat turns** of the same conversation, same effective user/principal and same connection until idle timeout (proposed default 30 minutes, configurable), hard max duration, cancel, conversation end or connection revoke. Retain existing unrelated parallel calls, approvals, fencing and result order. Lost browser state after worker/browser crash is not reconstructed by the generic result ledger and is not promised to survive.
6. Require effective network enforcement on navigation, redirects, all page-generated traffic and proxy/remote paths, including a **mandatory non-empty origin/domain whitelist** per connection. Unsupported combinations fail closed. **Mutating-action approval defaults to OFF** for first delivery: navigate, snapshot, structured extraction and screenshot never wait; click, fill, upload, download and evaluate JavaScript run immediately unless the connection turns “require approval” ON for those mutating actions. Unknown effects, lost sessions and expired approvals never blindly replay writes.
7. Deliver nine bounded first-version operations: navigate, snapshot, click, fill, structured extraction, screenshot, **upload**, **download** and **evaluate JavaScript**, with connection allow-toggles and Agent tool grants. Upload only from authorised attachments/workspace files; download size/type limited; evaluate JS sandboxed to page context (no Node/shell); results treated as untrusted page data.
8. Use a **two-layer configuration model**: (A) connection/operator controls for whitelist, proxy, runtimes, profile, mutating-approval toggle, allow-JS/upload/download, download limits, session idle/max and action/page budget; always-on private-IP block, untrusted page content, secret redaction, no public Settings and kill-switch. (B) Agent-node/builder grants of individual tools; ungranted tools are not advertised; builder cannot widen whitelist or disable network enforcement.
9. **Defer executable Python/TypeScript and project exports** (TASK-0251, TASK-0252) until after studio browser tools are accepted and integrated. Preserve existing managed export refusals. First studio milestone completion does not require AC8 export evidence.
10. **Two export drivers** (owner wording approved 2026-11-07). The fixture driver `memory` stays the TASK-0251 and TASK-0252 contract: static HTTP GET, no redirect following, click only through an `href`, fill stored in session memory, evaluate limited to `document.title` and `document.body.innerText` on the stored HTML, and whitelisted private origins reachable on this driver only. A later implementation may add live `playwright` and `browserless` drivers that keep one browser and one page per alias until idle, lifetime expiry, or process exit. That page is not a Studio conversation lease. On those drivers, navigate and an `href` click pass the whitelist before open, a click without an `href` and a fill act on the live element, and the runtime stores the resulting HTML for snapshot and extract. Live evaluate is a page-context expression of at most 4,000 characters when the connection allows it, with an untrusted result and no Node, shell, or filesystem access. Every live redirect hop stays on the whitelist and off private addresses, or it does not become the current page. Profile JSON supplied in `SUPERSTEP_BROWSER_PROFILE_*` applies cookies and localStorage only to an origin that is both listed and whitelisted, and only before the first navigation. The generated file contains the variable name. Invalid JSON does not open a page. `max_pages` counts document navigations and refuses the next one. `stealth` is passed only for Browserless. Upload, download, and screenshot bytes stay refused in the export. Screenshot results stay `{captured: true, inline_bytes: false}`. Other managed adapters, MCP stdio/HTTP, and the retriever stay explicit stubs. This decision does not reopen TASK-0251 or TASK-0252. The Python half is TASK-0261, done in PR #329 (REV-0251, QA-0251) and not merged yet. TASK-0262 is not started.

## Risk analysis (toggles and always-on controls)

| Control | Risk if mis-set / abused | Mitigation in this decision |
| --- | --- | --- |
| Origin whitelist (required, non-empty) | SSRF / browsing unexpected hosts; redirect to private or attacker domain | Mandatory; empty invalid; applies to navigation, redirects, subresources, local and Browserless; search/fetch destinations used to open browser must pass it |
| Proxy mode | Traffic leaves unintended path; silent direct fallback after proxy failure | Explicit modes only; no chat override; no silent fallback to direct |
| Local + Browserless runtimes | Browserless sees page traffic/cookies; weaker remote DNS/destination enforcement | Capability proof required; refuse unsupported mode; document gap; secrets encrypted; stealth off by default |
| Optional login profile | Session hijack via leftover cookies across principals/origins | Origin-scoped encrypted profiles; no shared live tabs across principals; revoke invalidates sessions |
| Require approval for mutating actions (default OFF) | Unintended clicks/fills/uploads/downloads/JS on live sites | Toggle visible; default flexible; when ON uses existing approval; unknown/lost/expired never auto-replay writes |
| Allow evaluate JS | DOM/token exfiltration; prompt-injection-driven script | Connection allow + Agent grant both required; page-context only; results untrusted; cannot expand whitelist/access |
| Allow upload | Malware or unintended file send from host | Only authorised attachments/workspace files; connection allow + Agent grant; no arbitrary host paths |
| Allow download | Oversized/malicious files into workspace | Max size and allowed types; connection allow + Agent grant |
| Session persist across turns (default ON, 30m idle) | Long-lived sessions after user walks away; leftover authenticated state | Idle timeout + hard max; cancel/conversation-end/revoke drains; crash survival not promised |
| Action/page budget | Runaway Agent loops | Per-session budget enforced |
| Screenshots | PII leak to public chat/trace | Protected artifacts; filtered from public chat by default; retention bounds |
| Page content to model | Prompt injection from page text | Always treat as untrusted; never follow page instructions to reveal secrets or expand access |
| Private/link-local/metadata IPs | Classic SSRF to internal services | Always blocked; not togglable |
| Stealth (Browserless, default off) | False sense of firewall/CAPTCHA bypass | Documented best-effort only; off unless chosen |
| Live export driver | A long-lived Playwright page can follow a redirect off the whitelist or apply profile cookies too broadly | One page per alias until idle, lifetime, or process exit; every hop rechecked; profile JSON applies only to origins that are both listed and whitelisted; no cookies in the generated file |
| Kill-switch | Incomplete drain leaving writes to replay | Drain/terminate; preserve audit; never replay writes as rollback |

Recommended safe-flexible defaults: whitelist required; mutating approval OFF but visible; JS/upload/download available in v1 but only effective when connection allows and builder grants the tools; session persist ON with 30m idle; screenshots filtered from public chat by default; stealth off unless chosen.

## Rationale

This preserves Superstep's LangGraph Agent orchestration, makes dynamic URLs ordinary runtime inputs and gives operators one source of infrastructure/network authority with explicit safety toggles. The design supports both adaptive work and repeatable automation without confusing browser infrastructure with a deferred portable export packaging phase or a hosted browser-Agent service. Flexible defaults keep browsing usable while always-on network and trust boundaries stay closed.

## Alternatives Considered

- Fixed URL and fixed steps only: useful for recipes but does not meet chat-supplied/unknown-target requirements.
- A new Browser Agent node with its own model loop: duplicates current Agent controls and obscures approvals/trace.
- A hosted browser Agent API for every call: quick integration but different control/portability semantics; deferred.
- A global change to generic MCP session lifetime: broader compatibility risk without solving ownership, proxy enforcement and browser recovery.
- Require approval for every possible-effect action by default: safer but too interruptive for the owner's flexible-but-safe browsing goal; rejected in favour of connection-level mutating-approval toggle defaulting OFF.
- Local-only first delivery if remote proof fails: rejected; remote (Browserless) is required; failure becomes an explicit refusal and owner decision, not a silent scope shrink.
- Keep exports on the first-delivery critical path: rejected; owner asked to finish studio first and defer TASK-0251/0252.

## Impacts And Risks

- New scoped worker/session, network/proxy/whitelist and (later) export contracts; potential schema/dependency additions must follow normal implementation review.
- Existing MCP/Agent settings and the standard Settings/Data/Execution tabs remain the product entry points. Mockup tabs are illustrative.
- Profile capture, provider credentials, live proxy selection and public deployment are operator actions outside this planning request.
- Remote/proxy policy enforcement and Browserless capability proofs are release gates, not promises inferred from CDP availability.
- Draft implementation PRs #303–#315 started against the previous Proposed plan and will need reconciliation after this amendment is accepted (see PLAN-0006).

## Approval

- Approved By: Thái Quí Nguyễn (owner)
- Approved On: 2026-11-06 (Asia/Saigon)
- Scope And Limits: the owner accepted the amended package and authorised implementation into `develop` ("Ok triển khai", sync latest develop first). One task PR per delivery task; merge only when required checks are green. No release/version bump authorised by this acceptance. TASK-0251/0252 remain deferred.
- 2026-11-07 addendum: the owner approved decision 10 ("ok ghi vào"). The approval covers that wording only. It does not merge the fixture-export pull requests, create live-driver tasks, or authorise implementation of decision 10.

## Review Or Revisit Trigger

- Owner reopens this decision; Browserless destination/proxy/DNS proof fails; interactive profile capture, hosted browser-Agent integration or first-milestone export packaging is pulled forward; toggle defaults prove too permissive or too interruptive in practice.
