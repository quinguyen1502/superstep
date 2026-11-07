# Decision

- Decision ID: DEC-0088
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0089
- Created/Updated: 2026-11-07
- Related: REQ-0089, PLAN-0009, DEC-0087 (supersedes its "no IP pinning" residual)

HTTP pinning (TASK-0267): mirror `core/net.py`. Resolve once, refuse if any answer is blocked (unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`), connect to the first checked address. Python: httpx request to the IP-literal URL with `Host` set to the original authority and the `sni_hostname` extension (httpcore uses it as `server_hostname`, so SNI and certificate hostname checks use the name). TypeScript: `node:http` / `node:https` (supported by Node and Deno) with a `lookup` hook returning only the checked address and `servername` = the name; `fetch` cannot pin. No redirects follow (Node's client never follows). Idempotency key unchanged.

Fallback with attachments (TASK-0268): Studio passes the same `files` to both attempts of `model_policy.run`; the export adds `call_llm_files_fallback` / `callLlmFilesFallback` with the TASK-0264 failover predicate, the fallback provider from `LLM_FALLBACK_PROVIDER`, at most one fallback call. LLM calls have no external side effect, so no idempotency key is involved.

Adapters (TASK-0269..0271, split from TASK-0266): environment-configured, real when configured, announced offline mock only when unconfigured and `LLM_PROVIDER` is unset, error when unconfigured in a live run. Concrete transports and variable names are recorded in each task before implementation.

MCP adapter (TASK-0269): a generated minimal Streamable HTTP JSON-RPC client (initialize, notifications/initialized, tools/call, session DELETE), ported from `engine/mcp_client.py` with the same result rules (`structuredContent`, else JSON text, else content; `isError` stops the run). No new dependency (httpx / fetch). Servers are identified only by a prefix `MCP_SERVER_<n>` (the Studio server id stays blanked by `sanitize`); configuration is `<PREFIX>_URL` and optional `<PREFIX>_HEADERS` (JSON). The URL is operator configuration, so no private-address guard is applied (unlike Studio's user-registered servers); redirects are not followed. stdio servers are not exported.

Retriever adapter (TASK-0270): the export calls the owner's Superstep knowledge base search API (`POST <SUPERSTEP_URL>/api/knowledge-bases/<id>/search`, Bearer `SUPERSTEP_TOKEN`, envelope `success/data/error`), so chunks, scores, embedder checks and access rules stay the studio's; no second embedding/vector-store implementation is exported. Knowledge bases are identified by a prefix `KNOWLEDGE_BASE_<n>` (ids stay blanked); `<PREFIX>_ID` supplies the id. A standalone (Studio-independent) index is out of scope.

Send email adapter (TASK-0271): Studio semantics kept — a node sends only if it had an SMTP credential in the studio (a boolean `_email_sends` survives `sanitize`; the credential never does), otherwise it is a dry run. Python ports `core/smtp.py` with stdlib `smtplib` (resolve once, private hosts only with `STUDIO_SMTP_ALLOW_PRIVATE=1`, connect to the checked IP, STARTTLS required by default and verified against the host name, `ssl` and `none` modes). TypeScript uses `npm:nodemailer@^6`, loaded only when sending, pointed at the checked IP with `tls.servername` = host. Settings: `SMTP_HOST`, `SMTP_FROM`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_NAME`. `Message-ID` = sha256(run id, node, recipients, subject, body)[:32]@sender domain, stable across retries of one run; SMTP itself has no idempotency, so a retried send can still deliver twice (recipients can deduplicate by Message-ID). Not ported: HTML format, Reply-To, the studio's e-mail quota.
