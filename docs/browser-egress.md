# Browser egress boundary

TASK-0242 / REQ-0086 / ARCH-0002 / DEC-0085. This task supplies the guarded
gateway and disposable proof harness. Product browser execution remains
unavailable until the runtime/session/approval tasks integrate these controls.

## Topology

The browser container has **network=none**. A small loopback byte bridge forwards
its HTTP proxy traffic to a private Unix socket on a per-session Docker volume.
The separate gateway owns that socket, resolves targets, validates every DNS
answer and connects only to the validated numeric IP. Only the gateway has the
network needed for approved destinations. Browser and gateway have no host
filesystem or Docker daemon socket mounts. The volume contains only the gateway
socket and is read-only in the browser container.

The loopback bridge exposes no application/control endpoint; it only relays bytes
to the validating gateway. Worker control must use a separate private mechanism.
Do not replace network=none with a shared Docker bridge and assume internal=true
is sufficient: Docker documents that an internal network can still reach its
gateway and some host services. Chromium also has implicit loopback proxy bypass
rules. The network namespace, not proxy settings alone, prevents direct escape.

## Destination policy

`engine/browser_network.py` validates all DNS answers for each newly opened
destination and pins one validated IP. It rejects non-global, multicast, mapped
IPv4, 6to4, Teredo and well-known NAT64 transition addresses. A mixed public/private
answer fails entirely. There is no production allow-private/fixture switch, and
`STUDIO_MCP_ALLOW_PRIVATE` does not relax browser traffic.

Origins are exact scheme/host/port tuples; nonstandard ports require an explicit
origin entry. The gateway checks the origin for each HTTP absolute-form request
or HTTPS CONNECT. HTTPS content is opaque to a CONNECT gateway: the product
worker must also enforce origin rules on requests, block service workers and
apply websocket policy. Gateway IP validation supplies the actual network
boundary even for page-generated traffic. Neither a page.goto check nor a
Playwright route handler alone replaces it.

HTTP headers are capped at 16 KiB, bodies at 1 MiB and connection transfer at
32 MiB/60 seconds; header reads have an absolute 15-second deadline. There are
at most 16 active connections. Plain HTTP forwards exactly one bounded request
body and closes; duplicate/framing/upgrade/streaming request forms are refused.
Plain ws upgrade is unsupported and fails closed; wss uses the guarded CONNECT
path. Default ports are 80/443; other approved fixture/service ports must be named.

The runtime supervisor must bound gateway lifetime and kill it on cancellation,
expiry or lost lease. DNS resolution may wait on the operating-system resolver;
connection admission is bounded even while DNS is slow. No gateway exists as a
public TCP proxy, and private socket directories must never be shared across
unrelated sessions/principals.

## Proxy routes

Direct means gateway-to-destination without an upstream proxy. Operator default
is an explicitly provided custom configuration and credentials; missing defaults
fail closed. HTTP_PROXY/HTTPS_PROXY/ALL_PROXY inheritance is never used. Custom
proxy endpoints must be operator-approved exact infrastructure origins, then
their own DNS answers are checked and pinned. Connection/model configuration
cannot add endpoints to that deployment approval set.

Initial upstream support is HTTP CONNECT with none/basic authentication. The
gateway sends **numeric destination IP:port** to the upstream proxy. It never
asks that proxy to resolve a model-supplied hostname. Browser TLS retains the
original host identity; the production worker must retain certificate checking.
Proxy credentials are sent only to the approved proxy, stripped from destination
HTTP headers and omitted from repr/audit/errors. Route/proxy address is immutable
for the session. Denied CONNECT, authentication failure or disconnect is a
failure; it never selects direct networking as fallback.

Arbitrary third-party proxies/CDP services are not verified by these fixtures.
Only operator-controlled/proven numeric-CONNECT paths are eligible. A proxy that
cannot enforce the destination boundary is unsupported; an operator approval
entry alone is not proof of provider behavior. Remote provider attestation and
rejection of unprovable combinations belong to TASK-0244.

## Reproduce the isolated fixture

```bash
python3 scripts/test-browser-egress.py --docker /path/to/docker
```

The script builds two narrowly scoped fixture images, creates uniquely named
containers/network/volumes, tests direct/custom/operator-default routes, inspects
actual isolation settings and removes only its own resources in finally. There
are no live accounts, purchases, real website visits or application-container
changes. `--skip-build` reuses images after a successful build; omit it after
changing source. Fixture stats/audit contain origins/statuses and synthetic data;
no query secret, proxy credential, cookie or screenshot is recorded.

The fixture-only policy subclasses DestinationPolicy **outside app/** to permit
one exact disposable container IP and synthetic DNS records; it has no internet
destinations. It cannot be selected in saved browser settings or model input.
Tests cover loopback/private/link-local/metadata, IPv6, mixed answers, rebinding,
redirects, images/fetch/wss attempts, secure-origin service-worker blocking,
numeric proxy CONNECT, upstream failure without fallback and a browser launched
without a proxy. Negative destination paths must never reach the fixture server.

The self-signed TLS key is generated during fixture image build and is synthetic;
certificate errors are ignored only in this fixture context. The product worker
must not inherit that test exception. The worker image runs pwuser (UID 1001),
Chromium sandbox enabled, cap-drop ALL, no-new-privileges, a read-only filesystem,
private tmpfs and bounded CPU/memory/pids. The gateway UID matches the socket owner;
permissions remain 0600. No privileged container, SYS_ADMIN, host IPC or disabled
browser sandbox is used to make tests pass.

## Dependency and source notes

The fixture reuses the existing lockfile's Playwright 1.64.1, with a separate
minimal integrity lock for playwright-core. The Microsoft fixture base is pinned
to image digest `sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f`.
The Python fixture gateway uses stdlib only and the project's existing Python 3.12
baseline. These are fixture dependencies, not an approved production browser image.
Playwright explicitly describes its published image as intended for testing and
development. TASK-0243 must review/pin the production worker separately.

The included seccomp profile derives from Microsoft Playwright v1.64.1's Docker
profile (Apache-2.0; license beside the profile). Original SHA-256:
`cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`.
It adds unconditional syscall admission for chroot so the unprivileged Chromium
user-namespace sandbox can initialise with cap-drop ALL; kernel capability checks
still apply. It does not grant host capabilities or disable seccomp. Record the
tested Linux/Docker/architecture combination before claiming portability.

Primary references: [Docker network isolation](https://docs.docker.com/reference/cli/docker/network/create/),
[Chromium proxy bypass behavior](https://chromium.googlesource.com/chromium/src/+/5e87dfef0c85687ea/net/docs/proxy.md),
[Playwright Docker guidance](https://playwright.dev/docs/docker),
[upstream seccomp profile](https://github.com/microsoft/playwright/blob/v1.64.1/utils/docker/seccomp_profile.json).

## Origin whitelist (Accepted DEC-0085)

Page destinations require a **non-empty** connection origin whitelist. An empty
allowlist is rejected when constructing `DestinationPolicy` (and earlier at the
connection settings layer in TASK-0241). Off-whitelist hosts, including redirects
and subresources that surface through the gateway, are denied. Infrastructure
dials (operator-approved proxies) use `infrastructure=True` and do not expand the
page whitelist.

