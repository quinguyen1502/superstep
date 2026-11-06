# Architecture Artifact

## Metadata

- Project: superstep
- Architecture ID: ARCH-0002
- Status: Accepted on 2026-11-06. Owner reviewed the amended package (relaxed approvals, cross-turn sessions, Browserless required, deferred exports, upload/download/evaluate JS, mandatory whitelist, two-layer toggles) and said "Ok triển khai" with instruction to sync latest develop before coding.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06 (Accepted; implementation authorised)
- Related Requirements: REQ-0086

## Context

DISC-0002 documents the short-lived generic MCP transport, existing managed connection/outcome contracts, parallel Agent slots, shared HTTP guard and placeholder/refused exports. These are reuse boundaries, not proof that native browser egress/session behavior already exists. Backend layering remains DEC-0009. Owner amendments on 2026-11-06 require Browserless in the first studio delivery, mandatory origin whitelist, session persistence across chat turns, nine tools including upload/download/evaluate JS, relaxed mutating-approval defaults, deferred exports and a two-layer config model.

## Decision Or Proposal

1. Expose a browser tool family and recipes through current managed discovery/call surfaces. Keep the current Agent expansion/model/provider loop. Connection metadata fixes infrastructure and authority; runtime arguments specify a task target; Agent grants select which of the nine tools are advertised.
2. Introduce a small versioned worker command contract with isolated provider implementations: local Playwright **and** Browserless remote attachment (required for first studio delivery). Run services bind an execution context to the tool port; engine modules do not import services/repositories or learn provider secrets.
3. Reuse the encrypted connection store where it fits. Add only schema needed for scoped profiles, **required origin whitelist**, safety toggles, session metadata (including conversation-scoped persistence), generation/fencing and browser artifact references, via SQLAlchemy/Alembic. No raw SQL or general plugin framework.
4. Enforce browsing destinations outside untrusted page code, at the network boundary that actually connects/resolves targets, including the connection whitelist for navigation, redirects and subresources. Local worker has no direct escape path around its controlled egress. Browserless and custom proxy modes require equivalent tested enforcement or explicit capability refusal — never silent local-only completion of the remote requirement.
5. Reuse existing snapshot/templating/tool arguments for fixed/state/model bindings. Add narrow metadata for missing binding modes rather than a second expression language. Optional start-page input is ordinary task data and must pass the whitelist before browser open.
6. Keep search, fetch and browser separate. Normalise one configured search provider through existing MCP/HTTP where possible; bounded HTTP fetch reuses guarded transport and does not load browser cookies or inherit its proxy implicitly. Search results used to open the browser must still pass the whitelist.
7. Keep recipes a bounded sequence of the same actions, with typed inputs/outputs and versioned snapshot per run. Prefer current workflow-as-tool composition to a separate recipe runtime. If a lightweight stored action definition is needed, justify it in the contract task.
8. **Defer** self-contained Python/TypeScript export helpers and project packaging (TASK-0251, TASK-0252) until after studio acceptance. Studio architecture must not invent export-only shortcuts that would make later export impossible, but first-milestone completion does not require executable export evidence.

## Boundaries And Interfaces

- API → services for connection/profile/recipe/whitelist/toggle visibility, CRUD, capabilities and artifact access; services → repositories for persisted metadata and → isolated worker control client for browser execution (local Playwright worker and Browserless control/CDP).
- Engine sees a typed port bound by RunService: operation, arguments and existing operation key plus trusted execution context. Context includes effective resource principal/visitor scope, conversation id when chat-driven, run, Agent/tool group, connection/version (including whitelist and toggle snapshot), lease/fence and ordered command identity; model-supplied fields cannot replace it.
- Worker commands/results are versioned bounded JSON. Result carries status, safe observation/extraction, page generation references, timing and optional private artifact reference; never raw Page/Browser objects or decrypted secrets.
- First-version capability vocabulary: navigate, snapshot, click, fill, structured extract, screenshot, **upload**, **download**, **evaluate_js**. Upload arguments reference authorised attachment/workspace file ids only. Download results are size/type bounded artifacts. Evaluate JS executes only in page context; return value is untrusted data. A recipe invokes those same commands in sequence subject to connection allows and Agent grants.
- Local/Browserless provider capabilities declare network enforcement, whitelist enforcement, proxy protocol/auth mode, scoped storage-state support, bounded screenshot/upload/download support and (later) export support. Do not infer these from the presence of a CDP URL.
- Trusted operator-configured worker/CDP control-plane endpoints have a separate deployment allowlist and authentication from browsed website targets. An explicitly configured internal worker or Browserless control endpoint must never enable private-network navigation for page/chat arguments.
- Proxy modes: direct, explicit operator default, connection-specific. Target validation, whitelist and remote DNS constraints apply to the proxy path too; no unapproved bypass list, arbitrary host environment inheritance or fallback route.
- Two-layer config: connection snapshot pins whitelist, proxy, provider, profile, mutating-approval flag, allow-js/upload/download, download limits, idle/max and budgets for the life of a session. Agent grants are validated on every tool discovery/call.

## Data Or State Considerations

