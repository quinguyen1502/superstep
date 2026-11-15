# Review

## Metadata

- Project: superstep
- Review ID: REV-0269
- Task ID: TASK-0284
- Reviewer: Grok (advisory; owner authorised the implementation, pt275u)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: approved for QA

## Review Scope

`/api/ready`, the shared probes module, job queue `depth`/`heartbeat`/`heartbeats`, worker busy slots and heartbeat, `Database.ping`, `RunRepository.oldest_started`, the `SERVICE_NOT_READY` catalog code (docs and en/vi locales), handbook en/vi health section, API route list and `.env.example`.

## Findings

### Blocking

- None.

### Non-Blocking

- The 503 body is the standard error envelope with the full report in `error.details`, not a success envelope with a 503 status. It keeps the envelope contract (errors only from the catalog) and platform probes only read the status.
- Probe timeouts use a shared four-thread pool; a database that hangs for longer than the timeout keeps a thread busy until the driver gives up (`connect_timeout` 10 s on Postgres). Later probes still time out after 2 s.
- `oldest_started` filters on `status`, which has no index. The query is a single aggregate and `runs.started` gets an index with the admin usage API; a status index can follow if large installs need it.
- Deploy templates and Docker `HEALTHCHECK` stay on `/api/health` as DEC-0095 says; the handbook explains when to use `/api/ready`.

## Review Decision

Approved for QA.
