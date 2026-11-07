# Decision

- Decision ID: DEC-0087
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0088
- Created/Updated: 2026-11-07
- Related: REQ-0088, PLAN-0008

Service stubs: a shared generated helper `offline_service` / `offlineService` decides. Without `LLM_PROVIDER` (the existing offline example mode that also mocks the model) it prints `(offline mock) <kind> <name> …` to stderr and the stub returns the Studio mock value (`[]`, `None`/`null`, e-mail dry run), preserving parity tests with the Studio mock run. With `LLM_PROVIDER` set it raises `NotImplementedError` / throws. Managed connections keep their unconditional placeholder error.

Missing targets: the subgraph node becomes a node that raises `LookupError` / throws when reached (not an empty compiled graph, not a build-time failure, so unrelated branches still run); missing workflow tools and unregistered functions raise instead of returning `None`.

Model fallback (TASK-0264): export the two-step order in plain generated code rather than a library wrapper, so failover codes match Studio (`PROVIDER_UNREACHABLE`, `PROVIDER_BAD_RESPONSE`, `MODEL_NOT_FOUND` ≈ connection/timeout errors, HTTP 5xx, HTTP 404) and authentication/validation errors do not fail over. The fallback provider is `LLM_FALLBACK_PROVIDER` (default `LLM_PROVIDER`); the fallback credential id is never exported. Offline mock mode calls the primary mock only, as Studio does offline.

HTTP (TASK-0265): generated code resolves the host and refuses private, loopback, link-local and reserved addresses unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`, never follows redirects, sends `user:pass@` as Basic auth and strips it from the URL, and sends an `Idempotency-Key` derived from node id and rendered request. DNS rebinding between check and connect is narrower than Studio's IP pinning; documented as a residual difference.
