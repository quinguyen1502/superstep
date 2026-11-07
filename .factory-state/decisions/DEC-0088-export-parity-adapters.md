# Decision

- Decision ID: DEC-0088
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0089
- Created/Updated: 2026-11-07
- Related: REQ-0089, PLAN-0009, DEC-0087 (supersedes its "no IP pinning" residual)

HTTP pinning (TASK-0267): mirror `core/net.py`. Resolve once, refuse if any answer is blocked (unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`), connect to the first checked address. Python: httpx request to the IP-literal URL with `Host` set to the original authority and the `sni_hostname` extension (httpcore uses it as `server_hostname`, so SNI and certificate hostname checks use the name). TypeScript: `node:http` / `node:https` (supported by Node and Deno) with a `lookup` hook returning only the checked address and `servername` = the name; `fetch` cannot pin. No redirects follow (Node's client never follows). Idempotency key unchanged.

Fallback with attachments (TASK-0268): Studio passes the same `files` to both attempts of `model_policy.run`; the export adds `call_llm_files_fallback` / `callLlmFilesFallback` with the TASK-0264 failover predicate, the fallback provider from `LLM_FALLBACK_PROVIDER`, at most one fallback call. LLM calls have no external side effect, so no idempotency key is involved.

Adapters (TASK-0269..0271, split from TASK-0266): environment-configured, real when configured, announced offline mock only when unconfigured and `LLM_PROVIDER` is unset, error when unconfigured in a live run. Concrete transports and variable names are recorded in each task before implementation.
