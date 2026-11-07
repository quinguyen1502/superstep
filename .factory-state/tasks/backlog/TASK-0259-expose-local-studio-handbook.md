# Task

## Metadata

- Project: superstep
- Task ID: TASK-0259
- Title: Handbook: Expose a local studio (tunnels and STUDIO_PUBLIC_URL)
- Status: backlog (awaiting owner acceptance of REQ-0087)
- Owner: Thái Quí Nguyễn
- Created: 2026-11-06
- Updated: 2026-11-06
- Requirement IDs: REQ-0087
- Design IDs: DES-0005
- Architecture IDs: DEC-0086
- Plan: PLAN-0007

## Objective

Add Operate → Expose a local studio in en and vi, and replace the one-line tunnel note in operate/channels.md with a link.

## Scope

- Cloudflare Quick Tunnel (`cloudflared tunnel --url http://localhost:8000`) and named tunnels; ngrok (`ngrok http 8000`, reserved domain); Microsoft Dev Tunnels (temporary `devtunnel host -p 8000` with anonymous access — exact flag re-checked against Microsoft Learn at implementation, or `devtunnel create --allow-anonymous` + `devtunnel port create -p 8000` + `devtunnel host` persistent).
- Port table: dev API 8000, Compose 8080, image `$PORT`.
- Set `STUDIO_PUBLIC_URL` (HTTPS origin, no path), restart API/worker, re-register Slack/Telegram/WhatsApp callbacks, verify via the channel test and provider dashboards; chat-trigger callback URLs.
- Security section and official-doc links. No screenshots unless real.

## Acceptance Criteria

- REQ-0087 handbook criteria; strict build passes; no invented env var names.

## Validation Plan

- Strict en/vi handbook build and image check; frontend build/lint/vitest; targeted Playwright; full `factory verify` and `factory validate`; REV/QA artifacts.

## Activity Log

- 2026-11-06: Created by planning on branch factory/plan-docs-links-tunnel. No implementation.
