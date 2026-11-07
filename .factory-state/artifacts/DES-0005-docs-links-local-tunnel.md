# Design

- Design ID: DES-0005
- Project: superstep
- Status: Accepted 2026-11-07
- Created/Updated: 2026-11-06
- Related: REQ-0087, DEC-0086, PLAN-0007

## User Flows

1. Admin opens Settings → Channels on a local Studio without `STUDIO_PUBLIC_URL`. The existing muted notice under each connection keeps its text and adds an inline link "Learn more" (vi "Hướng dẫn") with an external-link icon, opening Operate → Expose a local studio in a new tab.
2. While adding a Slack/Telegram/WhatsApp connection, the existing helper text ends with a link to the matching `operate/channels.md` section.
3. In the handbook, the reader picks a provider tab/section, runs the command, copies the HTTPS origin into `STUDIO_PUBLIC_URL`, restarts, then follows the verification checklist.

## States

- Public URL set: no tunnel link in the notice (notice already hidden).
- Public URL missing: notice + link.
- Offline/air-gapped: link still renders; handbook page notes self-hosting the docs.

## UI Rules And Accessibility

- Use existing text-link styling inside the current `text-xs text-muted-foreground` notice (no new Alert variant, no banner redesign); lucide `ExternalLink` at default icon size.
- Link text is descriptive or carries an `aria-label` that names the destination; `target="_blank"` with `rel="noopener noreferrer"`.
- Keyboard focus visible with the existing focus ring; en/vi strings added under `docs.*` keys with parity.

## UX Acceptance

- Links reach the correct locale page/anchor; no layout shift in channel cards at narrow widths; no tour or modal.
