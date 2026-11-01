# Public Chat API compatibility

This policy covers the public Chat HTTP API and socket protocol. It takes
effect with the phase-1 Chat API handbook. Workflow-trigger endpoints and
internal studio APIs have their own contracts.

## Versions and additive changes

New clients pin `/api/public/v1/chat/{slug}` and
`/ws/public/v1/chat/{slug}`. The URL's `v1` is the API major. OpenAPI and
AsyncAPI document versions describe their documents; they do not select a
different endpoint or replace the API major.

Within v1, changes are additive: optional response fields and new server
event types can be introduced. Clients must ignore unknown response fields
and event types, while retaining support for the fields/events they know.
Send only the documented client frame fields. Removing or renaming an
existing required contract, or changing its meaning incompatibly, requires
a new API major (`v2`).

SDK majors follow the public API major once the chat SDKs ship. The currently
published SDKs' workflow-run helpers do not imply that the planned chat
helpers or React/native toolkit are already available.

## Legacy paths

| Path | Current behavior |
| --- | --- |
| `/api/public/chat/{slug}/...` | Legacy HTTP alias of the v1 handlers; use the versioned URL in new integrations |
| `/ws/public/chat/{slug}` | Legacy same-origin socket with untyped `{chat_session_id,message}` / `{chat_session_id,response}`; emits `node_token` and `run_summary` |
| `/ws/public/v1/chat/{slug}` | Typed `message`/`answer` with optional first `auth`; emits `token`, `done`, `v` and per-connection `seq` |

Legacy paths are deprecated for new integrations but remain available while
the built-in page/widget uses them. The old socket is **not** a typed v1
alias: migrate frame parsing as well as the URL. Cross-origin third-party
user authentication uses the v1 socket. See the [Chat API guide](../run/chat-api.md).

## Deprecation and sunset

A breaking successor is published on a new major path. v1 stays supported
for **at least 12 months after v2 ships**. When a version is formally
deprecated, its responses will carry `Deprecation` and `Sunset` headers,
with a migration notice and a sunset date respecting that minimum window.
There is no announced v2 or v1 sunset date, and these response headers have
not yet been enabled. The policy is a commitment, not a claim that a sunset
is already scheduled.

## Upgrade checklist

1. Read the [changelog](https://github.com/quinguyen1502/superstep/blob/develop/CHANGELOG.md)
   and the migration notice for the target version.
2. Compare the [OpenAPI JSON](openapi.public.json),
   [AsyncAPI](https://github.com/quinguyen1502/superstep/blob/develop/docs/asyncapi/chat-v1.yaml)
   and [frame schemas](https://github.com/quinguyen1502/superstep/tree/develop/backend/app/api/schemas/chat_ws_v1).
3. Test auth/refresh, stream completion and interruption, Human answers,
   attachments, ratings and recovery from stored turns.
4. Pin the API path and a compatible SDK version, and handle unknown
   optional fields/events. Test the new major before switching traffic.
