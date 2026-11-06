# Browser connection and worker contract v1

TASK-0241 / REQ-0086 / ARCH-0002 / DEC-0085 (Accepted 2026-11-06). This delivery
implements metadata, discovery and typed contracts. It does not launch a browser.
Set `STUDIO_ENABLE_BROWSER=1` to configure/discover the `browser` managed adapter
through the existing `/api/mcp/servers` API. The default is disabled. Existing rows
remain visible/editable only under existing owner/admin policy; discovery and use are
denied when disabled. Deletion remains available to the authorised owner/admin.

## Connection metadata

The existing `McpServer.settings` JSON and encrypted `McpServer.secrets` store are
sufficient for this task. No SQL schema change or migration is needed. Live session
state and stored profile material are subsequent tasks, not data hidden in these
settings. A non-empty origin whitelist is required; no design-time website URL is
required.

| Setting | Default / bound |
| --- | --- |
| version | integer 1 |
| provider | `local` or `browserless` |
| proxy.mode | `direct`, `operator_default`, or `custom` |
| proxy.server | HTTP origin, only for custom; no credentials/path/query/fragment |
| proxy.auth | `none` or `basic`, only custom may choose basic |
| profile | optional name and 1–20 exact HTTP(S) origins; metadata only |
| allowed_origins | **required**, 1–50 exact HTTP(S) origins; empty is invalid |
| action_timeout_ms | 30,000; 1,000–60,000 |
| idle_timeout_s | 1,800 (30 minutes); 60–7,200 and no greater than lifetime |
| lifetime_s | 3,600; 120–14,400 |
| max_actions | 40; 1–200 |
| max_pages | 4; 1–20 |
| require_mutating_approval | false (navigate/snapshot/extract/screenshot never wait) |
| allow_evaluate_js | false |
| allow_upload | false |
| allow_download | false |
| download_max_bytes | 10 MiB; 1 KiB–50 MiB |
| download_allowed_types | default PDF/CSV/plain/JSON/PNG/JPEG; 1–30 MIME types |
| stealth | false; true only when provider is `browserless` (best-effort, not a bypass) |

Profile origins must be a subset of the connection origin allowlist. They do not
grant network access or load cookies. Origin checks here are syntax validation;
they do not claim DNS, IP or browser-egress enforcement (TASK-0242–0244).

Only `browserless_token`, `proxy_username` and `proxy_password` are accepted secret
keys. Browserless requires a secret API token. A local connection rejects that key.
Basic proxy authentication requires both proxy secrets; other modes reject them.
Secrets are encrypted before persistence and all hints are exactly `••••`. Updates
preserve existing MCP semantics: omit the secrets object to keep all; null values
keep named keys; unlisted keys are removed. Removal that leaves a required pair
incomplete fails atomically. Profile state provisioning is intentionally not
accepted until TASK-0244 enforces owner and origin scope.

## Capability eligibility and proof gates

| Provider/path | Contract accepts metadata | Proof required before execution |
| --- | --- | --- |
| local + direct | yes | isolated worker with no direct page-network escape, controlled DNS/egress |
| local + operator default | yes | explicit operator config, stable resolution; missing default fails closed |
| local + HTTP proxy (none/basic) | yes | enforced destination resolution on the selected proxy path; no direct fallback |
| browserless + those modes | yes | equivalent remote network isolation, authenticated control plane, whitelist/proxy/DNS proof |
| SOCKS/HTTPS proxy, provider geo | no | out of v1; cannot be selected through tool arguments |

`CAPABILITY_CONTRACT.runtime_verified` is false for every provider. Settings do not
contain a user-asserted "verified" capability. CDP reachability alone is
insufficient. No combination is advertised as executable by TASK-0241.
TASK-0242–0244 must prove the selected paths or return an explicit refusal. Shipping
local-only does not close the Browserless requirement.

## Tools and trusted context

The nine schemas are generated from `engine/browser_contract.py`, which is also the
worker validator. Unknown fields are forbidden. No tool accepts authority, session,
connection, proxy, profile, approval or Node/shell evaluation arguments.

| Tool | Arguments |
| --- | --- |
| navigate | runtime `url`, bounded HTTP(S), no embedded credentials |
| snapshot | none |
| click | `observation_id`, `element_id` |
| fill | the observed references plus `value` up to 4,000 characters |
| extract | observation reference and up to 20 named element references |
| screenshot | none; result holds only an opaque protected artifact ID |
| upload | observed file input plus `source_kind` (`attachment`/`workspace`) and `source_id` |
| download | observed element that triggers a download |
| evaluate | `observation_id` plus page-context `expression` up to 4,000 characters |

Connection `allow_upload` / `allow_download` / `allow_evaluate_js` hide those tools
from discovery until enabled. Agent grants (later UI task) further restrict what the
model sees. Mutating approval defaults OFF; when ON, click/fill/upload/download/evaluate
may return `approval_required`. Navigate/snapshot/extract/screenshot never wait.
Page text and evaluate results are untrusted. Tool definitions grant no implicit
authority.

`ExecutionContext` contains the effective principal (including visitor identity),
optional `conversation_id` for cross-turn session binding, run id, Agent group id,
connection id, a configuration snapshot hash and a lease generation. It is never part
of a tool schema. Worker commands carry session id, generation, sequence and
command id for ordered same-session execution.

## Always-on safety (not toggles)

- Mandatory non-empty origin whitelist on every connection.
- Private/link-local/metadata IP destinations blocked at the egress boundary (later tasks).
- Page content treated as untrusted; never follow page instructions to expand access.
- Secrets redacted in API responses and public chat.
- Public chat has no Settings access.
- Feature kill-switch drains sessions without replaying website writes.

## Error codes

| Code | When |
| --- | --- |
| `BROWSER_DISABLED` | Operator gate off |
| `BROWSER_RUNTIME_UNAVAILABLE` | Metadata-only path; no verified worker yet |
| `MCP_CONFIG_INVALID` | Invalid settings/secrets (including empty whitelist) |
