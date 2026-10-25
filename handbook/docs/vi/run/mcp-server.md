# Workflow làm công cụ MCP

Superstep cũng là một MCP server. Bật cho một workflow là các client MCP như
Claude Desktop, Cursor, Claude Code hay agent khác gọi được workflow đó như một
công cụ. Đây là chiều ngược lại với [MCP server](../guide/mcp.md), nơi workflow
của bạn gọi công cụ của các server bạn thêm vào.

## Bật

1. Mở workflow, chọn **Thêm > API**.
2. Ở thẻ **Token**, tạo một token. Client xác thực bằng token này, giống hệt
   [API công khai](public-api.md).
3. Ở thẻ **MCP**, bật **Cung cấp dưới dạng công cụ MCP**. Mọi workflow đều tắt
   cho tới khi bạn bật, và chỉ người được quản lý token của workflow mới đổi
   được.
4. Chọn client và sao chép cấu hình. Ngay sau khi tạo token, đoạn cấu hình đã
   chứa sẵn token; nếu không, hãy thay `<token>`.

Server nằm tại `https://<studio của bạn>/mcp` (Streamable HTTP, phản hồi JSON,
không có session). Gửi token qua `Authorization: Bearer wft_...` hoặc
`X-Workflow-Token: wft_...`.

```json title=".cursor/mcp.json"
{
  "mcpServers": {
    "superstep-refunds": {
      "url": "https://superstep.example.com/mcp",
      "headers": { "Authorization": "Bearer wft_..." }
    }
  }
}
```

Claude Desktop chỉ khởi chạy server cục bộ, nên cấu hình của nó chạy
`mcp-remote` để tới server HTTP; Claude Code nhận URL trực tiếp:

```bash
claude mcp add --transport http superstep-refunds https://superstep.example.com/mcp \
  --header "Authorization: Bearer wft_..."
```

## Công cụ

Mỗi token thuộc về một workflow, nên client thấy ba công cụ:

| Công cụ | Chức năng |
| --- | --- |
| `run_<tên workflow>` | Chạy phiên bản đã lưu mới nhất. Input schema là các trường state của workflow; tham số là input của run. Trả về kết quả run: `status`, `final_state`, `error`, `waiting`, `metrics`. |
| `get_run` | Trạng thái và kết quả của một run (`run_id`). |
| `resume_run` | Trả lời node Human mà run đang chờ (`run_id`, `response`: văn bản, hoặc `true` / `false` để duyệt / từ chối) rồi chờ run dừng lại lần nữa. |

Run là run API bình thường: hiện trong lịch sử của workflow với nguồn API, tính
vào giới hạn tốc độ của token (`STUDIO_TRIGGER_RATE_LIMIT`) và qua cùng kiểm
tra input. Một lần gọi công cụ chờ tối đa `STUDIO_SYNC_WAIT_MAX` giây; run vẫn
đang chạy khi đó trả về `status: running` kèm `run_id`, client hỏi lại bằng
`get_run`.

### Node Human

Run tới một node Human trả về `status: waiting` kèm `run_id` và lời nhắc của
node trong `waiting`. Client (hoặc người dùng client) trả lời bằng
`resume_run`; run tiếp tục từ checkpoint. Mọi người cũng trả lời được ngay
trong Superstep, trong editor hoặc hộp thư, như mọi run đang chờ.

### Lỗi

Lỗi trả về dưới dạng lỗi công cụ (`isError: true`) với nội dung là đối tượng
lỗi chung, ví dụ `{"error": {"code": "RUN_NOT_WAITING", ...}}`. Yêu cầu không
có token hợp lệ bị từ chối trước MCP với `401 TRIGGER_TOKEN_INVALID`; workflow
chưa bật trả về `403 MCP_SERVER_DISABLED`.

## Chế độ demo

Trong bản demo công khai, tài khoản khách không tạo được token hay đổi cài
đặt, nên không cung cấp được workflow.
