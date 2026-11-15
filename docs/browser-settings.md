# Browser and web connection settings

Use Settings → MCP servers → Add server → Managed
connection. `STUDIO_ENABLE_BROWSER` defaults on; set it to `0` to hide the
browser/web adapters. The independent browser runtime gate remains off by
default; discovering tools does not launch a browser or attest a remote service.

Choose **Isolated browser** for the local Docker runtime or an independently
approved HTTPS remote controller. Remote controller origin/token are encrypted,
write-only credentials. Arbitrary CDP/WSS endpoints are unsupported. No start
URL belongs on the connection: calls supply URLs at runtime.

**Network / Proxy** lives on this connection, with direct, operator-default and
custom HTTP routes. Custom supports no authentication or HTTP Basic with separate
encrypted username/password. Operator route approval is still mandatory; saving
settings does not approve an address. Failure never falls back to direct.
SOCKS, HTTPS proxy transport, country selection and stealth bypass are unsupported.

Allowed origins are exact HTTP(S) origins, one per line. Browser connections
require a non-empty whitelist; empty lists are rejected. Internal addresses stay
blocked by network policy. (Web search/fetch connections may leave the list empty
for public discovery under the same network policy.)
Personal login profiles require a name, exact HTTPS origins and a bounded
Playwright storage-state JSON seed. The server validates secure host-only cookies
and origin scope; organisation connections cannot use profiles. Seeds are not
read back or updated from page changes. Profile origins must be within an explicit
allowed-origin list. Session/action bounds cannot exceed the runtime contract;
idle timeout cannot exceed lifetime. Expiry and approval remain worker-enforced.

On edit, stored secret fields stay empty. Save keeps them unless explicitly
cleared or their provider/auth/profile is removed. Clear stored secret and Remove
profile use the shared exact-name confirmation; changes apply on Save. Required
credentials must be replaced before saving an active configuration. Connection
deletion also requires its exact name. These UI confirmations do not change API
DELETE semantics.

Choose **Web search and fetch** for a separate stateless connection. Enable fetch
and/or search; search requires a fixed HTTPS SearXNG JSON endpoint. Optional
encrypted search headers go only to that endpoint. Fetch never receives browser
cookies, profile, proxy or search authentication. With no tools enabled, discovery
returns an empty list. Search/fetch network policy still applies to actual requests.

The existing Settings inline cards remain the only management surface. Controls,
linked errors and help are available in English/Vietnamese with keyboard access,
light/dark themes and stacked narrow layout. Screenshot and node/recipe/trace
configuration are covered by the [editor](browser-editor.md); exports are documented separately.
