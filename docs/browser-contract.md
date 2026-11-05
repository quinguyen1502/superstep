# Browser connection and worker contract v1

TASK-0241 / REQ-0086 / ARCH-0002 / DEC-0085. This delivery implements metadata,
discovery and typed contracts. It does not launch a browser. Set
`STUDIO_ENABLE_BROWSER=1` to configure/discover the `browser` managed adapter through
the existing `/api/mcp/servers` API. The default is disabled. Existing rows remain
visible/editable only under existing owner/admin policy; discovery and use are
denied when disabled. Deletion remains available to the authorised owner/admin.

## Connection metadata

The existing `McpServer.settings` JSON and encrypted `McpServer.secrets` store are
sufficient for this task. No SQL schema change or migration is needed. Live
session state and stored profile material are subsequent tasks, not data hidden
in these settings. `settings={}` is a valid local/direct configuration; no
design-time website URL is required.

| Setting | Default / bound |
| --- | --- |
| version | integer 1 |
| provider | `local` or `controlled_remote` |
| proxy.mode | `direct`, `operator_default`, or `custom` |
| proxy.server | HTTP origin, only for custom; no credentials/path/query/fragment |
| proxy.auth | `none` or `basic`, only custom may choose basic |
| profile | optional name and 1–20 exact HTTPS origins; personal encrypted state (TASK-0244) |
| allowed_origins | up to 50 exact HTTP(S) origins; empty means public targets subject to enforced egress |
| action_timeout_ms | 30,000; 1,000–60,000 |
| idle_timeout_s | 120; 30–600 and no greater than lifetime |
| lifetime_s | 600; 30–1,800 |
| max_actions | 12; 1–100 |
| stealth | false; all other values rejected |

Profile origins must be a subset of a nonempty connection origin allowlist.
At runtime TASK-0244 narrows the effective network allowlist to profile origins.
Syntax validation alone does not establish DNS/IP or browser-egress enforcement.

Accepted secret keys are `remote_endpoint`, `remote_token`, `proxy_username`,
`proxy_password` and `profile_state`. Controlled remote requires an operator-approved
HTTPS origin and an authentication token of at least 32 characters. Raw CDP/WSS
endpoints and endpoint query tokens are refused. A local
connection rejects that key. Basic proxy authentication requires both secrets;
other modes reject them. Secrets are encrypted before persistence and all hints
are exactly `••••`, including endpoints/usernames. Updates preserve existing
MCP semantics: omit the secrets object to keep all; null values keep named keys;
unlisted keys are removed. Removal that leaves a required pair incomplete fails
atomically. TASK-0244 accepts bounded encrypted personal profile state with
owner/origin checks; see `browser-remote.md`.

## Capability eligibility and proof gates

| Provider/path | Contract accepts metadata | Proof required before execution |
| --- | --- | --- |
| local + direct | yes | isolated worker with no direct page-network escape, controlled DNS/egress |
| local + operator default | yes | explicit operator config, stable resolution; missing default fails closed |
| local + HTTP proxy (none/basic) | yes | enforced destination resolution on the selected proxy path; no direct fallback |
| controlled remote + those modes | yes | equivalent remote network isolation, authenticated allowed control plane, actual proxy capability |
| SOCKS/HTTPS proxy, provider geo, stealth | no | out of v1; cannot be selected through tool arguments |

`CAPABILITY_CONTRACT.runtime_verified` is false for every provider. Settings do
not contain a user-asserted "verified" capability. CDP reachability alone is
insufficient. No combination is advertised as executable by TASK-0241.
TASK-0242–0244 must prove the selected paths or return an explicit refusal.

## Tools and trusted context

The six schemas are generated from `engine/browser_contract.py`, which is also
the worker validator. Unknown fields are forbidden. No tool accepts authority,
session, connection, proxy, profile, approval or arbitrary evaluation arguments.

| Tool | Arguments |
| --- | --- |
| navigate | runtime `url`, bounded HTTP(S), no embedded credentials |
| snapshot | none |
| click | `observation_id`, `element_id` |
| fill | the observed references plus `value` up to 4,000 characters |
| extract | observation reference and up to 20 named element references |
| screenshot | none; result holds only an opaque protected artifact ID |

Click/fill are potentially effectful and require approval under the initial
policy. Page text is untrusted. Tool definitions grant no implicit authority.

`ExecutionContext` contains the effective principal (including visitor identity),
run, stable Agent/tool group, connection ID, configuration digest and positive
lease generation. The service binds it from authorised run state. A digest must
include the secret/configuration revision when sessions are introduced; the
generic managed operation digest is not sufficient. The worker must compare
context against its session record on every command, not merely trust a valid
DTO supplied by a client. No run context is wired by this task.

## Worker control channel

The next tasks implement a private authenticated HTTP/JSON worker control
channel (a deployment-private endpoint, never a model-supplied address). Session
open binds the above immutable context and the effective validated config;
secrets travel only over that authenticated channel. Command and close requests
must be authorised to that session. Public MCP routes do not expose this channel.

Command DTO v1 contains context, session ID, browser generation, zero-based
sequence, command ID, operation, validated arguments and bounded timeout. The
run scheduler allocates sequence in model call order before parallel dispatch.
Worker acceptance must enforce the expected next sequence and fence; a lock
alone is insufficient. Retransmission cannot repeat effects or return cached
observations as live state. TASK-0245 defines durable lifecycle/fencing storage;
TASK-0246 defines effect intent and recovery.

Worker request/result envelopes accept at most 256 KiB of finite UTF-8 JSON;
the HTTP transport must cap bytes before JSON parsing too. Observations have a
page generation and opaque observed element refs, at most 16,000 text characters
and 200 elements (1,000 characters per element). Extracted output is at most 20
fields of 4,000 characters. The byte budget applies even to multibyte text.
Origins exclude path/query/fragment; raw browser objects, cookies, control URLs
and image bytes have no result fields. Services must additionally redact known
secrets/sensitive page data and protect artifact access before exposing results.
Bounds and typed DTOs alone do not sanitise arbitrary page content.

Statuses distinguish confirmed, failed-before-effect, unknown, approval-required,
challenge-required, expired, session-lost, stale-observation, policy-denied and
cancelled. Unknown is never an automatic retry signal. A generation mismatch or
lost page requires re-observation/stop; checkpoint JSON is not a live browser.

## Compatibility and current failure mode

Owner/org CRUD, API envelopes and existing transports remain unchanged. Dry runs
only return the existing offline `dry_run` result. Real browser calls fail with
`BROWSER_RUNTIME_UNAVAILABLE` before reserving a generic managed intent/result;
the stateless ledger cannot safely execute or replay a live browser session.
All existing managed export annotations/refusals from current develop remain
in force; executable browser exports belong to TASK-0251/0252.

No browser dependency, provider account, remote/proxy connection, login state,
production migration, release or deployment is introduced by this contract task.

TASK-0244 refines the provisional remote provider name to `controlled_remote`: it uses the same isolated worker through authenticated, verified/pinned HTTPS RPC. `controlled_cdp` was metadata-only and never executable; old provisional records must be explicitly reconfigured. Profile provisioning and exact capability/refusal rules are in `docs/browser-remote.md`.
