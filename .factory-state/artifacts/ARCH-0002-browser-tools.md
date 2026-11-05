# Architecture Artifact

## Metadata

- Project: superstep
- Architecture ID: ARCH-0002
- Status: Accepted for delivery — owner instruction on 2026-11-05
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Related Requirements: REQ-0086

## Context

DISC-0002 documents the short-lived generic MCP transport, existing managed connection/outcome contracts, parallel Agent slots, shared HTTP guard and placeholder/refused exports. These are reuse boundaries, not proof that native browser egress/session behavior already exists. Backend layering remains DEC-0009.

## Decision Or Proposal

1. Expose a browser tool family and recipes through current managed discovery/call surfaces. Keep the current Agent expansion/model/provider loop. Connection metadata fixes infrastructure and authority; runtime arguments specify a task target.
2. Introduce a small versioned worker command contract with isolated provider implementations: local Playwright and capability-checked remote browser attachment. Run services bind an execution context to the tool port; engine modules do not import services/repositories or learn provider secrets.
3. Reuse the encrypted connection store where it fits. Add only schema needed for scoped profiles, session metadata, generation/fencing and browser artifact references, via SQLAlchemy/Alembic. No raw SQL or general plugin framework.
4. Enforce browsing destinations outside untrusted page code, at the network boundary that actually connects/resolves targets. Local worker has no direct escape path around its controlled egress. Remote browser and custom proxy modes require equivalent tested enforcement or explicit capability refusal.
5. Reuse existing snapshot/templating/tool arguments for fixed/state/model bindings. Add narrow metadata for missing binding modes rather than a second expression language. Optional start-page input is ordinary task data.
6. Keep search, fetch and browser separate. Normalise one configured search provider through existing MCP/HTTP where possible; bounded HTTP fetch reuses guarded transport and does not load browser cookies or inherit its proxy implicitly.
7. Keep recipes a bounded sequence of the same actions, with typed inputs/outputs and versioned snapshot per run. Prefer current workflow-as-tool composition to a separate recipe runtime. If a lightweight stored action definition is needed, justify it in the contract task.
8. Export self-contained helpers for supported browser connections/recipes in Python and TypeScript, plus project packaging. Replace the managed export refusal only for the supported browser adapter; preserve all unrelated refusals. Use environment placeholders for secret/provider/proxy/profile material and explicitly gate unsupported behavior.

## Boundaries And Interfaces

- API → services for connection/profile/recipe visibility, CRUD, capabilities and artifact access; services → repositories for persisted metadata and → isolated worker control client for browser execution.
- Engine sees a typed port bound by RunService: operation, arguments and existing operation key plus trusted execution context. Context includes effective resource principal/visitor scope, run, Agent/tool group, connection/version, lease/fence and ordered command identity; model-supplied fields cannot replace it.
- Worker commands/results are versioned bounded JSON. Result carries status, safe observation/extraction, page generation references, timing and optional private artifact reference; never raw Page/Browser objects or decrypted secrets.
- Initial capability vocabulary: navigate, snapshot, click, fill, structured extract, screenshot; no evaluate/shell/files/keyboard escape hatch. A recipe invokes those same commands in sequence.
- Local/remote provider capabilities declare network enforcement, proxy protocol/auth mode, scoped storage-state support, bounded screenshot support and export support. Do not infer these from the presence of a CDP URL.
- Trusted operator-configured worker/CDP control-plane endpoints have a separate deployment allowlist and authentication from browsed website targets. An explicitly configured internal worker endpoint must never enable private-network navigation for page/chat arguments.
- Proxy modes: direct, explicit operator default, connection-specific. Target validation and remote DNS constraints apply to the proxy path too; no unapproved bypass list, arbitrary host environment inheritance or fallback route.

## Data Or State Considerations

