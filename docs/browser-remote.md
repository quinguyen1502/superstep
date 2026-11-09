# Controlled remote browser and login profiles

The remote provider extends the isolated worker; the Superstep Agent still chooses each
primitive call. There is no hosted model loop. Managed browser execution is
gated by run sessions, fences and durable Human approval ([sessions](browser-sessions.md), [approvals](browser-approvals.md)).

## Provider and trust boundary

The provisional metadata-only `controlled_cdp` provider is replaced explicitly by
`browserless`. It speaks the same worker protocol over authenticated HTTPS
RPC to an operator-controlled deployment of `app.browser_controller`. Raw CDP/WSS,
arbitrary third-party self-reported capabilities and endpoint query tokens are
unsupported. Previously saved provisional metadata must be reconfigured; there
is no automatic conversion or fallback.

The operator supplies an independent allowlist of `ApprovedController` HTTPS
origins and numeric addresses. `approved_transport` matches the connection's
secret endpoint exactly, pins the connection address, preserves Host/TLS SNI and
verifies the certificate. Internal control-plane addresses can be explicitly
approved without enabling private page destinations. HTTP redirects, environment
proxies and TLS verification disablement are refused. A connection cannot approve
its own control endpoint. Tokens are at least 32 printable ASCII characters,
carried only in Authorization; response bodies are bounded to 4 MiB (private PNG
transport), command envelopes to 256 KiB. Requests are never automatically retried.

The capability record is an exact versioned compatibility check, **not remote
attestation**. Trust comes from operator review/provisioning of this known
controller/worker/gateway deployment and the independent allowlist, with the
controlled fixture below as implementation evidence. A random server returning
the same JSON is not approved. Deployment and paid/live provider setup are outside
this delivery.

The controller has no Studio database, credential registry or model. It starts
the same `LocalBrowserWorker`: network=none Chromium, private Unix control,
separate enforced gateway, resource bounds and watchdogs from
[browser-runtime.md](browser-runtime.md). Every request binds full execution
context/session/generation; foreign contexts fail. Per-session locks reject
concurrent access rather than letting lock acquisition establish model order.
Run sessions allocate deterministic command sequences before dispatch. Lost effects
remain unknown and close; old page refs are never reconstructed from cached data.

The dedicated API is not mounted on Studio. Its default bind is localhost; expose
it only behind operator-managed authenticated TLS with bounded body/read/request
limits, or configure uvicorn TLS. `STUDIO_BROWSER_CONTROL_TOKEN` and a unique
`STUDIO_BROWSER_CONTROL_ID` are required. One controller process owns each ID;
multiple replicas must use distinct IDs. Default capacity is 8 sessions and at
most 1024 recent request tombstones. Opens are not replayed while tombstoned.
Startup cleanup selects only resources with this controller's exact Docker label,
validates returned names/IDs and deletes its prior pages/volumes. It never scans
all application containers by a broad name prefix. Shutdown/periodic cleanup
retries pending cleanup; daemon outages remain explicit. Durable Studio-side
cleanup/fencing belongs to run sessions. No cross-process live-page reattachment is
promised.

## Profiles

Existing encrypted **personal** browser connections store `profile_state` (up to
64 KiB UTF-8), alongside existing masked proxy/provider secrets. No new database
schema or login capture UI is needed. Metadata contains profile name and 1–20
exact canonical HTTPS origins. The state format accepts only bounded cookies and
localStorage; IndexedDB, OPFS, WebAuthn, arbitrary state files and unknown fields
are refused. These are deliberate restrictions on the broader
[Playwright storage-state API](https://playwright.dev/docs/api/class-browsercontext).

`BrowserProfileService.prepare` requires `user:<connection owner>` as the effective
principal, personal scope and a current configuration digest. Public visitors,
app users, other users and org-wide profile sharing are refused. The digest
includes owner/scope/metadata and encrypted credential material; updating or
removing state invalidates an old context. Run sessions revalidate the current
connection on every call and revoke affected live sessions on update/delete.
The trusted RPC sender supplies a principal-bound seed; both supervisor and Node
worker independently reject mismatches before use.

Profile connections can visit **only profile origins**, even if the ordinary
connection allowlist was broader or empty. Cookies are secure, exact-host only,
not expired, and cannot use leading-dot/subdomain scopes. Duplicate cookies,
storage origins/keys and oversized state fail. Cookie paths are retained. This
closed network scope matters because cookies do not isolate by port. Other
origins, subdomains and ports must use another anonymous connection. Initial
cookies/localStorage are copied into a fresh ephemeral context for each session;
changes never write back to the stored profile. There is no live shared tab or
persistent browser user-data directory.

Observations/extractions redact known provisioned cookie/storage values; captures
mask those visible text values plus existing input/editable controls. This does
not classify all private site content. Captures remain owner-protected, never
public URLs/general graph state. No cookie values or storage state are returned
by tool/status/capability APIs. API secret hints remain exactly `••••`; preserve,
remove and atomic validation follow existing MCP semantics.

## Supported combinations

| Capability | Local | Controlled remote | Refusal |
|---|---|---|---|
| Six bounded operations | yes | same contract | raw CDP or incompatible protocol |
| Direct egress | enforced gateway | same isolated worker/gateway | unproved vendor isolation |
| Operator-default proxy | explicit operator route | controller's explicit operator route | missing default, no fallback |
| Custom proxy | approved HTTP none/basic | controller-approved HTTP none/basic | unapproved endpoint/auth, SOCKS/HTTPS proxy |
| Login state | personal HTTPS host-only cookies/localStorage | same seed checks and fresh context | org/visitor/app identity, broad/expired/unsupported state |
| Stealth/geo/CAPTCHA bypass | unsupported | unsupported | no silent setting drop or bypass promise |

Controller proxy approval/default configuration is infrastructure authority, not a
connection/model override. The default CLI accepts no custom proxy allowlist;
trusted deployment code can instantiate `BrowserControllerService` with its
reviewed configuration. Unsupported routes fail before any browser command.

## Reproducible proof

`backend/.venv/bin/python scripts/test-browser-remote.py --docker <docker>` builds
production worker code plus a test-only trusted CA child image and disposable
synthetic destination/proxy. It starts the real HTTPS control API outside page
namespaces and connects through the production pinned TLS client. It exercises:

- All six operations, exact approval and private capture through RPC.
- Direct/custom/operator-default routes and deliberate upstream failure without
  direct fallback; private target denial and no proxy auth at the destination.
- Real secure host-only cookie and localStorage loading, redaction, denied other
  origin/subdomain/port and a separate anonymous session.
- Restart cleanup of only the fixture controller's labels, including volumes.

The CA and synthetic private DNS/IP policy exist only in test fixtures, never in
production flags or tool arguments. Chromium TLS verification stays enabled.
This is a loopback HTTPS controller fixture using isolated Docker workers on the
same machine, not evidence for a purchased third-party provider or a different
physical host. It writes no screenshot images into Git. Unit/API checks cover
endpoint approval/TLS/redirect rules, auth, byte limits, foreign contexts,
capability refusal, unknown effect without retry, tombstones, encrypted profile
CRUD, principal/origin restrictions and configuration revocation digests.
