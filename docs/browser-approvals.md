# Browser approval and recovery

TASK-0246 builds on [run sessions](browser-sessions.md). Both browser flags remain
experimental and default off. This describes the implemented backend contract;
connection/recipe UI, filtered trace presentation and executable exports remain
TASK-0247–0253. It does not promise exactly-once website submissions.

## Human decisions

Every click/fill requires a decision, even when an Agent tool's approval option is
off. A configured approval on a read uses the same mechanism. No page text, model
response, arbitrary engine resume value, AI review policy or public chat answer
can grant authority. There is no initial bounded-policy exemption. Generic tools
retain their current approval and concurrency behavior.

The existing owner/reviewer inbox, authenticated owner resume and verified
Slack/Telegram/Teams/email/WhatsApp channel paths record a single-use receipt
after their existing first-answer CAS. The receipt binds the private ticket's
operation/argument hash, run/group/connection, inspected target hash, origin and
page generation. It contains bounded redacted target text, never raw arguments,
cookies or profile state. Reviewer identity must still be active when consumed.
Public chat questions are marked reviewer-only. Existing UI renders the bounded
site/role/target with approve/reject; page text is explicitly labelled untrusted.

The review deadline is the earliest of worker idle expiry, session lifetime,
five minutes and any shorter configured deadline. Inspection, approval and
health do not reset the worker's clocks. Browser deadlines can only reject;
generic automatic approval/escalation does not extend browser authority. Rejection,
expired review and changed targets become structured tool results for the Agent.
Form values and URL queries are omitted from browser tool trace arguments,
including refused calls; raw executable arguments remain in private pending state.

## Consumption and uncertainty

The queue head waits for approval. Siblings cannot overtake it. After a decision,
the service rechecks current access/configuration/fence and freshly inspects the
same page/element. A changed target or page returns stale and needs a new
observation/call/decision; it does not silently approve a different element.
The durable approved→dispatching CAS happens before the private worker grant.
That grant binds the exact command, target and absolute expiry, and is consumed
once by the worker. Element fingerprints are checked again at execution.

| State | Behavior |
|---|---|
| pending | Existing approval surface waits; no website effect |
| approved | Active verified reviewer, live page and current target still required |
| rejected / expired / stale | Tool result; skip the ticket without a wire effect |
| dispatching | A possible effect has crossed the durable boundary |
| confirmed | Worker acknowledgment and post-dispatch authority checks passed |
| unknown / lost | Stop and close; never rebuild/retry the possible effect |

Losing acknowledgment after a website POST leaves unknown even if the site
actually accepted it. Cancellation/fencing after dispatch cannot undo the site.
Recovery, retry, fork and generic effect ledgers cannot turn this into another
click. A failure before a worker grant can be conservative unknown/lost; this
prefers a visible stop over duplicate external writes.

## Waiting resumes and crash windows

An ordinary live waiting resume can hand off to a newer queue lease only with
the same owner, principal, run/group/connection and current configuration. It
renews the existing private worker context, increments generation and invalidates
old grants; it preserves page/refs/order and the original idle/lifetime clocks.
Browser wire leases use stored run generation + 1, so an unclaimed UI run has
lease 1 and its first queued resume has lease 2. Old contexts fail private health
and commands. Old supervisors use a context-independent housekeeping clock,
which cannot grant commands or idle-kill a page active under the newer fence.

The database records renewing and both candidate contexts before RPC. Interrupted
handoff stops rather than rebuilding. Remote cleanup tries both persisted epochs;
local cleanup uses only the generated resource IDs. Janitors stop startup/renewal
stuck over 30 seconds, not in-progress startup merely because cleanup metadata is
already durable. Fence enforcement happens at command/bind guards; janitors do
not kill a page just because a queue claim precedes its legitimate handoff.

A legitimately resumed wave may acknowledge an already-confirmed sibling only
after live exact-context attachment. This carries already_completed and **no
cached observation** and sends no browser command. A recovered crashed execution
or time-travel fork cannot use this waiting-resume exception. Browser state is
never reconstructed from an operation ledger.

Accepted receipts also have a throttled durable queue repair path. If the process
dies after recording a decision but before enqueue, maintenance reconstructs the
existing resume job only for the current waiting checkpoint and closed wait.
Only a still-valid, unconsumed verified receipt grants. A closed inbox with a
missing receipt rejects; dispatching/unknown stops. Multiple waits retain their
own receipt and a node→intent map after absorption; a completely answered wave
uses the existing wave-ready resume path. Existing wave CAS and run fencing
prevent duplicate claims. The receipt is not a replay
cache. A completely lost page always returns session_lost.

## Persistence and evidence

Alembic 0057 adds browser_intents, wait linkage, generation/sequence proof and
handoff candidate fields. Account/workflow purge removes target text/decisions
even if resource cleanup is pending; only minimal session/command cleanup
metadata remains until cleanup succeeds. Screenshots retain existing private
owner access and retention. No new public browser execution API is introduced.

Focused tests cover default approval, verified inbox reviewer vs stranger,
UI→queue and queue→queue epochs, concurrent handoff, reordered sibling resume,
AI/chat refusal, bounded deadlines, durable queue gaps, target changes,
uncertainty and no retry/fork. SQLite and disposable PostgreSQL 17 migrations
upgrade/downgrade preserve old session/command/wait records without inventing
receipts or replay proof.

`scripts/test-browser-approval.py` uses real isolated Chromium and a disposable
site/database. It proves one permitted handoff POST, expired grant with no POST,
target mutation with no POST, one POST followed by injected lost acknowledgment,
zero repeated effects, old fence denial, old-supervisor safety and expiry during
review. `scripts/test-browser-remote.py` proves HTTPS pinned transport renewal
alongside six actions, proxy/profile isolation and restart cleanup. Fixtures
remove their own containers/networks/volumes and write no screenshots to Git.
