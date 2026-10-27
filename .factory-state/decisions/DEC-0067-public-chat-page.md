# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0067
- Status: Accepted. The owner gave the CLAR-0005 answers on 2026-10-27; this record writes them down.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Related Requirements: REQ-0074 (CLAR-0005), REQ-0048
- Related Architecture:
  - DEC-0009 (layers)
  - DEC-0023 (resources of the owner)
  - DEC-0052 (web chat model)
  - DEC-0053 (access and steps): this decision replaces its "reserved" part
  - DEC-0054 (answered by)
- Related Tasks: TASK-0140, TASK-0141, TASK-0142, TASK-0143, TASK-0144

## Context

- Phase 1 (REQ-0048) already has three parts:
  - the `web` chat trigger, whose `command` is the slug and whose `settings` JSON holds the rest;
  - `chat_sessions` with `channel`, `owner` and `visitor` columns, and `chat_turns`;
  - one `source = "chat"` run per message, planned over the studio run socket `/ws/run`.
- The run socket and the REST routes need a studio user: the `studio_session` cookie (SameSite Lax) or a JWT.
- The run socket streams every event, including node input, output and state. The `steps` setting is applied only
  when sessions are read with `view=visitor`.
- Fixed-window rate limiters and counters exist in `services/rate_limit.py`. They are shared through Redis when it is
  set.
- The UI is served by nginx in Compose and by the API itself in the all-in-one image (`api/static.py`). Neither sends
  `X-Frame-Options` or `frame-ancestors` today, so any site can frame the studio.
- CLAR-0005 answers:
  - access: both `anonymous` and `signed_in`;
  - an anonymous visitor is remembered with an HttpOnly cookie;
  - limits per visitor, per IP and per workflow per day, with no CAPTCHA;
  - Human nodes behave as in the studio;
  - embed: a plain iframe snippet and a script widget that opens the same iframe;
  - the page shows a title, an intro and suggested messages;
  - builders see visitor chats read-only;
  - the page runs the latest saved version.

## Decision

1. **Publishing.**
   - The web chat's `access` takes three values:
     - `studio`, as before;
     - `anonymous`;
     - `signed_in`, which is any account of this studio.
   - A chat is published when `enabled` is set and `access` is not `studio`. Otherwise the public routes answer
     `CHAT_NOT_PUBLISHED` (404).
   - The slug is the trigger's `command`. It is 3 to 64 characters of `[a-z0-9-]`, it must not be a reserved word,
     and it is unique among web chats.
     - Errors: `CHAT_SLUG_INVALID` and `CHAT_SLUG_TAKEN`.
     - Changing the slug breaks the old link.
   - New settings keys:
     - `title` (60 characters);
     - `intro` (Markdown, 1000 characters, sanitised when shown);
     - `suggestions` (up to 4, 120 characters each);
     - `daily_limit` (a whole number from 0 to 100 000, default 500, where 0 means no cap);
     - `embed_origins` (up to 10 origins of the form `https://host[:port]`; `http://localhost[:port]` is also
       allowed, for local work).
   - Publishing is refused in demo mode.
2. **Public routes.** They live in a new router, `api/routes/public_chat.py`, and a new service,
   `PublicChatService`. The service sits beside `ChatSessionService` and reuses it.
   - `GET /api/public/chat/{slug}` returns the page settings: title, intro, suggestions, the `steps` mode, the access
     value, and whether the visitor is signed in. It never returns the workflow, its graph or its owner.
   - `GET /api/public/chat/{slug}/sessions` lists the visitor's own sessions. `GET .../sessions/{sid}` returns one,
     always with `view=visitor`.
   - `POST .../sessions` creates a session with `channel = "web"`, or `"embed"` when the page is in a frame.
   - `WS /ws/public/chat/{slug}` takes `{chat_session_id, message}` or `{chat_session_id, resume_run_id, response}`
     and nothing else, so it can only start or answer this chat's runs.
   - A session that belongs to someone else is not found (`CHAT_SESSION_NOT_FOUND`).
3. **Visitor identity.**
   - *anonymous*: the visitor is a signed token, an HMAC with the studio secret over `{slug, visitor id}`.
     - The server sets it on the first call, as an HttpOnly cookie `studio_chat_<slug-hash>` with
       `Path=/api/public/chat/{slug}` and `/ws/public/chat/{slug}`, lasting `retention_days`.
     - The cookie is `SameSite=Lax` on a direct visit. Over HTTPS it is `SameSite=None; Secure; Partitioned`, so it
       works inside an iframe in Chrome and Firefox.
     - The widget (decision 7) may send the same token in the header `X-Chat-Visitor`, or as `?visitor=` on the
       socket. The header wins over the cookie.
   - *signed_in*: the visitor is the studio user, read from the session cookie as `current_user` does. Sessions get
     `owner = uid` and `channel = "web"`.
     - A visitor who is not signed in gets `CHAT_SIGN_IN_REQUIRED` (401). The page then sends them to
       `/login?next=/c/{slug}`.
     - The studio cookie is not sent inside a cross-site frame, so the embed snippets are offered only for
       `anonymous`.
