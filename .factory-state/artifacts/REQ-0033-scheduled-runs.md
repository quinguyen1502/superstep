# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0033
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: remaining-work report of 2026-10-18 (item 6: "Run workflows on a schedule (cron)"; REQ-0004 open question) and the owner's reply, "Except 2, 3, 4. Do the rest"

## Summary

Workflow owners schedule runs with cron expressions in a time zone, from the editor, with a preview of the next times.

## Problem Or Opportunity

- Periodic work (daily reports, polling) needed an external cron calling the API trigger.

## Scope

### In Scope

- Schedule storage, cron parser, scheduler in the run worker, API, editor dialog, history badge, docs

### Out Of Scope

- Seconds, `L` / `#` cron extensions, calendars and holidays, catch-up of every missed time

## Stakeholders Or Users

- Workflow owners and admins

## Desired Behavior

- See DEC-0036.

## Business Rules

- Delete needs the typed name (UI rule 7). New codes in `CATALOG`, `docs/api-errors.md`, both locales: `SCHEDULE_NOT_FOUND`, `SCHEDULE_CRON_INVALID`, `SCHEDULE_LIMIT`.

## Constraints

- No new dependency. Layers per DEC-0009; Alembic migration.

## Acceptance Criteria

- A valid expression and zone create an enabled schedule with its next three times; an invalid field or zone is refused with a message that names it.
- Turning a schedule off clears its next time; turning it on recomputes it.
- A due schedule starts exactly one run as its creator with `source="schedule"`, which completes like an API run, and moves to the next time. Two workers seeing the same due row start one run.
- A creator without the share right stops the schedule; a deleted workflow's schedule is removed.
- DST: a skipped time runs an hour later; a repeated time runs once.
- The editor dialog lists, previews, refuses a bad expression, toggles, and deletes by typed name.

## Edge Cases

- Feb 29 schedules find the next leap year.
- Both day fields restricted: either matches.

## Assumptions

- Owner-or-admin is the right audience, as for API tokens.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0036-scheduled-runs.md`
- Task: `.factory-state/tasks/done/TASK-0046-scheduled-triggers.md`
