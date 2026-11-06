# Design Artifact

## Metadata

- Project: superstep
- Design ID: DES-0004
- Status: Accepted on 2026-11-06. Owner reviewed the amended package (relaxed approvals, cross-turn sessions, Browserless required, deferred exports, upload/download/evaluate JS, mandatory whitelist, two-layer toggles) and said "Ok triển khai" with instruction to sync latest develop before coding.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06 (Accepted; implementation authorised)
- Related Requirements: REQ-0086
- Related Architecture: ARCH-0002, DEC-0085

## Context

Use existing managed connection/MCP Settings, Agent/MCP config, run trace and chat question/approval surfaces. Follow `docs/ui-conventions.md`, existing `mcp-settings.tsx`, `managed-connection-fields.tsx`, `agent-settings.tsx` and shared presentation in `packages/react`. DISC-0002 records evidence. Mockups under `.factory-state/previews/browser-tool/` are concept references only; they are not a production layout or security waiver. Owner amendments on 2026-11-06 require a flexible-but-safe two-layer configuration UI with explicit toggles, required whitelist editor and written risk copy.

## Users And Goals

- Operator: set browser infrastructure, required origin whitelist, proxy/profile, safety toggles and access boundaries once without entering workflow URLs or exposing stored credentials.
- Builder: grant individual browser tools to an existing Agent, choose parameter bindings and compose reusable recipes; cannot widen whitelist or disable network enforcement.
- Chat user: provide a URL/goal, answer missing-information or approval requests and get an understandable outcome.

## Two-layer configuration

### A) Per browser connection (operator)

| Control | Default / rule | UI notes |
| --- | --- | --- |
| Origin/domain whitelist | Required, non-empty | Dedicated editor; cannot save empty; explains navigation/redirect/subresource enforcement |
| Proxy mode | Direct / operator system default / custom | No silent fallback; credentials write-only |
| Runtimes | Local Playwright and Browserless both supported in first delivery | Capability status per provider; refuse unsupported combinations with field errors |
| Optional login profile | Off / selected origin-scoped profile | Masked; typed-name delete |
| Require approval for mutating actions | **OFF** | Toggle with short risk hint; navigate/snapshot/extract/screenshot never wait |
| Allow evaluate JS / upload / download | Off unless operator enables | Separate toggles; recommend enabling only when needed |
| Download max size and allowed types | Concrete limits chosen in contract task | Shown when download allowed |
| Upload source rule | Authorised attachments/workspace only | Explained when upload allowed |
| Session idle timeout | Proposed **30 minutes**, configurable | Plus hard max duration field |
| Action/page budget | Configurable | Per-session |
| Always-on (not toggles) | Private IP block; untrusted page content; secret redaction; no public Settings; kill-switch | Documented as non-disableable |

### B) Per Agent node (builder)

- Grant tools individually: navigate, snapshot, click, fill, extract, screenshot, upload, download, evaluate JS.
- Ungranted tools are not advertised to the model and fail server-side if forged.
- Builder selects connection and bindings under existing Settings/Data/Execution tabs.
- Builder cannot edit connection whitelist, proxy, always-on network rules or operator toggles from the node form.

## User Flows

1. **Connection:** Settings → existing MCP/managed connection form → browser adapter/provider (local and/or Browserless) → required whitelist editor → Network / Proxy → safety toggles → optional scoped profile → resource/idle/budget bounds → save/discover. No single fixed website required beyond the whitelist. Edit masks stored secrets; test uses only explicitly authorised fixture/provider operations. Risk short-copy appears next to mutating-approval, JS, upload and download toggles.
2. **Autonomous browsing:** select browser tools under existing Agent Settings → choose connection and permitted tools → configure `url` as fixed, workflow-bound or Agent-filled → provide parameter description → configure round/action bounds under Execution. Agent task/model already belong to this node; no second browser Agent setting.
3. **Unknown URL:** user sends a URL, workflow supplies a declared value, or Agent invokes a configured search tool. Off-whitelist destinations are denied with a clear message before the browser opens. If context cannot identify a target, current chat/Human question flow asks for the missing organisation/site. Search and fetch are separate enabled tools with separate transport/proxy configuration.
4. **Multi-turn session:** later chat turns in the same conversation may reuse the live browser session for the same principal and connection until idle/max expiry. UI shows session age/idle remaining in authorised builder/operator views; public chat does not expose handles.
5. **Recipe:** existing generic tool configuration exposes a typed sequence, arguments, output mapping and connection. Saved recipe can be selected by an Agent or wrapped by an existing workflow tool. A recipe failure does not silently enable autonomous mode.
6. **Run:** existing trace groups browser operations under the Agent/recipe with tool, safe target, status and elapsed time. Inspector shows bounded observation and protected screenshot when authorised. Chat shows only the existing permitted subset and safe final output; screenshots filtered from public chat by default.
7. **Approval/recovery:** when mutating approval is ON, use existing approval UI; show the current site and bounded redacted action arguments. Reject returns a tool result. When OFF, mutating actions proceed without waiting. Expired/lost browser or unknown effect has a specific stop state and explicit next action; no “retry all clicks” button.

## Information Architecture

