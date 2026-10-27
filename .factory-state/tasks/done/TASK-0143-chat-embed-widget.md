# Task

## Metadata

- Project: superstep
- Task ID: TASK-0143
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067

## Objective

Protect the studio from framing. Let a published `anonymous` chat be embedded with a plain iframe snippet, or with the
script widget, whose bubble opens the same iframe and keeps the visitor's history in Safari too.

## Scope

### In Scope

- Frame headers (DEC-0067, decision 6):
  - `frame-ancestors 'none'` and `X-Frame-Options: DENY` on every studio page;
  - `/c/{slug}` gets `frame-ancestors 'self' <embed_origins>`.
  - Compose: `nginx.conf.template` gets `location /c/` with `auth_request` on `/api/public/chat/{slug}/frame`, plus
    `widget.js`.
  - All-in-one image: a middleware in `api/static.py`.
- `?embed=1` (decision 7): the compact layout and `channel = "embed"`.
- `widget.js`, a separate Vite entry in plain TypeScript:
  - the bubble, open and close, `data-slug`, `data-position` and `data-open`;
  - the visitor token in the host's localStorage;
  - the `postMessage` handshake with origin checks on both sides.
- The iframe side: it accepts the token from the allowed origins only, sends it in `X-Chat-Visitor`, and posts a new
  token back.
- Chat settings: the `embed_origins` editor, and "Copy iframe" and "Copy widget" snippets, shown for `anonymous`
  only.
- Tests:
  - pytest for the headers in the all-in-one middleware;
  - the image smoke check of the headers;
  - e2e `frontend/e2e/chat-embed.spec.ts`: a host page on a second origin embeds the widget and chats, reloads and
    keeps its chat, and a host that is not allowed is blocked by `frame-ancestors`;
  - vitest for the widget's message handling.

### Out Of Scope

- A widget that draws its own chat UI, custom colours, and the embed for `signed_in`.

## Inputs

- TASK-0140 to TASK-0142.
- `frontend/nginx.conf.template`, `backend/app/api/static.py`, `frontend/vite.config.ts`, `Dockerfile`,
  `.github/workflows/image.yml` (the smoke step).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md`
- Decisions: none
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md` (question 5: `widget-and-iframe`)

## Expected Outputs

- A host page with one `<script>` tag shows the bubble and the chat. The studio can no longer be framed.

## Implementation Notes

- Keep `widget.js` small and free of dependencies. It must not touch the host page's styles beyond its own prefixed
  elements.
- The frame check endpoint must be cheap and must not count towards the chat limits.

## Constraints

- Every widget string comes from the iframe or from `data-*` attributes. The widget has no UI text of its own,
  except the bubble's aria-label, which is given in en and vi.

## Dependencies

- TASK-0142.

## Acceptance Criteria

- Every studio page response has the deny headers, in Compose and in the all-in-one image. `/c/{slug}` has the
  allowed origins.
- The e2e test above passes. The plain iframe snippet also works in Chromium.
- The docker compose smoke and the image smoke pass on CI.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run build && npx vitest run && npx playwright test e2e/chat-embed.spec.ts`
- CI compose and image smoke

## Assumptions

- The official nginx image has the `auth_request` module, as it does today.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0074.
- 2026-10-27: merged into develop (PR #189) with the owner's approval.

## Handoff Notes

- TASK-0144 documents the snippets and the token note.
- Review: `.factory-state/artifacts/REV-0126-task-0143.md`.
- QA: `.factory-state/artifacts/QA-0126-task-0143.md`.