4. **Runs and streaming.**
   - A message plans a run as phase 1 does (`RunService.plan` with `chat_session_id`), but runs as the workflow's
     owner (DEC-0023), using the owner's credentials, knowledge bases and MCP servers. It records `source = "chat"`.
   - It runs the latest saved version.
   - The public socket does not forward raw events. It sends only:
     - `node_token` deltas of the reply field;
     - step events reduced to the `steps` mode, with the same rules as `steps_of`;
     - the Human question, when the node is answered by the visitor;
     - the final status and error code.
     - Run ids, state, node input and node output are never sent, except in `full` mode, where steps already show
       input and output.
   - Human nodes follow DEC-0054 unchanged. An Agent tool approval is always answered by a reviewer.
5. **Limits.**
   - Before a run is planned, the service checks, in this order:
     - `STUDIO_PUBLIC_CHAT_RATE_VISITOR` (default 10) per visitor;
     - `STUDIO_PUBLIC_CHAT_RATE_IP` (default 30) per client IP;
     - both over `STUDIO_PUBLIC_CHAT_RATE_WINDOW` (default 60 s);
     - then the workflow's `daily_limit` through a counter keyed by the UTC day.
   - Going over gives `RATE_LIMITED` with `retry_after`, or `CHAT_DAILY_LIMIT` (429). The run is not started.
   - Session creation and reads have their own per-IP limit. `TEXT_MAX` and `max_turns` stay as they are.
6. **Frames.**
   - The studio sends `Content-Security-Policy: frame-ancestors 'none'` and `X-Frame-Options: DENY` on every page,
     except `/c/{slug}`.
   - `/c/{slug}` sends `frame-ancestors 'self' <embed_origins>`, or `'none'` when the list is empty, and no
     `X-Frame-Options`.
   - Compose: nginx gets `location /c/`. It uses `auth_request` on `GET /api/public/chat/{slug}/frame`, which only
     returns the header, then copies the header (`auth_request_set`) and serves `index.html`. The other locations
     add the deny headers.
   - All-in-one image: a small middleware in `api/static.py` does the same.
   - Vite dev server: no frame headers.
7. **Embed.** `?embed=1` gives a compact layout: no studio header, a transparent outer background, and the
   `channel = "embed"` session.
   - **iframe snippet**: `<iframe src=".../c/{slug}?embed=1">`. In Safari, which blocks cookies in frames, the chat
     works for the page view but the history is not kept.
   - **widget**: `<script src=".../c/widget.js" data-slug="{slug}" async>`.
     - `widget.js` is a separate Vite entry, plain TypeScript, with no React. It draws a bubble that opens and closes
       the iframe, with the options `data-position` and `data-open`.
     - The script stores the visitor token in the host page's localStorage and passes it to the iframe with
       `postMessage`. The iframe sends it in `X-Chat-Visitor`. When the host has no token, the iframe posts back the
       one it gets from the server.
     - The iframe accepts messages only from the origins in `embed_origins`. The script accepts messages only from
       the studio origin.
     - The host site can read that token. The handbook says so.
8. **Builders.**
   - `GET /api/workflows/{wid}/chat/visitors` lists the sessions with `channel` `web` or `embed`, without owner names
     or visitor ids. It needs the run right.
   - The Chat tab shows them read-only, with the builder's full steps.
   - Retention deletes them as it deletes other sessions.
9. **Errors.** New codes:
   - `CHAT_NOT_PUBLISHED`
   - `CHAT_SLUG_INVALID`
   - `CHAT_SLUG_TAKEN`
   - `CHAT_SIGN_IN_REQUIRED`
   - `CHAT_DAILY_LIMIT`
   - `CHAT_EMBED_ORIGIN_INVALID`
   - Each goes in CATALOG, `docs/api-errors.md` and both locales.
   - `CHAT_ACCESS_NOT_AVAILABLE` stays in the catalog. It is no longer raised for these values.

## Alternatives Considered

- **Reuse `/ws/run` with a visitor token.** Rejected. That socket takes a workflow id and any input and streams raw
  events. A separate socket that can only send chat messages keeps the attack surface small.
- **An id in localStorage for direct visits.** Rejected for the page itself, because any script on the page could read
  it. The widget uses the host's storage only because it has to.
- **A widget that draws its own chat UI.** Rejected. It needs a second chat UI, CORS and style isolation.
- **A pinned published version.** Not now. Versions exist, so it can come later as a setting.

## Consequences

- The run socket and the studio REST API are unchanged. The public surface is one router, one socket and one
  service.
- Frame protection for the whole studio comes with this work.
- A deployment over plain HTTP gets no `Partitioned` cookie. The iframe then keeps no history in any browser, but the
  direct link and the widget keep it.
