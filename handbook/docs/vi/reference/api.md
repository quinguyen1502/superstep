# HTTP API

UI dùng cùng API với mọi client khác. Trang OpenAPI tương tác nằm ở `/docs` của
API (<http://localhost:8000/docs> khi phát triển).

Dịch vụ chỉ cần khởi chạy workflow thì dùng API công khai: xem
[API công khai và SDK](../run/public-api.md) và
[Tham chiếu API công khai](public-api.md) (`/openapi.public.json`, `/docs/public`).

## Envelope

Mọi response REST đều là một envelope:

```jsonc
// success
{"success": true, "data": <payload>, "error": null}
// error
{"success": false, "data": null, "error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password", "details": null}}
```

`code` dạng `UPPER_SNAKE` ổn định và là hợp đồng giữa hai bên; `message` là
tiếng Anh, cho người đọc và log. Client dịch theo `code` và dùng `message` khi
không có bản dịch. Danh sách mã ở [Mã lỗi](errors.md).

Phần kiểm tra workflow cũng vậy. `POST /api/validate`, lưu workflow
(`POST /api/workflows`) và dùng một mẫu đều trả về `errors`, danh sách thông báo
tiếng Anh, và `issues`, mã của chúng theo cùng thứ tự: `{"code", "params"}`, hoặc
`null` với thông báo không có mã. Sự kiện `error` của run qua WebSocket cũng có
`issues` khi báo các lỗi kiểm tra này. Editor hiện `issues` theo ngôn ngữ giao diện.

## Xác thực

| Client | Cách |
| --- | --- |
| API client | `POST /api/auth/login` → `data.token`; then `Authorization: Bearer <token>` |
| Trình duyệt | Cookie `studio_session`, cộng `X-Requested-With: studio` cho request ghi |
| WebSocket | Cookie, hoặc `?token=<token>` |
| Trigger workflow | `Authorization: Bearer wft_…`, chỉ cho `/api/hooks/*` và `/api/lg/*` |

## Chạy workflow qua WebSocket

```text
WS /ws/run
→ {"workflow_id": "…", "input": {…}}             chạy một workflow đã lưu
→ {"resume_run_id": "…", "response": "approved"}  trả lời node Human đang chờ
→ {"workflow_id": "…", "workflow": {…}, …}       chạy graph chưa lưu của trình soạn thảo
→ {"workflow_id": "…", "input": {…}, "steps": 1}  dừng sau một superstep
→ {"workflow_id": "…", "input": {…}, "until": "node_id"}  dừng sau node đó
→ {"type": "cancel"}                              huỷ run hiện tại
← {"type": "run_started", …} {"type": "node_started", …} {"type": "node_token", …}
  {"type": "node_finished", …} … {"type": "run_finished", …}
```

## Endpoint

??? abstract "Xác thực và tài khoản"

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

??? abstract "Workflow, phiên bản, chia sẻ"

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
    GET    /api/workflows/{wid}/python          (mã, các dòng của node; ?version=n)
    GET    /api/workflows/{wid}/export/python   (file .py để tải về)
    GET    /api/workflows/{wid}/code            (?language=python|typescript; như /python)
    GET    /api/workflows/{wid}/export/{language}  (python: file .py, typescript: file .ts LangGraph.js)
    GET    /api/workflows/{wid}/export/{language}/project  (zip dự án LangGraph chạy được bằng langgraph dev)
    ```

??? abstract "Runs"

    ```text
    GET    /api/workflows/{wid}/runs          (?tests=true: các run test)
    GET    /api/runs/pending
    GET    /api/runs/{run_id}                (một run cùng các sự kiện, như lịch sử liệt kê; run được gọi của công cụ workflow)
    GET    /api/runs/{run_id}/checkpoints   (time travel; fork: WS /ws/run {"fork": {...}})
    POST   /api/runs/{run_id}/cancel
    WS     /ws/run
    ```

??? abstract "API trigger và lần gửi"

    ```text
    GET    /api/workflows/{wid}/tokens          POST   /api/workflows/{wid}/tokens
    DELETE /api/workflows/{wid}/tokens/{tid}    POST   /api/workflows/{wid}/tokens/{tid}/rotate-secret
    POST   /api/hooks/workflows/{wid}/runs      GET    /api/hooks/workflows/{wid}/runs/{run_id}
    GET    /api/workflows/{wid}/deliveries      POST   /api/workflows/{wid}/deliveries/{did}/redeliver
    GET    /api/workflows/{wid}/mcp             PUT    /api/workflows/{wid}/mcp
    POST   /mcp                                 (MCP Streamable HTTP, workflow token)
    ```

??? abstract "LangGraph Agent Server API (một phần)"
    API tương thích LangGraph ([hướng dẫn](../run/agent-server-api.md)), `x-api-key: wft_…` hoặc JWT.

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

??? abstract "Lịch chạy"

    ```text
    GET    /api/workflows/{wid}/schedules       POST   /api/workflows/{wid}/schedules
    PATCH  /api/workflows/{wid}/schedules/{sid} DELETE /api/workflows/{wid}/schedules/{sid}
    POST   /api/schedules/preview
    ```

??? abstract "Chat trigger"

    ```text
    GET    /api/workflows/{wid}/chat-triggers       POST   /api/workflows/{wid}/chat-triggers
    PATCH  /api/workflows/{wid}/chat-triggers/{tid} DELETE /api/workflows/{wid}/chat-triggers/{tid}
    (chủ hoặc admin; {channel_id, place: "dm" | id kênh hoặc chat, command, input_field, reply_field, enabled})
    ```

??? abstract "Chat và trang chat công khai"

    ```text
    GET    /api/workflows/{wid}/chat                PUT    /api/workflows/{wid}/chat   (cài đặt; PUT cần quyền chủ sở hữu)
    GET    /api/workflows/{wid}/chat/sessions       POST   /api/workflows/{wid}/chat/sessions
    GET    /api/chat/sessions/{sid}?view=builder|visitor   DELETE /api/chat/sessions/{sid}
    GET    /api/workflows/{wid}/chat/visitors       GET    /api/workflows/{wid}/chat/visitors/{sid}   (chỉ xem)
    GET    /api/workflows/{wid}/chat/logo?v=      (logo: data: URL trong PUT để đặt, "" để bỏ)
    WS     /ws/run   {chat_session_id, message} | {chat_session_id, resume_run_id, response}

    Không cần đăng nhập (trang công khai, theo slug):
    GET    /api/public/chat/{slug}                  (title, intro, suggestions, access, steps_mode, signed_in, embed_origins, logo)
    GET    /api/public/chat/{slug}/sessions         POST   /api/public/chat/{slug}/sessions   ({embed?})
    GET    /api/public/chat/{slug}/sessions/{sid}
    GET    /api/public/chat/{slug}/logo?v=<logo>
    WS     /ws/public/chat/{slug}   {chat_session_id, message} | {chat_session_id, response}
    GET    /api/public/chat-frame?path=/c/{slug}    (frame-ancestors của trang, cho nginx)
    ```

    Khách chat ẩn danh được nhận diện bằng một cookie HttpOnly, hoặc header
    `X-Chat-Visitor` (`?visitor=` trên socket) khi trang được nhúng. Gửi
    `X-Chat-Visitor: new` để nhận token mới trong `visitor_token`.

??? abstract "Kiểm thử workflow"

    ```text
    GET    /api/workflows/{wid}/tests          POST   /api/workflows/{wid}/tests
    PUT    /api/workflows/{wid}/tests/{tid}    DELETE /api/workflows/{wid}/tests/{tid}
    POST   /api/workflows/{wid}/tests/run      ({test_ids?, mock?, version?}: version = một phiên bản cũ đã lưu)
    GET    /api/workflows/{wid}/tests/runs     (lịch sử các lần chạy test)
    GET    /api/workflows/{wid}/tests/runs/{sid}   (kèm so sánh với phiên bản trước)
    POST   /api/workflows/{wid}/tests/runs/{sid}/cancel
    POST   /api/workflows/{wid}/tests/runs/{sid}/langsmith
    POST   /api/workflows/{wid}/tests/from-run/{run_id}   (bản nháp test case từ một run, chưa lưu)
    ```

??? abstract "Mẫu"

    ```text
    GET    /api/templates                       POST   /api/templates
    POST   /api/templates/import                DELETE /api/templates/{tid}
    GET    /api/templates/{tid}/export          POST   /api/templates/{tid}/use
    ```

??? abstract "Credential và nhà cung cấp"

    ```text
    GET    /api/providers                       POST   /api/providers/{pid}/test
    GET    /api/credentials                     POST   /api/credentials
    PUT    /api/credentials/{cid}               DELETE /api/credentials/{cid}
    GET    /api/credentials/{cid}/models        POST   /api/credentials/{cid}/embeddings/test
    ```

??? abstract "Kho tri thức"

    ```text
    GET    /api/knowledge-bases                 POST   /api/knowledge-bases
    GET    /api/knowledge-bases/{kid}           PUT    /api/knowledge-bases/{kid}
    DELETE /api/knowledge-bases/{kid}           POST   /api/knowledge-bases/{kid}/documents
    DELETE /api/knowledge-bases/{kid}/documents/{did}
    POST   /api/knowledge-bases/{kid}/reindex   POST   /api/knowledge-bases/{kid}/search
    ```

??? abstract "Máy chủ MCP"

    ```text
    GET    /api/mcp/servers                     POST   /api/mcp/servers
    PUT    /api/mcp/servers/{sid}               DELETE /api/mcp/servers/{sid}
    POST   /api/mcp/servers/{sid}/discover
    ```

??? abstract "Duyệt và danh tính"

    ```text
    GET    /api/approvals/channels              POST   /api/approvals/channels
    PUT    /api/approvals/channels/{cid}        DELETE /api/approvals/channels/{cid}
    POST   /api/approvals/channels/{cid}/test   POST   /api/approvals/channels/{cid}/register-webhook
    POST   /api/approvals/callback/{kind}       GET|POST /api/approvals/callback/{kind}/{cid}
    POST   /api/channels/events/slack           (Slack Events API: chat trigger; tin nhắn Telegram dùng URL callback)
    GET    /api/approvals/identities            PUT    /api/approvals/identities
    POST   /api/approvals/identities/{kind}/send-code
    POST   /api/approvals/identities/{kind}/verify
    GET    /api/approvals/link                  POST   /api/approvals/link
    GET    /api/approvals/audit
    GET    /api/approvals/inbox                 POST   /api/approvals/inbox/{run_id}
    GET    /api/approvals/slack/oauth           POST   /api/approvals/slack/oauth/start
    GET    /api/approvals/slack/oauth/callback
    ```

??? abstract "Thông báo"

    ```text
    GET    /api/notifications                   POST   /api/notifications/{nid}/read
    POST   /api/notifications/read-all
    GET    /api/notifications/preferences       PUT    /api/notifications/preferences
    WS     /ws/notifications
    ```

??? abstract "Người dùng, nhóm, quản trị"

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
