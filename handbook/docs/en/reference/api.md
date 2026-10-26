# HTTP API

The UI uses the same API as any client. The interactive OpenAPI page is at
`/docs` on the API (<http://localhost:8000/docs> in development).

Services that only start workflows use the public API: see
[Public API and SDKs](../run/public-api.md) and the
[Public API reference](public-api.md) (`/openapi.public.json`, `/docs/public`).

## Envelope

Every REST response is an envelope:

```jsonc
// success
{"success": true, "data": <payload>, "error": null}
// error
{"success": false, "data": null, "error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password", "details": null}}
```

`code` is stable `UPPER_SNAKE` and is the contract; `message` is English for
humans and logs. Clients translate by `code` and fall back to `message`. The
codes are listed in [Error codes](errors.md).

Workflow checks work the same way. `POST /api/validate`, saving a workflow
(`POST /api/workflows`) and using a template return `errors`, a list of English
messages, and `issues`, their codes in the same order: `{"code", "params"}`, or
`null` for a message without one. A run's `error` event over WebSocket carries
`issues` too when it reports these checks. The editor shows `issues` in the UI
language.

## Authentication

| Client | How |
| --- | --- |
| API client | `POST /api/auth/login` → `data.token`; then `Authorization: Bearer <token>` |
| Browser | The `studio_session` cookie, plus `X-Requested-With: studio` on writes |
| WebSocket | The cookie, or `?token=<token>` |
| Workflow trigger | `Authorization: Bearer wft_…` on `/api/hooks/*` and `/api/lg/*` only |

## Running a workflow over WebSocket

```text
WS /ws/run
→ {"workflow_id": "…", "input": {…}}             start a saved workflow
→ {"resume_run_id": "…", "response": "approved"}  answer a waiting Human node
→ {"workflow_id": "…", "workflow": {…}, …}       run the editor's unsaved graph
→ {"workflow_id": "…", "input": {…}, "steps": 1}  pause after one superstep
→ {"workflow_id": "…", "input": {…}, "until": "node_id"}  pause after that node
→ {"type": "cancel"}                              cancel the current run
← {"type": "run_started", …} {"type": "node_started", …} {"type": "node_token", …}
  {"type": "node_finished", …} … {"type": "run_finished", …}
```

## Endpoints

??? abstract "Auth and account"

    ```text
    POST   /api/auth/register
    POST   /api/auth/login
    POST   /api/auth/logout
    GET    /api/auth/options
    POST   /api/auth/password-reset
    POST   /api/auth/password-reset/confirm
    GET    /api/me
    POST   /api/me/password
    ```

??? abstract "Workflows, versions, sharing"

    ```text
    GET    /api/workflows                       POST   /api/workflows
    GET    /api/workflows/{wid}                 PATCH  /api/workflows/{wid}
    DELETE /api/workflows/{wid}                 POST   /api/workflows/{wid}/duplicate
    GET    /api/workflows/{wid}/dependents      POST   /api/validate
    GET    /api/workflows/{wid}/versions        GET    /api/workflows/{wid}/versions/{n}
    GET    /api/workflows/{wid}/versions/diff   POST   /api/workflows/{wid}/versions/{n}/restore
    GET    /api/workflows/{wid}/shares          PUT    /api/workflows/{wid}/shares
    DELETE /api/workflows/{wid}/shares/{target}
    PUT    /api/workflows/{wid}/team-shares     DELETE /api/workflows/{wid}/team-shares/{tid}
    GET    /api/workflows/{wid}/transfer        POST   /api/workflows/{wid}/transfer
    GET    /api/workflows/{wid}/python          (the code, node lines; ?version=n)
    GET    /api/workflows/{wid}/export/python   (the .py file to download)
    GET    /api/workflows/{wid}/code            (?language=python|typescript; same data as /python)
    GET    /api/workflows/{wid}/export/{language}  (python: the .py file, typescript: the LangGraph.js .ts file)
    GET    /api/workflows/{wid}/export/{language}/project  (the runnable LangGraph project zip for langgraph dev)
    ```

??? abstract "Runs"

    ```text
    GET    /api/workflows/{wid}/runs          (?tests=true: test runs)
    GET    /api/runs/pending
    GET    /api/runs/{run_id}/checkpoints   (time travel; fork: WS /ws/run {"fork": {...}})
    POST   /api/runs/{run_id}/cancel
    WS     /ws/run
    ```

??? abstract "API triggers and deliveries"

    ```text
    GET    /api/workflows/{wid}/tokens          POST   /api/workflows/{wid}/tokens
    DELETE /api/workflows/{wid}/tokens/{tid}    POST   /api/workflows/{wid}/tokens/{tid}/rotate-secret
    POST   /api/hooks/workflows/{wid}/runs      GET    /api/hooks/workflows/{wid}/runs/{run_id}
    GET    /api/workflows/{wid}/deliveries      POST   /api/workflows/{wid}/deliveries/{did}/redeliver
    GET    /api/workflows/{wid}/mcp             PUT    /api/workflows/{wid}/mcp
    POST   /mcp                                 (MCP Streamable HTTP, workflow token)
    ```

??? abstract "LangGraph Agent Server API (subset)"
    LangGraph-compatible API ([guide](../run/agent-server-api.md)), `x-api-key: wft_…` or a JWT.

    ```text
    GET    /api/lg/info                         POST   /api/lg/assistants/search
    GET    /api/lg/assistants/{id}             GET    /api/lg/assistants/{id}/graph
    GET    /api/lg/assistants/{id}/schemas     POST   /api/lg/threads
    POST   /api/lg/threads/search               GET    /api/lg/threads/{tid}
    DELETE /api/lg/threads/{tid}               GET    /api/lg/threads/{tid}/state
    POST   /api/lg/threads/{tid}/history       POST   /api/lg/threads/{tid}/runs
    POST   /api/lg/threads/{tid}/runs/wait     POST   /api/lg/threads/{tid}/runs/stream
    GET    /api/lg/threads/{tid}/runs          GET    /api/lg/threads/{tid}/runs/{rid}
    GET    /api/lg/threads/{tid}/runs/{rid}/join  POST /api/lg/threads/{tid}/runs/{rid}/cancel
    POST   /api/lg/runs                         POST   /api/lg/runs/wait
    POST   /api/lg/runs/stream
    ```

??? abstract "Schedules"

    ```text
    GET    /api/workflows/{wid}/schedules       POST   /api/workflows/{wid}/schedules
    PATCH  /api/workflows/{wid}/schedules/{sid} DELETE /api/workflows/{wid}/schedules/{sid}
    POST   /api/schedules/preview
    ```

??? abstract "Chat triggers"

    ```text
    GET    /api/workflows/{wid}/chat-triggers       POST   /api/workflows/{wid}/chat-triggers
    PATCH  /api/workflows/{wid}/chat-triggers/{tid} DELETE /api/workflows/{wid}/chat-triggers/{tid}
    (owner or admin; {channel_id, place: "dm" | channel or chat id, command, input_field, reply_field, enabled})
    ```

??? abstract "Workflow tests"

    ```text
    GET    /api/workflows/{wid}/tests          POST   /api/workflows/{wid}/tests
    PUT    /api/workflows/{wid}/tests/{tid}    DELETE /api/workflows/{wid}/tests/{tid}
    POST   /api/workflows/{wid}/tests/run      ({test_ids?, mock?, version?}: version = a stored earlier version)
    GET    /api/workflows/{wid}/tests/runs     (suite history)
    GET    /api/workflows/{wid}/tests/runs/{sid}   (with the comparison to an earlier version)
    POST   /api/workflows/{wid}/tests/runs/{sid}/cancel
    POST   /api/workflows/{wid}/tests/runs/{sid}/langsmith
    POST   /api/workflows/{wid}/tests/from-run/{run_id}   (a draft case from a run, not saved)
    ```

??? abstract "Templates"

    ```text
    GET    /api/templates                       POST   /api/templates
    POST   /api/templates/import                DELETE /api/templates/{tid}
    GET    /api/templates/{tid}/export          POST   /api/templates/{tid}/use
    ```

??? abstract "Credentials and providers"

    ```text
    GET    /api/providers                       POST   /api/providers/{pid}/test
    GET    /api/credentials                     POST   /api/credentials
    PUT    /api/credentials/{cid}               DELETE /api/credentials/{cid}
    GET    /api/credentials/{cid}/models        POST   /api/credentials/{cid}/embeddings/test
    ```

??? abstract "Knowledge bases"

    ```text
    GET    /api/knowledge-bases                 POST   /api/knowledge-bases
    GET    /api/knowledge-bases/{kid}           PUT    /api/knowledge-bases/{kid}
    DELETE /api/knowledge-bases/{kid}           POST   /api/knowledge-bases/{kid}/documents
    DELETE /api/knowledge-bases/{kid}/documents/{did}
    POST   /api/knowledge-bases/{kid}/reindex   POST   /api/knowledge-bases/{kid}/search
    ```

??? abstract "MCP servers"

    ```text
    GET    /api/mcp/servers                     POST   /api/mcp/servers
    PUT    /api/mcp/servers/{sid}               DELETE /api/mcp/servers/{sid}
    POST   /api/mcp/servers/{sid}/discover
    ```

??? abstract "Approvals and identities"

    ```text
    GET    /api/approvals/channels              POST   /api/approvals/channels
    PUT    /api/approvals/channels/{cid}        DELETE /api/approvals/channels/{cid}
    POST   /api/approvals/channels/{cid}/test   POST   /api/approvals/channels/{cid}/register-webhook
    POST   /api/approvals/callback/{kind}       GET|POST /api/approvals/callback/{kind}/{cid}
    POST   /api/channels/events/slack           (Slack Events API: chat triggers; Telegram messages use the callback URL)
    GET    /api/approvals/identities            PUT    /api/approvals/identities
    POST   /api/approvals/identities/{kind}/send-code
    POST   /api/approvals/identities/{kind}/verify
    GET    /api/approvals/link                  POST   /api/approvals/link
    GET    /api/approvals/audit
    GET    /api/approvals/inbox                 POST   /api/approvals/inbox/{run_id}
    GET    /api/approvals/slack/oauth           POST   /api/approvals/slack/oauth/start
    GET    /api/approvals/slack/oauth/callback
    ```

??? abstract "Notifications"

    ```text
    GET    /api/notifications                   POST   /api/notifications/{nid}/read
    POST   /api/notifications/read-all
    GET    /api/notifications/preferences       PUT    /api/notifications/preferences
    WS     /ws/notifications
    ```

??? abstract "Users, teams, administration"

    ```text
    GET    /api/roles
    GET    /api/admin/users                     PATCH  /api/admin/users/{target}
    DELETE /api/admin/users/{target}            POST   /api/admin/users/{target}/password-reset
    GET    /api/admin/policy                    PUT    /api/admin/policy
    GET    /api/admin/langsmith                 PUT    /api/admin/langsmith
    GET    /api/admin/audit
    GET    /api/teams                           POST   /api/teams
    PATCH  /api/teams/{tid}                     DELETE /api/teams/{tid}
    POST   /api/teams/{tid}/members             DELETE /api/teams/{tid}/members/{member}
    ```

??? abstract "Import, code, meta"

    ```text
    POST   /api/import                          GET    /api/import/{jid}
    POST   /api/import/{jid}/finalize
    POST   /api/code/test
    GET    /api/health                          GET    /api/meta/runtime
    GET    /api/tools
    ```