- Session identity is `(effective principal, conversation_id when chat-driven, run or conversation-bound group, Agent/tool group, connection snapshot)`, with a generation token and bound proxy/profile/whitelist/toggle policy. Agent step-slot IDs alone cannot identify a browser session because slots change across rounds.
- Sessions **persist across chat turns** of the same conversation / principal / connection until idle timeout (proposed default 30 minutes), hard max duration, cancel, conversation end or revoke. Store only opaque worker/session metadata in checkpoints. A session may be reattached only if the worker proves ownership, current generation, fence and liveness. Cookie/profile persistence is separate from a live-page checkpoint. Crash survival across worker/browser process loss is not promised.
- Page references expire when navigation or browser generation changes. Old snapshot/extract ledger data does not recreate the page. A recovered run must re-observe or stop, never proceed with stale action refs.
- Per-session scheduling preserves model call order across parallel tool slots and process boundaries. Group/serialize in the scheduler or an equivalent ordered command contract; independent lock acquisition order is insufficient. Preserve unrelated tool parallelism and DEC-0069 result ordering.
- Expiry/cancel/revocation/fence loss closes or invalidates the browser and rejects late results. An approval can outlive the browser; resume must validate session/page state and request renewed approval when action target/arguments changed.
- Mutating-approval default is OFF. When ON, potential mutating effects use durable intent/outcome metadata and existing approval semantics. Unknown external outcomes cannot be recovered by a blind tool retry, session rebuild, time-travel fork or generic managed ledger replay regardless of the toggle.
- Profiles are owner-bound encrypted state filtered to declared origins. Runtime URL changes do not export cookies to another origin. Provider/proxy/whitelist/toggle configuration changes invalidate or replace the session, not mutate it in flight.
- Screenshots and downloads use existing protected artifact/storage patterns, owner checks and retention. Do not put image bytes, raw form values, download binaries or remote debug URLs into general graph state, public traces or model context without explicit bounded policy. Public chat filters screenshots by default.

## Quality Attributes And Release Gates

- **Network:** test browser-generated redirects, subresources, websockets/service-worker-related bypasses, DNS changes, proxy resolution and **whitelist denials** with a controlled fixture on both local and Browserless paths. Deny private/link-local/metadata destinations at the effective resolver/egress boundary. Uncontrolled third-party CDP/proxy configurations are not a supported shortcut around this gate. If Browserless cannot prove parity, refuse that mode and escalate — do not mark the studio remote requirement complete via local-only.
- **Resource bounds:** non-root isolated browser worker, no host filesystem/socket mounts, bounded CPU/memory/process/time/concurrency/result/screenshot/download sizes, session idle/max and action/page budgets. Exact image/dependency versions selected and pinned by the runtime tasks. Browserless account/token setup is operator configuration.
- **Approvals:** mutating-approval toggle defaults OFF; when ON, click/fill/upload/download/evaluate_js wait. Navigate/snapshot/extract/screenshot never wait on that toggle. Arbitrary page text or model classification cannot establish that a mutating action is harmless.
- **Upload/download/JS:** upload path validation against authorised attachment/workspace ids; download type/size enforcement; evaluate_js page-context sandbox with untrusted results; connection allow flags and Agent grants both required.
- **Portability (deferred):** later single-file/project exports can include generated helpers; validate actual execution then. Studio must keep contracts versioned so deferred export remains feasible.
- **Offline:** fake worker/search/Browserless providers and mock runs produce no real network effects. Real fixture access has a narrow test-only private-network exception unavailable to production arguments.
- **Operations:** counters/status for active/expired sessions, queue/limits and cleanup outcomes; provider tokens and proxy credentials never logged. Feature disablement prevents new sessions and drains/revokes existing ones safely without replaying writes.

## Rationale And Alternatives

- Current Agent tools and MCP contract fit the product; a second browser Agent loop would duplicate cost, retry, approval and trace semantics.
- Direct in-process Playwright would simplify calls but expose API resources to untrusted pages; reject it for production.
- An unmodified per-call Playwright MCP transport is insufficient for persistent page state across chat turns. Keep generic MCP behavior compatible instead of globally extending all MCP sessions.
- A generic third-party-browser-agent task adapter can be added later, but carries its own orchestration and observability tradeoffs.
- A managed operation cache alone cannot provide browser checkpoint recovery or exactly-once UI writes.
- Requiring approval for every possible-effect action by default was rejected by the owner in favour of connection-level mutating-approval defaulting OFF.
- Deferring exports shortens the first studio critical path without deleting the portable-code requirement.

## Migration Or Compatibility Notes

- Existing workflows, managed adapters, MCP stdio/HTTP and non-browser exports stay compatible. Browser extensions are opt-in and feature-gated.
- Assign schema revision numbers only against the integration branch at implementation time. Pre-existing user/org policy, API envelopes and central error/i18n paths remain unchanged.
- Rollback disables new browser operations, terminates sessions and preserves outcome/audit records. Never roll back by retrying uncertain website writes.
- Draft implementation PRs #303–#315 targeting the previous Proposed plan are not part of this architecture acceptance and must be reconciled after the amended package is accepted.

## Risks, Assumptions And Open Questions

- Browserless and proxy modes may lack verifiable destination/whitelist enforcement or origin-filtered profiles. Reject that combination, or amend scope with owner review, before claiming remote support. Local-only is not an authorised substitute for the remote requirement.
- Persistence across chat turns and worker command transport require a small contract proof in the session task. Do not expand this into a generic browser hosting platform.
- Search provider configuration, artifact limits, exact idle/max defaults (30 minutes idle proposed) and download type lists are documented implementation decisions.
- Task set, architecture and DEC-0085 remain Proposed until owner acceptance of this amended package; no implementation was requested by the planning amendment.

## Impacted Artifacts

- REQ-0086, DES-0004, DEC-0085, DISC-0002 and PLAN-0006.
- Existing DEC-0009, DEC-0018, DEC-0063, DEC-0066, DEC-0069 and DEC-0081 remain authoritative unless an implementation decision explicitly amends a named clause.
