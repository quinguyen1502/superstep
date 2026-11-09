# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0087
- Status: Accepted — owner approved REQ-0087 and PR #319 with DEC-0086 option A on 2026-11-07; Teams/e-mail links and tour deferred
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-06
- Source: Owner chat 2026-11-06 ("build the documentation link and tunnel part"), following the earlier documentation-links/tunnel proposal
- Related: DES-0005, DEC-0086, PLAN-0007, TASK-0259, TASK-0260

## Summary And Scope

1. **Handbook page "Expose a local studio"** (en + vi, Operate section) explaining how to give a local Studio a public HTTPS origin for platform callbacks with Cloudflare Tunnel (quick and named), ngrok, and Microsoft Dev Tunnels; how to set `STUDIO_PUBLIC_URL` and restart; and how to verify Slack, Telegram, WhatsApp, Teams/e-mail links and chat-trigger callbacks.
2. **Contextual handbook links in the Studio UI**, starting with Settings → Channels: the existing "STUDIO_PUBLIC_URL is not set" notice gains a "Learn more" link to the new page, and channel connection helpers (Slack first, then Telegram/WhatsApp) link to the matching sections of `operate/channels.md`. One shared helper builds locale-aware handbook URLs.

Out of scope: guided tours/onboarding walkthroughs, a docs search or embedded docs panel, broad UI redesign, new environment variables unless accepted in DEC-0086, automatic tunnel management by Studio, browser export tasks TASK-0251/0252, and images/mockups (real screenshots only if actually captured).

## Business Rules

- The only public-origin variable is `STUDIO_PUBLIC_URL`. Docs and UI must not mention invented names (for example `STUDIO_BUBLIC_URL`, `STUDIO_SECURE_TUNNEL`).
- Ports: the dev API (`uvicorn`) listens on 8000; the Compose nginx entry point is 8080; the all-in-one image uses `$PORT` (8000 by default). The tunnel must target the process that serves `/api`.
- `STUDIO_PUBLIC_URL` is an HTTPS origin without a path or trailing slash; Telegram requires HTTPS. Changing it requires an API/worker restart and re-registering provider callbacks (for example Telegram `setWebhook`, Slack request URL).
- Quick/temporary tunnel URLs change on every start; stable URLs need a named Cloudflare tunnel, a reserved ngrok domain, or a persistent dev tunnel.
- Security: a tunnel publishes the whole Studio, not only callback paths. Docs must warn against exposing dev mode with the demo account, require production auth settings or provider access controls, and tell users to stop the tunnel when done. Callback signature checks stay enforced; docs never suggest disabling them.
- Commands are taken from current official provider docs (Cloudflare Quick Tunnels, ngrok, Microsoft Dev Tunnels) and linked.
- UI links open the published handbook in a new tab with `rel="noopener noreferrer"`, an accessible name, and en/vi labels; they never block the setting they explain.

## Acceptance Criteria

- `operate/expose-local.md` exists in en and vi, is in both navs, cross-links from `operate/channels.md` (replacing the one-line tunnel note), and the strict en/vi handbook build passes.
- The page covers the three providers, temporary vs stable URLs, set/restart/verify steps, per-channel callback URLs, and the security warning, with official-doc links.
- Channels "public URL missing" notice and the Slack/Telegram/WhatsApp connection helpers show a "Learn more" (with its vi label) link to the correct locale and anchor; unit and e2e tests assert href, target and rel.
- One helper builds handbook URLs; the base follows DEC-0086. en/vi locale parity tests pass; shadcn default sizes and existing toolbar/alert patterns are kept.
- Full Factory verify/validate, review and QA artifacts per task; all required CI green before any merge.

## Resolved Questions

- Link base: DEC-0086 option A, fixed published handbook URLs (owner, 2026-11-07).
- Teams/e-mail links and any tour are deferred to future requirements (owner, 2026-11-07).
