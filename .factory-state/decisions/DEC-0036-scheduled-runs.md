# Decision Record

## Metadata

- Project: langgraph-studio
- Decision ID: DEC-0036
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-11-08
- Related Requirements: REQ-0033, REQ-0004
- Related Architecture:
- Related Tasks: TASK-0046, TASK-0278

## Context

REQ-0004 left open whether a cron or schedule trigger was needed. The owner asked for it (remaining-work item 6). Runs could start only from the UI, an API token, or a channel resume.

## Decision

- **Table.** `workflow_schedules` holds the workflow, owner (creator), name, a five-field cron expression, an IANA time zone, a JSON input, an enabled flag, `next_run`, `last_run`, `last_run_id`, and a `note` that says why the scheduler turned it off.
- **Parser.** `services/cron.py`, with no new dependency. It accepts `*`, ranges, lists, steps, month and weekday names, weekday 7 as Sunday, and five macros. When both day fields are restricted, either one matches. Times are wall-clock in the zone: a skipped time runs an hour later, and a repeated one runs once.
- **Firing.** `RunWorker.maintain()` calls `ScheduleService.fire_due()` every second. A due row is claimed by `UPDATE … SET next_run = new WHERE next_run = seen`, so with several processes only one of them fires a given time. The next time is computed after now, so a missed time fires once and is not replayed. The run is a `queued` row with `source="schedule"` on the existing job queue.
- **Rights.** Managing schedules needs the workflow's `share` right (owner or admin), the same as API tokens, because the runs spend the creator's credentials unattended. At fire time a creator without that right turns the schedule off (`note="access"`). A schedule whose workflow is gone is deleted.
- **Limits.** At most 20 schedules per workflow, and an input no larger than a run input.

## Rationale

- The job queue already gives leases, retries, cancellation, and history. Schedules only need to enqueue.
- A conditional update needs no lock service and works the same on SQLite and Postgres.
- Not replaying missed times avoids a burst of runs after downtime.

## Alternatives Considered

- Option: APScheduler or Celery beat
  - Benefits: Mature scheduling
  - Tradeoffs: A second scheduler process or a job store beside the existing queue, and a new dependency
  - Reason Not Chosen: The run worker already loops every second
- Option: `croniter`
  - Benefits: Full cron syntax (seconds, `L`, `#`)
  - Tradeoffs: A dependency for about 80 lines of code
  - Reason Not Chosen: Five fields cover the need, and the parser is tested against DST

## Impacts

- History shows a **Schedule** badge. The `api` source handling in `run_worker.py` now reads `job["source"]`.
- Migration `0027_schedules` follows `0026_auth_hardening` (TASK-0045, PR #49), so this branch is stacked on it.

## Risks

- With `STUDIO_WORKER=0` on every process, schedules never fire. That is the same as API runs.
- Deleting a workflow leaves its schedules until their next due time, when they are removed.

## Follow-Up

- 2026-11-08 (TASK-0278): The public workflow-token API manages schedules of that one workflow (`GET`/`POST /api/hooks/workflows/{wid}/schedules`, `POST .../schedules/preview`, `PATCH`/`DELETE .../schedules/{sid}`). It reuses `ScheduleService`. The token owner is the schedule owner, the same share right this decision already requires. Firing is unchanged: `RunWorker.maintain()` still calls `ScheduleService.fire_due()`.
