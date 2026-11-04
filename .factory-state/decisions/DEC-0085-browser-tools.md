# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0085
- Status: Proposed — not an approved technology or implementation decision
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Related Requirements: REQ-0086
- Related Architecture: ARCH-0002
- Related Tasks: see PLAN-0006

## Context

The owner researched browser tools, requested evolving mockups for autonomous navigation and dynamic URLs, discussed connection-level proxies, and then explicitly requested requirement capture and task breakdown. Current managed/MCP surfaces fit tool selection, but their per-call session and export behavior do not implement browser continuity or portability (DISC-0002).

## Decision Proposed

1. Separate **browser connections**, **browser tools on existing Agents**, and **typed reusable recipes**. Reuse generic MCP/tool/workflow-tool surfaces; do not add a vendor-specific canvas node or a hidden second browser Agent.
2. Start URLs are optional task data. Per-tool arguments support fixed, workflow-bound and Agent-filled values; configured search/fetch remain separate tools. Missing context results in a question or explicit incomplete state.
3. Proxy belongs to the browser connection, with explicit direct/operator-default/custom modes, encrypted auth, capability validation and stable routing for a live session. No runtime chat proxy override or automatic direct fallback.
4. Prefer isolated local Playwright plus a capability-checked remote browser provider. Provider-specific stealth is optional and never presented as a universal firewall/CAPTCHA/access bypass.
5. Bind session identity and command order to the trusted run/principal/Agent group. Retain existing unrelated parallel calls, approvals, fencing and result order. Lost browser state is not reconstructed by the generic result ledger.
6. Require effective network enforcement on navigation, redirects, all page-generated traffic and proxy/remote paths. Unsupported combinations fail closed. Default possible-effect actions are approval-gated unless an explicit reviewed action policy allows them.
7. Deliver executable Python/TypeScript and project exports with the supported behavior and externally supplied secrets. Preserve existing managed export refusals for unrelated adapters and explicitly reject unsupported browser capabilities.

## Rationale

This preserves Superstep's LangGraph Agent orchestration, makes dynamic URLs ordinary runtime inputs and gives operators one source of infrastructure/network authority. The design supports both adaptive work and repeatable automation without confusing browser infrastructure with a delegated browser Agent service.

## Alternatives Considered

- Fixed URL and fixed steps only: useful for recipes but does not meet chat-supplied/unknown-target requirements.
- A new Browser Agent node with its own model loop: duplicates current Agent controls and obscures approvals/trace.
- A hosted browser Agent API for every call: quick integration but different control/portability semantics; deferred.
- A global change to generic MCP session lifetime: broader compatibility risk without solving ownership, proxy enforcement and browser recovery.

## Impacts And Risks

- New scoped worker/session, network/proxy and export contracts; potential schema/dependency additions must follow normal implementation review.
- Existing MCP/Agent settings and the standard Settings/Data/Execution tabs remain the product entry points. Mockup tabs are illustrative.
- Profile capture, provider credentials, live proxy selection and public deployment are operator actions outside this planning request.
- Remote/proxy policy enforcement and arbitrary-page effect classification are release gates, not promises inferred from SDK support.

## Approval

- Approved By: no detailed design approver recorded yet.
- Approved On: pending.
- Scope And Limits: the owner authorised writing the requirement and proposed task decomposition on 2026-11-03. No implementation, migration execution, dependency installation, merge, deployment or release authorisation is inferred.

## Review Or Revisit Trigger

- Owner accepts/amends the proposed task set; initial provider/proxy proof fails; cross-turn browser persistence, arbitrary files/scripts or a hosted browser-Agent integration enters scope.
