# Chạy

Workflow chạy được theo sáu cách. Cách nào cũng đi qua cùng một engine, tạo
cùng một kiểu trace và hiện trong lịch sử run (**Chạy → Xem tất cả**).

| Bắt đầu bởi | Cách | Nhãn trong Lịch sử |
| --- | --- | --- |
| Trình soạn thảo | **Chạy**, **Một bước** hoặc **Chạy tới đây**, qua `/ws/run` | — |
| Dịch vụ khác | `POST /api/hooks/workflows/{wid}/runs` với token của workflow | **API** |
| Client MCP | Công cụ `run_...` của workflow tại `/mcp`, với token của workflow | **API** |
| Lịch | Lịch cron gắn với workflow | **Lịch** |
| Tin nhắn chat | Một từ lệnh gửi tới Slack app hoặc bot Telegram | **Chat** |
| Người tiếp tục run | Duyệt, từ chối hoặc trả lời node Human đang chờ | — |

<div class="grid cards" markdown>

-   :material-chart-gantt:{ .lg .middle } **[Run và trace](traces.md)**

    ---

    Timeline Logs, chạy từng bước, huỷ, giới hạn và chi phí.

-   :material-account-check:{ .lg .middle } **[Duyệt bởi người](human-approval.md)**

    ---

    Run đang chờ, thông báo và duyệt qua chat.

-   :material-api:{ .lg .middle } **[API trigger và webhook](api-triggers.md)**

    ---

    Token, run sync và async, callback có chữ ký, worker.

-   :material-tools:{ .lg .middle } **[Workflow làm công cụ MCP](mcp-server.md)**

    ---

    Claude Desktop, Cursor và agent khác gọi workflow như một công cụ.

-   :material-calendar-clock:{ .lg .middle } **[Lịch chạy](schedules.md)**

    ---

    Cron, múi giờ và các mốc bị lỡ.

-   :material-message-text-outline:{ .lg .middle } **[Chạy từ chat](chat-triggers.md)**

    ---

    Tin nhắn tới Slack app hoặc bot Telegram chạy workflow; bot trả lời.

-   :material-chat-processing-outline:{ .lg .middle } **[Chat](chat.md)**

    ---

    Chat với workflow ngay trong studio, có bộ nhớ và các bước.

-   :material-flask-outline:{ .lg .middle } **[Kiểm thử workflow](tests.md)**

    ---

    Test case, Chạy tất cả, so sánh với phiên bản trước.

</div>