- Connection: provider (local / Browserless), control endpoint secret, Network / Proxy (direct / configured system default / custom), write-only proxy username/password, optional country only when provider supports it, **required whitelist**, safety toggles, profile reference, resource/idle/budget bounds.
- Node Settings: tools (nine operations), connection, Agent task/system prompt and optional recipe definitions.
- Node Data: per-parameter source/value/description, output/state fields and recipe inputs/results.
- Node Execution: per-action timeout, browser-action budget presentation, session scope/expiry presentation and relevant retry limitations.
- Existing node config remains **Settings · Data · Execution**, with en/vi labels and the established fixed order. No production Browser-only tab strip copied from the mockup.
- Recipe UI stays within generic tools; do not introduce a global recipe marketplace or new main-navigation product area.

## Surface Or Screen States

| State | Content and available action |
| --- | --- |
| Unconfigured / inaccessible | Name missing connection/profile/tool/whitelist and offer an authorised setup path; never expose another owner's resources. |
| Ready / unsupported capability | Show granted tools and effective provider/proxy/whitelist mode; field-level error for combinations the provider cannot enforce (including Browserless policy gaps). |
| Running | One ordered per-session operation stream; show current page generation without making tokens/handles public. |
| Missing input / searching | Explain the missing value or search operation; ask in chat/Human flow when needed. |
| Waiting approval | Only when mutating approval is ON; sanitised action, effective target and approve/reject; maintain existing focus and deadline behavior. |
| Challenge / expired session | Explicit state with a safe handoff or restart-from-observation option; no automatic CAPTCHA completion or cookie fabrication. Idle/max expiry between chat turns uses the same expired vocabulary. |
| Unknown effect | Explain that external outcome is not confirmed; do not present an automatic resend. |
| Completed / failed / cancelled | Safe result or specific error, cleanup outcome and authorised artifact access. |

## Interaction Behavior

- Parameter source switch preserves drafts but submits exactly one source; empty required fixed/state values fail validation. Model-filled URL does not inherit a guessed start URL. Whitelist denial is distinct from malformed URL.
- Whitelist editor requires at least one origin/domain; empty save is blocked with a translated error.
- Proxy credentials and CDP URL tokens stay write-only. A proxy failure does not flip silently to direct mode. Provider-only settings are disabled/hidden with an explanation when unsupported.
- Safety toggles show brief risk hints (SSRF/prompt-injection/session/JS/upload/download/screenshot/Browserless traffic/long-lived session). Always-on rules are listed as non-disableable help text, not fake toggles.
- Browser/search/fetch permission controls have explicit descriptions. Unchecking a browser tool affects discovery/schema and runtime validation, not merely UI visibility. Upload/download/evaluate JS require both connection allow and Agent grant.
- All delete/revoke/unlink actions use ConfirmDeleteDialog/useConfirmDelete with the exact item name and existing plain DELETE API.
- Screenshots require access checks and bounded retention. Trace text, page content and filenames are escaped; no untrusted HTML injected into Studio/chat. Public chat filters screenshots by default.

## Content And Messaging

- Every visible label, hint, error and status has matching en/vi locale keys and follows the glossary. Clearly label stealth as provider capability with no bypass guarantee.
- Distinguish connection error, missing input, whitelist denial, policy denial, challenge, session loss/idle expiry, timeout, unknown effect and successful extraction.
- URLs displayed to builders are sanitised; query secrets, proxy credentials, login fields and remote-control endpoints never appear in public chat.
- Risk short-copy for toggles summarises the PLAN/DEC risk table without replacing the handbook.

## Accessibility And Responsive Behavior

- Use existing shadcn components and tokens, labelled controls, keyboard navigation, normal tab order, visible focus and linked field errors. Focus enters/leaves approval/typed-delete dialogs through existing components.
- Status updates use polite announcements; operational status has text and not color alone. Reduced-motion preferences apply.
- Wrap long targets/tool names, stack paired controls on narrow screens and keep common toolbar size/alignment rules. No forced horizontal page overflow.
- Validate in en/vi and light/dark; save evidence outside Git or as CI artifacts, per owner precedent.

## UX Acceptance Criteria

- Operator can finish connection/whitelist/proxy/toggle setup and builder can attach granted browser tools without supplying a single fixed start URL.
- Chat URL, workflow URL, search-first, missing-context, multi-turn session reuse and recipe flows are inspectable with existing controls; no special Browser Agent node or extra config tabs.
- Credentials remain masked through create/edit/error/replay/export/public chat, and all destructive management actions require typing the item name.
- Keyboard/mobile/locale/theme checks cover the full state matrix, including idle expiry between turns, mutating-approval ON/OFF, whitelist denial and policy failure through a proxy or Browserless.

## Assumptions And Open Questions

- The owner requested planning amendments; detailed UX acceptance is pending. Proxy, whitelist and safety toggles must be present in production design even though the last mockup omits them.
- Optional interactive remote-login/live-view UX remains deferred; initial profiles are pre-provisioned operator state with clear domain restrictions.
- Exact idle default (30 minutes proposed), hard max and download type/size numbers are confirmed in the contract/runtime tasks.

## Impacted Artifacts

- REQ-0086, ARCH-0002, DEC-0085, DISC-0002 and PLAN-0006; existing UI conventions remain authoritative.
