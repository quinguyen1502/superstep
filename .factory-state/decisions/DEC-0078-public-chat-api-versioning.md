# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0078
- Status: Proposed on 2026-10-31. Awaiting the owner's review.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Related Requirements: REQ-0082
- Related Tasks: TASK-0215, TASK-0216, TASK-0219, TASK-0220, TASK-0221
- Related Architecture: DEC-0067 (public chat page), DEC-0010 (envelope), DEC-0077 (third-party auth)

## Context

- The chat HTTP API is only in the internal `/openapi.json`; `/openapi.public.json` (`backend/app/api/openapi_public.py`) has only the two hooks paths.
- The socket `/ws/public/chat/{slug}` takes one client frame (`{chat_session_id, message}` or `{chat_session_id, response}`, optional `locale`), streams `public_event`s (`run_started`, `node_token`, step events by steps mode, the Human question, `run_summary`, errors), accepts `{"type": "cancel"}`, then closes. There is no formal schema.
- The handbook `reference/api.md` (en, vi) lists chat endpoints without attachments and ratings.

## Options

### Versioning

- **A. Path version `/api/public/v1/chat/...` and `/ws/public/v1/chat/...`** (recommended): visible, cache and proxy friendly, matches how SDKs pin a base path. Current unversioned paths stay as aliases of v1 (the studio page and widget keep working).
- **B. Header or media-type version** (`Superstep-Version: 2026-10-31`, Stripe style): fine-grained, but invisible in logs and harder for WebSocket clients.
- **C. No version, additive changes only**: simplest, but no way to make a breaking change safely.

### Event schema

- **A. JSON Schema for each client and server frame plus an AsyncAPI 3.0 document** (recommended): AsyncAPI describes WebSocket channels; JSON Schema is reused by contract tests and to generate SDK types.
- **B. Pydantic models only, exported into the OpenAPI as components**: less tooling, but OpenAPI cannot describe the socket itself.
- **C. Prose in the handbook only**: not testable.

### Transport

- **A. Keep WebSocket as the only streaming transport** (recommended): it already streams tokens and carries cancel; browsers, Node 22+ (global `WebSocket`; `ws` for older Node) and React Native support it.
- **B. Add SSE (`POST .../messages` returning `text/event-stream`)**: simpler through some proxies and serverless functions, and usable from Python without a socket library. Costs a second code path and tests.
- Decision: no SSE in this plan. Revisit if a real client cannot use WebSocket (e.g. a serverless backend proxying the chat). The Python SDK uses the `websockets` library as an optional extra (`superstep[chat]`).

## Decision (recommended)

1. **Paths.** v1 under `/api/public/v1/chat/{slug}` and `/ws/public/v1/chat/{slug}`. The old paths are aliases (same handlers), documented as deprecated but not removed while the studio frontend uses them; the studio moves to v1 in TASK-0223.
2. **Endpoints in v1**: page settings, logo, sessions list/create/get, attachments upload/download/delete, ratings put/delete, plus `GET .../sessions/{sid}/turns?after=` for incremental history (needed for reconnection). All in `/openapi.public.json` with a `Chat` tag, response models and error codes.
3. **Socket protocol v1.**
   - Every frame has a `type`. Client frames: `auth` (DEC-0077), `message` (`chat_session_id`, `text`, `attachments[]`, `locale`), `answer` (`chat_session_id`, `turn_id`, `response`: text or form object), `cancel`. The current untyped `{chat_session_id, message|response}` frame stays accepted on the old path.
   - Server frames: `ready`, `run_started`, `token` (renamed from `node_token` in v1; the old path keeps `node_token`), `step`, `question` (Human node: prompt, kind, options, fields), `turn` (the stored turn id for rating), `done` (status), `error` (envelope).
   - Each server frame carries `v: 1` and a monotonic `seq` for de-duplication on reconnect.
   - JSON Schema files in `backend/app/api/schemas/chat_ws_v1/*.json` and `docs/asyncapi/chat-v1.yaml`; served at `/asyncapi.public.yaml`.
4. **Contract tests.** Backend tests validate every frame the socket sends against the schema; the SDK tests replay recorded frames; a CI step fails if the schema changes without a version note.
5. **Compatibility and deprecation policy** (handbook, `reference/compatibility.md`):
   - within v1 only additive changes (new optional fields, new event types that clients must ignore when unknown);
   - a breaking change needs v2; v1 stays at least 12 months after v2 ships, with a `Deprecation` and `Sunset` header (RFC 8594, RFC 9745) on v1 responses once deprecated;
   - SDK majors follow API majors.

## Rationale

- Path versions are the least surprising for third-party developers and SDKs; a formal schema makes the stream testable and lets the SDK generate types instead of copying them.

## Impacts

- New router prefix, alias routes, schema files, OpenAPI builder change, handbook pages en and vi, contract tests.

## Open Questions

1. Rename `node_token` to `token` in v1? Recommendation: yes (v1 is the first public contract); the old path keeps the old names.
2. Keep one message per socket connection, or allow a long-lived socket with many messages? Recommendation: keep one per connection in v1 (simple, proven); the SDK hides it. A multiplexed socket can come in v1 as an additive option later.
3. SSE: Recommendation: not now (see Transport).

## Approval

- Approved By: pending
- Approved On: pending

## Review Or Revisit Trigger

- A client that cannot use WebSocket, or a need for a breaking change.
