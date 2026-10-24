# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0056
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Related Requirements: REQ-0050
- Related Architecture: DEC-0008
- Related Tasks: TASK-0087

## Decision

1. LangSmith is optional: the `langsmith` SDK is imported only when a client is needed; `client_factory` is replaceable for tests.
2. Sending runs as a `langsmith_suite` queue job (RunWorker), never on the request path; failures are logged and never change test results.
3. "Per-workspace" setting = the studio-wide `langsmith` setting ({"evals": bool}), admins only, audited as `policy.langsmith`.
4. Trace links: LangSmith names an OTLP run after the root span id, so `runs.trace_root` stores it; tenant/project ids are looked up once (cached, retried after 5 minutes).