- Session identity is `(effective principal, run, Agent/tool group, connection snapshot)`, with a generation token and bound proxy/profile policy. Agent step-slot IDs alone cannot identify a browser session because slots change across rounds.
- Store only opaque worker/session metadata in checkpoints. A session may be reattached only if the worker proves ownership, current generation, fence and liveness. Cookie/profile persistence is separate from a live-page checkpoint.
- Page references expire when navigation or browser generation changes. Old snapshot/extract ledger data does not recreate the page. A recovered run must re-observe or stop, never proceed with stale action refs.
- Per-session scheduling preserves model call order across parallel tool slots and process boundaries. Group/serialize in the scheduler or an equivalent ordered command contract; independent lock acquisition order is insufficient. Preserve unrelated tool parallelism and DEC-0069 result ordering.
- Expiry/cancel/revocation/fence loss closes or invalidates the browser and rejects late results. An approval can outlive the browser; resume must validate session/page state and request renewed approval when action target/arguments changed.
- Potential effects use durable intent/outcome metadata and existing approval semantics. Unknown external outcomes cannot be recovered by a blind tool retry, session rebuild, time-travel fork or generic managed ledger replay.
- Profiles are owner-bound encrypted state filtered to declared origins. Runtime URL changes do not export cookies to another origin. Provider/proxy configuration changes invalidate or replace the session, not mutate it in flight.
- Screenshots use existing protected artifact/storage patterns, owner checks and retention. Do not put image bytes, raw form values or remote debug URLs into general graph state, public traces or model context without explicit bounded policy.

## Quality Attributes And Release Gates

- **Network:** test browser-generated redirects, subresources, websockets/service-worker-related bypasses, DNS changes and proxy resolution with a controlled fixture. Deny private/link-local/metadata destinations at the effective resolver/egress boundary. Uncontrolled third-party CDP/proxy configurations are not a supported shortcut around this gate.
- **Resource bounds:** non-root isolated browser worker, no host filesystem/socket mounts, bounded CPU/memory/process/time/concurrency/result/screenshot sizes. Exact image/dependency versions selected and pinned by the runtime tasks.
- **Approvals:** conservative by tool/action policy. Arbitrary page text or model classification cannot establish that click/fill is harmless; reviewed read-only recipe policies are explicit exceptions.
- **Portability:** single-file exports can include generated helpers; project exports include dependencies, browser install/container guidance, secret placeholders and compatible Node/Python runtime information. Validate actual execution, not just generated syntax.
- **Offline:** fake worker/search providers and mock runs produce no real network effects. Real fixture access has a narrow test-only private-network exception unavailable to production arguments.
- **Operations:** counters/status for active/expired sessions, queue/limits and cleanup outcomes; provider tokens and proxy credentials never logged. Feature disablement prevents new sessions and drains/revokes existing ones safely.

## Rationale And Alternatives

- Current Agent tools and MCP contract fit the product; a second browser Agent loop would duplicate cost, retry, approval and trace semantics.
- Direct in-process Playwright would simplify calls but expose API resources to untrusted pages; reject it for production.
- An unmodified per-call Playwright MCP transport is insufficient for persistent page state. Keep generic MCP behavior compatible instead of globally extending all MCP sessions.
- A generic third-party-browser-agent task adapter can be added later, but carries its own orchestration and observability tradeoffs.
- A managed operation cache alone cannot provide browser checkpoint recovery or exactly-once UI writes.

## Migration Or Compatibility Notes

- Existing workflows, managed adapters, MCP stdio/HTTP and non-browser exports stay compatible. Browser extensions are opt-in and feature-gated.
- Assign schema revision numbers only against the integration branch at implementation time. Pre-existing user/org policy, API envelopes and central error/i18n paths remain unchanged.
- Rollback disables new browser operations, terminates sessions and preserves outcome/audit records. Never roll back by retrying uncertain website writes.

## Risks, Assumptions And Open Questions

