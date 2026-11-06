# Conversation and run-bound browser sessions

TASK-0245 connects the existing Agent/MCP runtime to isolated browser workers.
TASK-0246 extends the approval/resume behavior described here; see
[browser-approvals.md](browser-approvals.md) for the current receipt, handoff,
confirmed-sibling acknowledgment and crash-window contract.
Enablement is experimental and defaults off: both `STUDIO_ENABLE_BROWSER=1` and
`STUDIO_ENABLE_BROWSER_RUNTIME=1` are required for trusted run ports. A standalone
MCP connection test/call still cannot launch a browser without a run context.
Durable browser-specific Human approval, filtered trace/recovery UX and release
acceptance remain TASK-0246 onward; this task does not enable those implicitly.

## Authority and identity

RunService constructs the browser port after assigning the run ID, resource
owner, effective actor and worker fence. Group IDs hash the full Agent/node path
and stay stable across rounds/tool slots. Session identity is principal + (conversation when chat-driven, else run) +
group + connection. Chat-driven sessions **persist across turns** of the same
conversation, principal and connection until idle timeout (default 30 minutes),
hard max lifetime, cancel, conversation end or connection revoke. Configuration includes encrypted credentials/profile state;
changes do not mutate a live page. Tool arguments cannot replace identity,
profile/proxy/provider, generation, ticket or approval authority.

The resource owner continues to select credentials (existing DEC-0023), while
the principal identifies the actual actor. Studio/authenticated sessions use
`user:<actor>`; anonymous visitors and app users use opaque hashes of their
verified chat scope. A child run inherits its top parent's actor, with a distinct
run/group. Platform chats receive a channel-scoped identity; an unknown chat
actor is never upgraded to the resource owner's user ID. Personal login profiles
therefore refuse visitors/app/platform actors and delegated users who are not
the profile owner. Scope comes from persisted chat records, not workflow inputs.

## Ordering before parallel dispatch

The Agent model step reserves a whole batch in model order **before** LangGraph
sends parallel tool slots. Each valid browser call receives a private ticket in
the hidden pending state; tickets are not added to model tool-call messages or
public metadata. Generic tools are not in this queue. A standalone MCP node has its own group;
use an Agent or the planned recipe tool for multi-action page continuity. Sessions/connections/groups
have independent queues and unrelated tools retain existing parallel scheduling
and model-ordered result joining.

`BrowserSessionRepository` uses SQLAlchemy transactions/CAS. Only the ticket at
`executing_order` can claim execution, even if later calls reach another process
first. Command hashes bind operation/arguments without storing raw URL/form
values in scheduler tables. Tickets are idempotent reservations, not replayable
results. Each session has at most 300 reservations. A short singleton-row write
lock makes the global default capacity of 16 new/starting/ready/pending-cleanup
sessions atomic across SQLite/PostgreSQL processes. Remote controller capacity
(default 8) also applies; missing capacity refuses, never bypasses isolation.

Wire sequence increments only for consumed worker commands. Rejected Agent
approvals can skip a pending ticket without consuming a browser action. An
`approval_required` result holds the head; later calls cannot overtake it or
automatically approve it. TASK-0246 supplies durable verified Human decisions.
The test harness alone grants an exact private approval to demonstrate ordering
of a real website effect; that is not a public approval path.

Browser tool steps bypass the generic node-result ledger and stateless managed
operation ledger. A model checkpoint may retain its pending ticket identities,
but an old observation/result is never returned as proof of a live page. Reusing
a completed/uncertain ticket or losing the page stops the session; no new page is
opened to replay a call. Generic MCP transports/ledgers remain unchanged.

## Reattachment, fencing and lifecycle

A process may attach to an existing local/remote worker only after the private
health control proves the exact context/session/generation. Health never opens a
page or refreshes idle time. The worker's activity clock is authoritative, so a
surviving supervisor does not idle-kill a page being used by another process.
If the creator exits, Node enforces idle/lifetime and the durable janitor removes
remaining containers/volumes. An unproved/missing worker is session_lost.

