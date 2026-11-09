# Runtime URLs and separate web tools

Web tools add backend contracts through existing Agent/MCP surfaces. There is
no mandatory connection start URL and no second browser Agent loop. Settings and
trace UI are described in [settings](browser-settings.md) and [editor](browser-editor.md).
`STUDIO_ENABLE_BROWSER` controls browser/web discovery (default on; set `0` to disable).
Browser execution also needs its separate runtime flag; fetch/search launch no
browser and do not need that flag.

## URL binding

An Agent MCP `navigate` or `fetch` tool can declare one `url_binding`:

| Configuration | Runtime value |
|---|---|
| omitted or `{"source":"model"}` | Normal model-filled `url` argument, for example a URL supplied in chat or selected from search |
| `{"source":"fixed","value":"https://example.org/portal"}` | Builder's fixed URL; hidden from model parameters |
| `{"source":"state","value":"{{state.url}}"}` | Existing state-reference renderer, including its validation and filters |

Fixed/state values are resolved once into private pending arguments **before**
browser tickets are reserved. A model-supplied `url` cannot override either
binding. Changed arguments cannot reuse an earlier approval/ticket. Model text
containing a template is never evaluated as a state reference. A standalone MCP
node continues to use ordinary `arguments: {"url":"{{state.url}}"}`.

Empty/missing runtime URLs return `missing_input` without launching a browser or
choosing a fallback destination. Invalid fixed URLs/state references fail workflow
validation; malformed runtime URLs fail the tool/network policy. The Agent can
ask the user for the organisation/site, or the builder can branch on missing
input into the existing Human/chat question flow. For an ambiguous carrier/task,
ask for identity before searching. Search is optional; without a configured
provider its explicit result is `unsupported/search_not_configured`.

The runtime validates URL syntax and destination policy; it cannot establish
that an LLM-selected public site is the correct organisation. Results are
untrusted candidates, never a grant of authority. Use saved `allowed_origins`
and fixed/state bindings when the target must be constrained. There is no
automatic guessed start URL or domain synthesis from an order number.

## Separate managed web connection

Use the existing MCP connection API with `transport: "managed", adapter: "web"`:

```json
{
  "name": "Public web discovery",
  "transport": "managed",
  "adapter": "web",
  "settings": {
    "enabled_tools": ["search", "fetch"],
    "allowed_origins": ["https://example.org"],
    "search": {"provider": "searxng", "endpoint": "https://search.example.org/search"}
  }
}
```

`search_headers` is a separate encrypted JSON secret containing allowed HTTP
authentication headers. It is fully masked on read, sent only to the fixed
search endpoint, and never forwarded to a candidate/fetch URL. The existing MCP
owner/org policy and standard API envelope apply. Enabled tools are enforced
again at execution, including forged model calls; default tools are only fetch.
Connection/profile/proxy/allowlist fields are forbidden runtime arguments.

The initial adapter uses SearXNG `q` + `format=json` and normalises `results` to
bounded URL/title/snippet candidates. An operator must provision a reachable,
TLS-verified public HTTPS instance with JSON enabled. No paid provider is
required or automatically installed, and no live search account is configured
by this task. The API format and JSON enablement are documented by
[SearXNG Search API](https://docs.searxng.org/dev/search_api.html) and
[search formats](https://docs.searxng.org/admin/settings/settings_search.html)
(checked 2026-11-06). Provider refusal, invalid shape, empty results and disabled
tools remain explicit; they do not silently switch providers or open a browser.

## Transport and bounds

Fetch is a single unauthenticated GET using a fresh HTTP client. Search uses a
separate fresh client. Neither inherits browser cookies/storage/proxy, remote
control tokens, environment proxies or netrc. TLS stays verified, with original
Host/SNI and a numeric pinned connection. The existing browser DestinationPolicy
rejects every non-global DNS answer, mixed/rebinding answers, metadata and IPv6
translation routes. Nonstandard fetch ports need an explicit allowed origin.
`STUDIO_MCP_ALLOW_PRIVATE` does not waive this policy. Candidate domains are not
resolved while normalising search results; all DNS/address checks run when a
candidate is actually fetched or used by the isolated browser.

There are no automatic redirects or credential propagation. A redirect returns
`unsupported/redirect_requires_explicit_url`; an explicit next URL must pass a
new policy check. There is no custom web proxy option in this initial contract.

- Query: at most 512 characters; at most 10 candidate results from the first 100
  provider entries. Duplicate URLs and malformed/credential-bearing/non-global
  literal-IP candidates are dropped. Saved allowed origins filter candidates.
- Response: at most 256 KiB; compressed bodies are refused before decoding.
  HTTP connect timeout 5 s, read timeout 20 s and body elapsed budget 30 s.
  DNS uses the shared OS resolver; this is not an absolute DNS time guarantee.
- Fetch: HTML/plain text/JSON only, at most 16,000 output characters, default
  12,000. HTML text extraction ignores script/style/noscript/template contents;
  it does not run JavaScript. PDF/binary/browser challenges return specific stop
  states. Output includes truncation and `untrusted: true`.
- Known search credential values are redacted before clipping returned text;
  URLs containing those secrets are dropped. Fetch result metadata exposes the
  origin, not URL queries. Browser trace arguments retain the prior sanitizer.
- Mock/dry runs stay offline. Search/fetch are managed reads and may reuse their
  normal operation results; these never stand in for a live browser observation.

`tests/test_browser_url_bindings.py` checks Agent chat/fixed/state sources,
standalone MCP templates, override/injection refusal, search-first, missing input
and fetch-only without a browser. `tests/test_web_discovery_tools.py` checks
provider normalisation/failures, bounds, pinned transport/TLS, proxy/cookie/secret
separation, destination denial and authenticated API ownership/tool enforcement.
Providers are controlled fakes; no live provider availability or search quality
is claimed.