- Remote endpoints and proxy modes may lack verifiable destination enforcement or origin-filtered profiles. Reject that combination, or amend scope with owner review, before claiming support.
- Persistence and worker command transport require a small contract proof in the first task. Do not expand this into a generic browser hosting platform.
- Search provider configuration, artifact limits and exact default timeouts are documented implementation decisions. The prototype's 12 actions/30 seconds/2-minute idle values are proposed defaults, not approved requirements.
- Task set, architecture and DEC-0085 remain proposed until owner acceptance; no implementation was requested by the planning instruction.

## Impacted Artifacts

- REQ-0086, DES-0004, DEC-0085, DISC-0002 and PLAN-0006.
- Existing DEC-0009, DEC-0018, DEC-0063, DEC-0066, DEC-0069 and DEC-0081 remain authoritative unless an implementation decision explicitly amends a named clause.

## Owner Delivery Authorisation — 2026-11-05

The owner instructed: “Pull develop về branch hiện tại, và tiến hành chuỗi task này.” This accepts the proposed browser delivery scope and starts PLAN-0006 in dependency order. This supersedes earlier planning-only/pending-start statements; source onboarding approval statuses are unchanged. Implementation, fixture validation and task PRs are authorised; merges, production/provider setup, release and deployment are not. Task branches may stack on the published planning package; dependent implementation tasks require predecessor review/QA and an explicitly documented stack.

## Local Worker Refinement — TASK-0243, 2026-11-05

The private HTTP/JSON worker channel uses a Unix socket inside network=none, reached by the trusted supervisor through Docker exec/stdin. No TCP control endpoint or host mount enters the page namespace. Generated schemas share the Python source contract; the only TCP listener relays bytes to the isolated gateway. Local worker/image/cleanup and screenshot retention are specified and proved in `docs/browser-runtime.md`. Idle/lifetime watchdogs remove the containers/volume without needing another call; failed Docker cleanup is explicit as cleanup_pending and must be retained/reaped by TASK-0245. Stored captures are owner-only with a one-hour TTL, account/workflow purge and Alembic 0055. This does not claim Agent binding, remote/profile support, durable approvals, UI or executable exports complete.

## Remote/Profile Refinement — TASK-0244, 2026-11-05

The provisional metadata-only controlled_cdp provider becomes controlled_remote: authenticated/pinned HTTPS RPC to an operator-reviewed deployment of the same isolated local worker/gateway. Arbitrary CDP cannot establish the required boundary and is refused. Capability JSON is version compatibility, not attestation; independent operator endpoint/address approval is mandatory. No model loop is delegated. Personal encrypted profile_state permits only secure host-only cookies and localStorage at declared canonical HTTPS origins, with principal-bound seeds and fresh contexts. The entire profile connection is restricted to those origins because cookies are not port-scoped. Other users/org-wide/visitors/app identities and unsupported storage/stealth routes refuse. Configuration digest includes encrypted credentials; TASK-0245 must revalidate/revoke sessions on CRUD/fence changes. `docs/browser-remote.md` records exact support, deployment limits and actual HTTPS/Docker evidence. No third-party deployment or live account is claimed.

## Session Refinement — TASK-0245, 2026-11-05

RunService derives effective actor scope from persisted chat/child records, separate from resource ownership. The model step reserves private ordered tickets before Send; SQL CAS and bounded capacity coordinate processes. Browser steps bypass generic result ledgers. Exact-context health proves existing-page attachment without refresh/replay; the worker activity clock remains authoritative across supervisors. Alembic 0056 stores only opaque session/order/status metadata and encrypted remote cleanup authority. Current config/flag/fence/cancel is checked before/after calls and by a running watcher. Already-dispatched effects may be unknown and are never retried/undone. Pending cleanup survives owner deletion without a user FK, keeps capacity and clears tokens on confirmed cleanup; API and worker janitors retry. Separate experimental runtime gate defaults off. `docs/browser-sessions.md` records limits and proof; TASK-0246/0250 still own durable approvals/recovery and public trace filtering.