The current connection/configuration, principal/run, runtime flag, cancel signal
and run fence are checked before dispatch and after the result. While a command
runs, a 100 ms watcher rechecks authority and closes on failure. Connection
update/delete revokes sessions; user deactivation/role change/deletion closes
owned and actor sessions. A deleted workflow is checked by the run guard. A new
worker fence invalidates prior browser sessions rather than replaying them;
resumption needing a new observation/approval is TASK-0246's explicit UX.

A website effect already dispatched before cancellation/fence loss may have
happened. The result is unknown, the worker closes and there is no retry or
claim that an external write was undone. A stale fence before dispatch cannot
send another command. Terminal/cancel/timeout closes matching lease sessions;
waiting/paused sessions may remain only until their bounded idle/lifetime.
Cancelling/expiring a waiting run closes them too. Independent session queues do
not rely on thread-lock acquisition order.

Alembic `0056_browser_sessions` adds session/order/status and a capacity lock;
there are no page snapshots, cookies, raw arguments or screenshot bytes there.
Remote cleanup authority alone is encrypted and cleared after confirmed cleanup.
Unverified cleanup retains a pending row for retry, including after account/run
purge; its owner is an opaque identifier without a user cascade. Verified closed
records are purged with account/workflow run data. This deliberate minimal
retention prevents an account deletion from losing the only cleanup handle.

The worker janitor runs every 5 seconds, including with runtime disabled; the
API expiry sweep provides an additional minute fallback. It drains disabled,
expired, stale, changed, terminal or dead-worker sessions and retries pending
cleanup. A startup interrupted over 30 seconds is stopped. Docker/control-plane
outages remain visible as pending cleanup and consume capacity until verified.
All Studio processes must share the existing encryption key/database. No
cross-machine local-Docker attachment is claimed; use the controlled remote
provider when worker infrastructure is elsewhere.

## Operator configuration

| Variable | Authority |
|---|---|
| `STUDIO_ENABLE_BROWSER` | metadata/discovery gate |
| `STUDIO_ENABLE_BROWSER_RUNTIME` | separate experimental trusted-run execution gate |
| `STUDIO_BROWSER_CONTROLLERS` | JSON array of operator-approved `{endpoint,address}` HTTPS control origins and numeric pins |
| `STUDIO_BROWSER_PROXY_ORIGINS` | JSON array of approved local upstream HTTP proxy origins |
| `STUDIO_BROWSER_PROXY_DEFAULT` | explicit local default `{proxy:{mode,server,auth},secrets:{...}}`; absent means refuse operator-default |

These are infrastructure settings, never model/workflow inputs. Remote proxy
allowlist/defaults belong to the remote controller's trusted deployment, not
these local overrides. TLS/control trust and profile restrictions are in
[browser-remote.md](browser-remote.md); local topology/resource bounds are in
[browser-runtime.md](browser-runtime.md).

## Evidence

`backend/.venv/bin/python scripts/test-browser-sessions.py --docker <docker>`
uses a disposable SQLite database, real Chromium and isolated synthetic website.
Two independent processes deliberately arrive out of order; navigation precedes
snapshot. The creator then exits; another supervisor attaches to the same page,
a test-only approved click creates exactly one POST effect, and a stale fence
prevents an additional approved click. It verifies removal of worker/gateway
resources and writes no screenshot files to Git. The HTTPS remote fixture also
verifies exact-context health/attachment and retained profile/proxy behavior.

`tests/test_browser_run_sessions.py` exercises actual Agent/RunService binding,
separate-process SQLite and optional disposable PostgreSQL order, ledger bypass,
capacity, skipped/held approvals, lost-page no replay, config CRUD revocation,
cancelled uncertain effects, pending cleanup through user purge and chat/child
principal derivation. Migration upgrade/downgrade preserves existing data.
