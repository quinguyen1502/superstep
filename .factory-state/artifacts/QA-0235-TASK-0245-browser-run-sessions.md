# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0235
- Task ID: TASK-0245
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: scoped pass; full declared verification pending

## Acceptance Coverage

- Model-order same-session calls: passed. Batch reservations happen in the model step before parallel Send; SQLite and PostgreSQL independent-process CAS tests deliberately reverse arrival. Real Chromium navigation precedes snapshot across two processes. Actual Agent/RunService keeps one page across rounds and existing generic parallel tests pass.
- Principal/run/group/connection isolation: passed scoped checks. Effective chat/app/visitor/child actor is derived from persisted scope, not the resource owner or model. Foreign tickets cannot control or close another principal's page. Config/secret digest changes invalidate old sessions; profile owner checks remain in force.
- Generic concurrency/result order/MCP compatibility: passed focused regressions and actual Agent integration. Browser nodes alone bypass replay ledgers; skipped Agent approval consumes no wire action; approval_required holds the queue. No model approval is inferred. Durable verified browser approval is TASK-0246.
- Cancellation/fence/revoke/timeout/terminal cleanup: passed primitives/integration. Pre-dispatch stale fence prevents a real additional fixture POST; in-flight cancelled possible effects become unknown without retry. Terminal and waiting cancellation close; current config/flag/actor/fence are rechecked. Health can attach an existing page after its creator process exits, without resetting idle/replaying. Pending cleanup survives user purge and is retried; remote tokens clear on verified cleanup.

## Evidence

- Real Docker `scripts/test-browser-sessions.py`: passed ordered navigate/snapshot, same page after creator exit, exactly one approved fixture effect, zero additional fenced effects and container/volume cleanup. Private approval reset exists only in the fixture; no durable Human path claimed.
- Real HTTPS `scripts/test-browser-remote.py`: passed exact-context health/attachment, six actions, direct/default/custom proxy and no fallback, profile origin separation, redaction, anonymous fresh session and own-label restart cleanup.
- Focused browser/Agent/MCP/recovery/public-child/account suite: 142 passed, 2 skipped before final lifecycle additions. Later targeted session/identity/cancellation/cleanup checks: 30 passed, 1 optional skip.
- Disposable PostgreSQL 17 Alpine plus SQLite: 7 passed, covering 0056 migration upgrade/downgrade, existing data preservation, database seed and real process CAS order. Fixture container/data removed.
- Factory ready passed before implementation. Factory validate/IDs/whitespace/Node syntax passed; final full command profile to be appended against task commit. No new dependency package or public REST API; no screenshot files in Git.

## Gaps And Residual Risk

Runtime is experimental/default off behind a separate flag. Durable browser approval, filtered public traces, changed-session recovery UX, UI/recipes/export and final delivery acceptance remain their assigned tasks. Already-dispatched writes cannot be undone by fencing; uncertainty closes the page without retry. Pending cleanup can outlast a daemon/controller outage and deliberately retains minimal encrypted cleanup authority; janitors retry with capacity held. Local Docker reattachment requires the same daemon; remote deployments use the reviewed HTTPS controller. No live credentials, third-party deployment or release evidence claimed.

## QA Decision

Scoped pass pending complete declared verification and owner review. Remain review; no done/merge approval inferred.
