# Vietnamese glossary

Terms for `vi.json`, `README.vi.md` and `handbook/docs/vi`. The rules that use it are in [UI conventions](../../../docs/ui-conventions.md) (rule 10).

- Address the user as "bạn".
- "Vui lòng" only in error messages.
- Use the new-style tone marks: xoá, huỷ, khoá, tuỳ, mã hoá.

| English | Vietnamese | Note |
|---|---|---|
| workflow, node, edge, run, state, reducer, schema, subgraph, trace, checkpoint, token, webhook, trigger, cron, prompt, credential, API key, model | keep in English | "nút" means a button, never a node; no "lượt chạy"/"lần chạy", no "thông tin xác thực" |
| node type names (Start, End, LLM, Tool, Condition, Human, Join, Subgraph, …) | keep in English | match the canvas; write "node LLM", "node Code" |
| input, output | keep in English ("Trường input", "Input của run") | |
| field | trường | "trường state" |
| key (stored secret, dict key) | khoá | "API key" stays |
| provider | nhà cung cấp | |
| server | máy chủ | "MCP server" = máy chủ MCP; exception: the subprocess-runtime badge (below) says "server" as the owner chose |
| tool | công cụ | MCP tool = công cụ MCP; the node type "Tool" stays |
| knowledge base | kho tri thức | |
| approve, approval, approver | duyệt, yêu cầu duyệt, người duyệt | not "phê duyệt" |
| template | mẫu | "prompt template" stays |
| version, rollback | phiên bản, khôi phục | |
| label | nhãn | |
| optional | tuỳ chọn | not "không bắt buộc" |
| email | email | not "e-mail" |
| replay | xem lại | |
| test case, test run | test case, run test | |
| Python, TypeScript, Deno, npm, package, Web API | keep in English | Mode options read "Code (Python)" / "Code (TypeScript)" in both locales; "Ngôn ngữ" for a language label |
| Chat (the tab, the setting) | Chat | "Cài đặt Chat", "Bật chat"; not "trò chuyện" for the feature name |
| conversation, chat (one session) | cuộc trò chuyện | "Cuộc trò chuyện mới" for New chat |
| message | tin nhắn | |
| step (a node run shown in a chat) | bước | "Tên bước" for the labels mode |
| visitor (the person chatting) | người chat | the Human "Answered by" option too |
| builder (the studio view of a chat) | người dựng | |
| View as (the chat's view switch) | Xem dưới góc nhìn | |
| Workflow builder (View as option) | Người dựng workflow | |
| Chat visitor (View as option: the public chat preview) | Khách chat | "người chat" stays for the Human node's Answered by |
| Builder / Visitor (short View as labels on the compact chat toolbar) | Người dựng / Khách | |
| You're previewing what chat visitors see (visitor view banner) | Bạn đang xem trước như khách chat | |
| public page, publish (a chat open to anyone with the link or signed-in users) | trang công khai, công khai | "Bật Chat để công khai trang" |
| page address (the chat's slug) | địa chỉ trang | |
| intro (the page's text before the first message) | lời giới thiệu | |
| suggested message | tin nhắn gợi ý | |
| Visitors (the Chat tab's list of public chats) | Khách | "Chat của khách", read-only |
| embed, frame (iframe) | nhúng, frame | "Các site được nhúng chat này" |
| chat bubble (the embed widget) | bong bóng chat | |
| answered by | người trả lời | the option "A reviewer" is "Người duyệt" |
| round (an Agent node's model call and the tool calls it asks for) | vòng | "Số vòng tối đa", "Vòng 2" in the trace |
| tool call | lần gọi công cụ | |
| parameter (what a model passes to a tool) | tham số | |
| workflow tool (an Agent tool that runs another saved workflow) | công cụ workflow | the source in the tool menu is "Another workflow" / "Workflow khác" |
| child run / called run (the run a workflow tool starts) | run được gọi | "Called by …" / "Được gọi bởi …"; the parent waits: "Waiting for another workflow" / "Đang chờ một workflow khác" |
| result (the fields a workflow tool gives back) | kết quả | |
| task prompt (an Agent node's prompt) | prompt nhiệm vụ | "System prompt" stays |
| retention | thời gian lưu | "Thời gian lưu (ngày)" |
| Runs on host (subprocess Code runtime; never "not isolated" / "without isolation") | Chạy trực tiếp trên server; "Chạy trên server" on the canvas node; never "không cách ly" | longer texts say "without Docker limiting its access" / "không có Docker giới hạn quyền"; "cách ly" / "isolation" only for what the Docker sandbox does | warning badge with a tooltip: "Code runs directly on the server, without Docker limiting its access. Use only for trusted code." / "Code đang chạy trực tiếp trên máy chủ, không có Docker giới hạn quyền. Chỉ nên dùng cho code tin cậy." |
| General · Settings · Data · Execution (Node Config tabs, rule 12) | Chung · Cài đặt · Dữ liệu · Thực thi | |
