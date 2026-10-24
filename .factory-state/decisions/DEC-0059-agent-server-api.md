# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0059
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Related Requirements: REQ-0054
- Related Architecture: DEC-0008
- Related Tasks: TASK-0091

## Decision

1. Path `/api/lg`: under `/api`, so the existing dev proxy, nginx and PaaS routing serve it unchanged.
2. Request and response bodies follow the Agent Server API (raw JSON, not the studio envelope) so the SDK parses them; errors keep the studio envelope with catalog codes.
3. One active run per thread (THREAD_BUSY otherwise); a thread's state is its last run's final state and a new run's input is shallow-merged on top.
4. Human node = interrupt; resume reuses the existing waiting-run resume path; `since` is computed before enqueue to avoid a stream race.
5. Agent Server routes are an allowed exception to the envelope rule, documented in docs/backend-architecture.md.
