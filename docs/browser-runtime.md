# Isolated local browser worker

The local runtime adds a worker,
private control transport and protected screenshot storage. Agent/run bindings,
durable approvals, remote profiles, recipes, UI and exports are separate layers
with their own pages. Managed browser calls still refuse execution until those seams
are integrated; metadata feature enablement alone does not launch a browser.

## Build and prove

```bash
backend/.venv/bin/python scripts/browser-contracts.py
docker build -t superstep-browser-worker:1 docker/browser-worker
docker build -f docker/browser-gateway/Dockerfile -t superstep-browser-gateway:1 .
backend/.venv/bin/python scripts/test-browser-worker.py --docker /path/to/docker
```

The last command creates only disposable synthetic fixtures and deletes its own
containers, network and volumes. It proves all six operations, exact-command
approval, stale-reference rejection, another-principal artifact denial, viewport
capture bounds, screenshot-count/action budgets, automatic idle cleanup, an
uncertain click timeout without retry, and real production-gateway private-IP
denial. It writes no screenshots to Git. Fixture-only private-IP and self-signed
TLS policies are not copied into production images.

## Isolation and control

`engine/browser_worker.py` supervises two containers. The worker has network=none,
UID/GID 1001, Chromium sandbox enabled, cap-drop ALL, no-new-privileges, a read-only
root, 768 MiB memory with no swap, one CPU, 128 pids and a bounded private tmpfs.
It mounts only its gateway socket volume read-only. No host files, API Docker
socket, database, JWT key or unrelated credentials enter the browser container.
The gateway receives only selected proxy configuration through a temporary 0600
env file; secret values never enter Docker argv. The file is removed after launch.
Gateway configuration is immutable for the session and has a hard lifetime.

The private HTTP/JSON control endpoint listens on a 0600 Unix socket inside the
worker's tmpfs. The trusted supervisor uses Docker exec with JSON on stdin to
reach it. This refines v1's private HTTP control channel without exposing a TCP
control listener to page code or requiring a host filesystem/socket mount. The
only loopback TCP listener is the byte bridge to the validating egress gateway.
Docker host access is supervisor authority, never a tool argument or browser
capability. Infrastructure image/network selection belongs to the operator.

The worker validates generated Draft 2020-12 schemas with coercion/default
mutation disabled; services validate the same Pydantic contracts. Schema parity
is tested. Every command checks full principal/run/group/connection/configuration,
session generation and expected sequence against its bound session. Out-of-order
calls fail rather than racing for a lock. The run session integration allocates
these sequences in model order.

Open has no start URL. Navigations take bounded runtime HTTP(S) arguments.
The worker checks request origins, blocks service workers, guards websocket
origins, closes popups, dismisses dialogs and cancels downloads. TLS certificate
checking remains enabled. All real network connections still pass through the
separate gateway; origin hooks alone are not the IP boundary.

## Actions and outcomes

The page viewport is 1024×768. Snapshot scans at most 400 candidate elements and
returns at most 200 visible references, bounded text and a safe origin. References
point to actual element handles, not caller-supplied CSS selectors. Input values
and editable contents are omitted. Existing references are invalidated on
navigation, fresh observation or possible-effect actions; target fingerprints
also detect material element changes. Unknown page text remains untrusted data.
Initial observation/actions operate on the main page, not a general frame/file/
keyboard/evaluate surface.

Click/fill initially return approval_required. Only the trusted control port can
grant a one-use approval for the exact command fingerprint and current observed
target. A changed value/context/target cannot reuse it. This is a worker primitive,
not the completed Human-node approval product: browser approvals bind it to verified
durable approvals, rejection, expiry and run recovery. No page/model argument
can approve itself.

Action timeout is bounded by connection policy. Uncertain possible effects
return unknown and close the session; neither the worker nor supervisor retries.
Transport loss returns unknown for possible effects or session_lost for reads.
Expired/lost/cancelled/unknown sessions are cleaned up. Supervisor watchdogs
remove worker, gateway and socket volume on idle/lifetime expiry even if no
further tool call occurs. Browser-side expiry is checked on every control request
and periodically as defence in depth. A hard kill is used for unresponsive
processes. If Docker cleanup cannot be verified, cleanup_pending is explicit and
close can be retried; run sessions retain/reap that state rather than report a
successful cleanup. No closed session accepts new commands.

## Protected screenshots

The worker holds at most four viewport PNGs of 2 MiB each in memory, masking
input/textarea/select/contenteditable fields. Tool results contain only private
artifact IDs. A separate authenticated control read transfers bytes; another
principal/context is refused. `BrowserRuntimeService` persists successful capture
bytes before replacing the worker reference with a stored reference, so it never
returns a dangling public download URL. Failure to fetch/store closes the worker
and withholds that reference.

SQLAlchemy BrowserArtifact and Alembic 0055 store the bounded PNG plus owner,
execution principal/run/connection/group and explicit expiry. PNG viewport bounds
are checked before writes. This is separate from user chat uploads. Retention is
one hour: reads reject expiry immediately, and the existing minute sweeper removes
bytes. Account purge and workflow/run deletion also remove captures.

`GET /api/browser/artifacts/{id}` requires the authenticated owner account; missing,
expired and other-owner IDs have the same 404. Responses use image/png, no-store,
nosniff, restricted CSP and no signed/public URL. Public visitor/app-user tokens
do not grant this Studio endpoint. Publication/trace filtering and screenshot
presentation belong to the editor; images are never general workflow state or inline
WorkerResult bytes. Masking input controls cannot sanitise all private content
rendered by a website; captures remain owner-protected data.

## Dependency selection and compatibility

The worker uses Node 24 LTS (observed v24.22.2), the official node:24-bookworm-slim
image pinned to `sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c`.
Playwright-core 1.64.1 and Ajv 8.20.0 reuse versions already in the root lockfile,
with a separate minimal integrity lock. Playwright installs its matching Chromium
binaries/system dependencies; no floating system Chrome is selected. The gateway
uses stdlib Python 3.12 with its base pinned to
`sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.

Playwright's Apache-2.0 package supplies the browser API; Ajv's MIT package supplies
the standard schema validator instead of a partial handwritten validator. The
selected stable major versions, first-party provenance, maintained LTS runtime,
Linux amd64/arm64 image families and necessity are documented here; actual proof
was Docker Desktop 28.3.3/aarch64. Other platform/runtime combinations require
their own evidence. Python contracts use the project's existing Pydantic dependency.

The reviewed seccomp profile/license now live beside the Python worker client
and are included in the backend wheel/API image source. The fixture and runtime
use this one copy; wheel inclusion is verified. The production worker is built
separately from the Microsoft development/testing fixture image. No live provider,
account, proxy purchase, release or application deployment occurs in this task.

Primary references: [Node release support](https://nodejs.org/en/about/previous-releases),
[Playwright browser compatibility](https://playwright.dev/docs/browsers),
[Ajv Draft 2020-12 support](https://ajv.js.org/json-schema.html),
[Ajv license](https://github.com/ajv-validator/ajv/blob/master/LICENSE).
