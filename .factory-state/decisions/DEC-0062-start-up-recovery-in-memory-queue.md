# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0062
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Related Requirements: REQ-0071
- Related Architecture: none
- Related Tasks: TASK-0115

## Context

Findings (2026-10-25, `tests/test_durable_restart.py` with a real uvicorn process killed by SIGKILL):

- The engine does not persist through a LangGraph checkpointer (`InMemorySaver` only observes supersteps). Superstep
  writes its own checkpoints to its database (`runs.checkpoint`: node(s), state, iteration counts, workflow
  snapshot), SQLite by default or Postgres.
- A run paused at a Human node is stored as `waiting` with that checkpoint: it already survived a restart and was
  resumed from the studio after it. Worked before this task.
- Queue jobs save a progress checkpoint after every node. With Redis, the lease reaper requeues a dead worker's job
  and it continues from that checkpoint (TASK-0020/0021). With the in-memory queue (the default without
  `REDIS_URL`), the job vanished with the process: the run stayed `running` (or `queued`) forever. Did not work.
- Editor runs are written when they end, so a restart leaves no row behind; a resume from the editor keeps the run
  `waiting` until it settles, so it can be answered again.

## Decision

1. At start-up, with the in-memory queue only, the worker requeues every `queued`/`running` run of a queue source
   (api, schedule, chat, test) as a `recovered` job (`RunWorker.recover_unfinished`, once per process). The existing
   recovered-job path (claim with fencing, `plan_recover`) continues it; test runs get their suite's `mock` flag back.
2. A cap instead of endless retries: a run already claimed `STUDIO_RECOVER_MAX_ATTEMPTS` (default 3) times, counted
   by `runs.lease_gen`, ends as `error` `RUN_INTERRUPTED` (new code, 500) with its events kept and its callback sent.
3. `STUDIO_RECOVER_ON_START=0` turns it off, for several API processes sharing one database without Redis (one would
   take over another's live runs). With Redis nothing changes: leases already cover it.
4. No persistent LangGraph checkpointer: the database checkpoints already give durability for every database backend,
   and adding a second store would duplicate state.

## Consequences

- The default single-process setup now continues interrupted API runs after a restart; the node in flight runs again
  (finished side-effect calls are reused from the ledger).
- Delayed jobs and webhook deliveries held only in memory are still lost on restart (documented as Redis territory).
