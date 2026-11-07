# Review

## Metadata

- Project: superstep
- Review ID: REV-0236
- Task ID: TASK-0246
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-05
- Updated: 2026-11-06
- Outcome: scoped pass; final declared verification passed

## Review Scope And References

TASK-0246 delta from TASK-0245 c8093635; the complete unmerged stack against develop is prerequisite work, not this task's scope. REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006; `docs/browser-approvals.md`; TASK-0245 #310 / REV-0235 / QA-0235; #309/#308/#304/#303/#299. Owner approved implementation/fixtures/stacked delivery, not merge or release.

## Findings

- Resolved review finding: an answered final multi-approval wave can lose its ready-to-resume queue job after its wait markers are removed. Isolated follow-up retains the exact intent map and queues the existing wave-ready path; two crash-window tests passed. Applied as e7f1ab8d (identical source to isolated 2d0d6159); actual two-connection wave and pending-cleanup target purge tests pass. No blocking source finding remains.
- Resolved before source commit: default click/fill approval could not rely on the configurable tool flag; browser decisions now require a durable verified human receipt. Raw resume words, model/page text, AI policy and public chat cannot grant.
- Resolved before source commit: UI run generation 0 and first queued generation 1 previously mapped to the same browser epoch. Positive wire epoch = stored run generation + 1; actual inbox UI→queue test proves renewal. Janitors do not revoke between claim and legitimate handoff. Concurrent binders share one renewal.
- Resolved before source commit: later siblings arriving before a decided head could defer again instead of waiting; forced thread ordering now verifies progress without a repeated effect. Old context supervisors use housekeeping health without command authority.
- Resolved before source commit: profile secrets must be redacted before clipping target descriptions; invalid/refused/handoff browser arguments use a shared trace sanitizer. Account/workflow purge removes target text even while cleanup metadata must remain.

## Standards And Architecture Alignment

Existing Agent/MCP/effect/approval/channel/wave seams; no second Agent loop or public execution endpoint. Services own authority, repositories use SQLAlchemy/CAS and Alembic 0057, worker grants bind exact command/target/expiry. Generated private schemas remain checked against Python. No dependencies or new error codes/UI components. Bilingual backend approval prompts; existing shared envelope, locales and delete UI/API behavior retained.

## Design Alignment

Existing approval surfaces receive bounded redacted site/role/target labelled untrusted. Public chat is reviewer-only. Full connection/recipe/trace controls and accessibility verification remain TASK-0249/0250; runtime stays experimental/default off. This is backend scoped delivery, not full product acceptance.

## Validation Review

Final focused suite on c7cb3af7: 92 passed, 4 optional skips. Disposable SQLite/PostgreSQL 17: 9 passed including 0057 downgrade/upgrade and real process CAS. Actual pinned HTTPS/Chromium and approval mutation/expiry/lost-ack proofs passed. Full eight-command profile passed on c7cb3af7: backend 483.79 s, root build/lint/test and both SDK checks passed. Final wave/purge follow-up has focused regressions and is undergoing its own isolated full profile on 2d0d6159. No screenshots committed and no live provider/account setup.

## Assumptions And Required Follow-Up

Unknown external effects cannot be undone or exactly-once guaranteed. No blind retry/page rebuild/fork replay. Drain active experimental sessions before upgrading the private protocol. Self-review is advisory; owner review and final declared verification remain gates before done/Ready/merge.

## Review Decision

Conditionally approved for QA/review after the wave fix, with committed-source full verification passed; owner review pending. No merge approval inferred.

- 2026-11-06 final verification: full eight-command Factory profile passed on isolated 2d0d6159, identical final backend source to task e7f1ab8d. Backend 481.74 s; root build/lint/test, Python SDK and TypeScript SDK build/test/typecheck all passed in one canonical run. Exact locked workspace dependencies were installed after a root-only node_modules symlink selected the wrong nested TypeScript version; no source/dependency-manifest change. The prior environment-only failures are superseded by this complete pass. No blocking finding remains; owner approval still required.
