# Design Artifact

## Metadata

- Project: superstep
- Design ID: DES-0004
- Status: Accepted for delivery — owner instruction on 2026-11-05; production UI follows existing conventions
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Related Requirements: REQ-0086
- Related Architecture: ARCH-0002, DEC-0085

## Context

Use existing managed connection/MCP Settings, Agent/MCP config, run trace and chat question/approval surfaces. Follow `docs/ui-conventions.md`, existing `mcp-settings.tsx`, `managed-connection-fields.tsx`, `agent-settings.tsx` and shared presentation in `packages/react`. DISC-0002 records evidence. Mockups under `.factory-state/previews/browser-tool/` are concept references only; they are not a production layout or security waiver.

## Users And Goals

- Operator: set browser infrastructure, proxy/profile and access boundaries once without entering workflow URLs or exposing stored credentials.
- Builder: grant browser tools to an existing Agent, choose parameter bindings and compose reusable recipes.
- Chat user: provide a URL/goal, answer missing-information or approval requests and get an understandable outcome.

## User Flows

1. **Connection:** Settings → existing MCP/managed connection form → browser adapter/provider → Network / Proxy → optional scoped profile → destination policy and bounds → save/discover. No fixed website required. Edit masks stored secrets; test uses only explicitly authorised fixture/provider operations.
2. **Autonomous browsing:** select browser tools under existing Agent Settings → choose connection and permitted tools → configure `url` as fixed, workflow-bound or Agent-filled → provide parameter description → configure round/action bounds under Execution. Agent task/model already belong to this node; no second browser Agent setting.
3. **Unknown URL:** user sends a URL, workflow supplies a declared value, or Agent invokes a configured search tool. If context cannot identify a target, current chat/Human question flow asks for the missing organisation/site. Search and fetch are separate enabled tools with separate transport/proxy configuration.
4. **Recipe:** existing generic tool configuration exposes a typed sequence, arguments, output mapping and connection. Saved recipe can be selected by an Agent or wrapped by an existing workflow tool. A recipe failure does not silently enable autonomous mode.
5. **Run:** existing trace groups browser operations under the Agent/recipe with tool, safe target, status and elapsed time. Inspector shows bounded observation and protected screenshot when authorised. Chat shows only the existing permitted subset and safe final output.
6. **Approval/recovery:** use existing approval UI; show the current site and bounded redacted action arguments. Reject returns a tool result. Expired/lost browser or unknown effect has a specific stop state and explicit next action; no “retry all clicks” button.

## Information Architecture

- Connection: provider, control endpoint secret, Network / Proxy (direct / configured system default / custom), write-only proxy username/password, optional country only when provider supports it, profile reference, destination policy, resource/idle bounds.
- Node Settings: tools, connection, Agent task/system prompt and optional recipe definitions.
- Node Data: per-parameter source/value/description, output/state fields and recipe inputs/results.
- Node Execution: per-action timeout, browser-action budget, session scope/expiry presentation and relevant retry limitations.
- Existing node config remains **Settings · Data · Execution**, with en/vi labels and the established fixed order. No production Browser-only tab strip copied from the mockup.
- Recipe UI stays within generic tools; do not introduce a global recipe marketplace or new main-navigation product area.

## Surface Or Screen States

| State | Content and available action |
| --- | --- |
| Unconfigured / inaccessible | Name missing connection/profile/tool and offer an authorised setup path; never expose another owner's resources. |
| Ready / unsupported capability | Show granted tools and effective provider/proxy mode; field-level error for combinations the provider cannot enforce. |
| Running | One ordered per-session operation stream; show current page generation without making tokens/handles public. |
| Missing input / searching | Explain the missing value or search operation; ask in chat/Human flow when needed. |
| Waiting approval | Sanitised action, effective target and approve/reject; maintain existing focus and deadline behavior. |
| Challenge / expired session | Explicit state with a safe handoff or restart-from-observation option; no automatic CAPTCHA completion or cookie fabrication. |
| Unknown effect | Explain that external outcome is not confirmed; do not present an automatic resend. |
| Completed / failed / cancelled | Safe result or specific error, cleanup outcome and authorised artifact access. |

## Interaction Behavior

- Parameter source switch preserves drafts but submits exactly one source; empty required fixed/state values fail validation. Model-filled URL does not inherit a guessed start URL.
- Proxy credentials and CDP URL tokens stay write-only. A proxy failure does not flip silently to direct mode. Provider-only settings are disabled/hidden with an explanation when unsupported.
- Browser/search/fetch permission controls have explicit descriptions. Unchecking a browser tool affects discovery/schema and runtime validation, not merely UI visibility.
- All delete/revoke/unlink actions use ConfirmDeleteDialog/useConfirmDelete with the exact item name and existing plain DELETE API.
- Screenshots require access checks and bounded retention. Trace text, page content and filenames are escaped; no untrusted HTML injected into Studio/chat.

## Content And Messaging

- Every visible label, hint, error and status has matching en/vi locale keys and follows the glossary. Clearly label stealth as provider capability with no bypass guarantee.
- Distinguish connection error, missing input, policy denial, challenge, session loss, timeout, unknown effect and successful extraction.
- URLs displayed to builders are sanitised; query secrets, proxy credentials, login fields and remote-control endpoints never appear in public chat.

## Accessibility And Responsive Behavior

- Use existing shadcn components and tokens, labelled controls, keyboard navigation, normal tab order, visible focus and linked field errors. Focus enters/leaves approval/typed-delete dialogs through existing components.
- Status updates use polite announcements; operational status has text and not color alone. Reduced-motion preferences apply.
- Wrap long targets/tool names, stack paired controls on narrow screens and keep common toolbar size/alignment rules. No forced horizontal page overflow.
- Validate in en/vi and light/dark; save evidence outside Git or as CI artifacts, per owner precedent.

## UX Acceptance Criteria

- Builder can finish connection/proxy setup and attach browser tools without supplying a fixed URL.
- Chat URL, workflow URL, search-first, missing-context and recipe flows are inspectable with existing controls; no special Browser Agent node or extra config tabs.
- Credentials remain masked through create/edit/error/replay/export/public chat, and all destructive management actions require typing the item name.
- Keyboard/mobile/locale/theme checks cover the full state matrix, including expiry during approval and policy failure through a proxy.

## Assumptions And Open Questions

- The owner requested planning; detailed UX approval is pending. Proxy settings were discussed after the last mockup and must be added in production design, not assumed present in the prototype.
- Optional interactive remote-login/live-view UX is deferred; initial profiles are pre-provisioned operator state with clear domain restrictions.

## Impacted Artifacts

- REQ-0086, ARCH-0002, DEC-0085, DISC-0002 and PLAN-0006; existing UI conventions remain authoritative.

## Owner Delivery Authorisation — 2026-11-05

The owner instructed: “Pull develop về branch hiện tại, và tiến hành chuỗi task này.” This accepts the proposed browser delivery scope and starts PLAN-0006 in dependency order. This supersedes earlier planning-only/pending-start statements; source onboarding approval statuses are unchanged. Implementation, fixture validation and task PRs are authorised; merges, production/provider setup, release and deployment are not. Task branches may stack on the published planning package; dependent implementation tasks require predecessor review/QA and an explicitly documented stack.
