# Chat API

Tạo client cho [chat đã công khai](chat.md#cong-khai-chat) bằng HTTP để quản
lý phiên, lịch sử, tệp và đánh giá, cùng WebSocket để nhận tin nhắn dạng
stream. Chat chạy workflow đã lưu bằng tài nguyên của chủ workflow. Người
gọi chỉ truy cập được phiên của mình.

## Hợp đồng và quyền truy cập

| Hợp đồng | Server đang chạy | Nguồn |
| --- | --- | --- |
| HTTP v1 | `/openapi.public.json`, `/docs/public`, thẻ `Chat` | [Tham chiếu API công khai](../reference/public-api.md), [OpenAPI JSON](../reference/openapi.public.json) |
| Socket v1 | `/asyncapi.public.yaml` | [AsyncAPI YAML](https://github.com/quinguyen1502/superstep/blob/develop/docs/asyncapi/chat-v1.yaml) |
| Schema frame | Có trong AsyncAPI | [JSON Schema client và server](https://github.com/quinguyen1502/superstep/tree/develop/backend/app/api/schemas/chat_ws_v1) |

HTTP dùng `/api/public/v1/chat/{slug}`; stream dùng
`/ws/public/v1/chat/{slug}` (`wss://` khi chạy HTTPS). Client mới nên dùng
đường dẫn có phiên bản. Xem [Tương thích](../reference/compatibility.md) về
đường dẫn cũ và chính sách phiên bản. Mỗi kết nối socket gửi một tin nhắn
hoặc một câu trả lời Human; hiện chưa có SSE.

| Chế độ | Danh tính qua HTTP | Danh tính qua socket |
| --- | --- | --- |
| `anonymous` | Cookie chat hoặc `X-Chat-Visitor` | Cookie chat, `auth.visitor` hoặc `?visitor=` |
| `signed_in` | Session/Bearer token của studio | Session studio hoặc studio `?token=` trên cùng origin |
| `app` | `Authorization: Bearer <user JWT>` | Frame đầu `auth.token`; `?token=` là cách dự phòng |

Client ẩn danh và studio dùng cùng origin với Superstep (trang nhúng chạy
bên trong iframe của Superstep). Client gọi trực tiếp từ origin khác cần
app token và origin được phép: xem [Xác thực bên thứ ba](chat-third-party-auth.md).
`access` có thể là chuỗi đơn kiểu cũ hoặc danh sách chế độ; app token hợp lệ
được ưu tiên hơn cookie ẩn danh. Lịch sử app, ẩn danh và studio tách biệt.

## Tạo phiên

Lấy user token ngắn hạn từ backend đã xác thực của bạn. Ở đây `userToken`
là JWT đó; `baseUrl` là origin của Superstep, không có dấu gạch chéo cuối,
và `slug` là địa chỉ trang chat.

```javascript
const baseUrl = 'https://studio.example.com'
const slug = 'support'
async function chatHttp(path, options = {}) {
  const response = await fetch(`${baseUrl}/api/public/v1/chat/${slug}${path}`, {
    ...options,
    credentials: 'omit',
    headers: { ...options.headers, Authorization: `Bearer ${userToken}` },
  })
  const body = await response.json()
  if (!body.success) throw body.error
  return body.data
}
const page = await chatHttp('')
const session = await chatHttp('/sessions', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
})
const sessionId = session.id
```

JSON REST có envelope `{"success":true,"data":...,"error":null}`; lỗi có
`success:false` và `error:{code,message,details}`. Tải logo và tệp trả về
byte ảnh/tệp. Mọi route nằm trong
[Tham chiếu HTTP](../reference/api.md#public-chat-v1).

Với client ẩn danh cùng origin không dùng cookie, bắt đầu bằng
`X-Chat-Visitor: new`. Giữ `data.visitor_token` trả về khi tạo/liệt kê phiên,
gửi lại trong `X-Chat-Visitor` và dùng `auth.visitor` trên socket.
Token này cho phép đọc lịch sử của khách đó; không để người khác lấy được.

## Gửi và nhận stream

Ví dụ tiếp tục dùng `baseUrl`, `slug`, `sessionId`, `userToken` ở trên.
Token được gửi trong frame để không xuất hiện trong URL.

```javascript
const socketUrl = new URL(`/ws/public/v1/chat/${slug}`, baseUrl)
socketUrl.protocol = socketUrl.protocol === 'https:' ? 'wss:' : 'ws:'
const socket = new WebSocket(socketUrl)
let lastSeq = -1
socket.addEventListener('message', ({ data }) => {
  const frame = JSON.parse(data)
  if (frame.v !== 1 || frame.seq <= lastSeq) return
  lastSeq = frame.seq
  switch (frame.type) {
    case 'ready':
      socket.send(JSON.stringify({ type: 'auth', token: userToken }))
      socket.send(JSON.stringify({ type: 'message', chat_session_id: sessionId,
        text: 'Đơn hàng của tôi ở đâu?', attachments: [], locale: 'vi' }))
      break
    case 'token':
      // Nối frame.delta vào câu trả lời đang nhận.
      break
    case 'question':
      // Giữ frame.node và hiện frame.prompt cho người chat.
      break
    case 'turn':
      // Giữ frame.turn_id để đánh giá câu trả lời đã lưu.
      break
    case 'done':
      // Kiểm tra frame.status rồi tải lại các lượt đã lưu qua HTTP.
      break
    case 'error':
      // Xử lý frame.error.code; không hiển thị lỗi thô như HTML.
      break
    default:
      // Bỏ qua kiểu frame chưa biết; ví dụ này không cần xử lý step/run_started.
      break
  }
})
socket.addEventListener('close', () => {
  // Đóng mà chưa có done/error là gián đoạn: đọc lịch sử trước khi thử lại.
})
socket.addEventListener('error', () => {
  // Hiện lỗi kết nối mà không ghi token vào log.
})
```

## Các frame

Frame client có `type` cùng các trường dưới đây. Không thêm `v`, `seq` hay
trường tùy ý vào frame client; frame không hợp lệ trả về `CHAT_FRAME_INVALID`.
Gửi tối đa một `auth`, trước thao tác chính.

| Kiểu client | Trường |
| --- | --- |
| `auth` | `token` cho user app hoặc `visitor` cho khách ẩn danh |
| `message` | `chat_session_id`, `text`; tùy chọn `attachments` (id đã upload), `locale` (`en`/`vi`) |
| `answer` | `chat_session_id`, `response`; tùy chọn `node` lấy từ câu hỏi và `locale` |
| `cancel` | Không có trường khác; gửi khi run đang chạy |

Mọi frame server có `v:1` và `seq` tăng từ 0 trong từng kết nối. `ts`, nếu
có, là giây Unix. Bỏ qua kiểu và trường chưa biết. `seq` bắt đầu lại khi mở
socket mới; nó không phải cursor lịch sử.

| Kiểu server | Ý nghĩa |
| --- | --- |
| `ready` | Đã nhận kết nối, `protocol:"superstep-chat"`; chưa xác nhận xác thực/quyền truy cập |
| `run_started` | `run_id` của run |
| `token` | Nối `delta`; có thể kèm `node`, `field`, `iteration` |
| `step` | `event` là `started`, `finished` hoặc `error`, kèm `node`; chi tiết theo chế độ hiện bước |
| `question` | Node Human đang chờ: `node`, `prompt`, `kind`/`input_type`, có thể kèm lựa chọn/trường |
| `turn` | `turn_id` của câu trả lời đã lưu, `role`, có thể kèm `status`, `run_id`; gửi trước `done` khi lưu kịp |
| `done` | `status` là `ok`, `error`, `waiting`, `cancelled` hoặc `timeout`; sau đó server đóng socket |
| `error` | `error.code` ổn định, `message` tiếng Anh, có thể kèm `details`; không đảm bảo có `done` sau lỗi |

Một lượt trao đổi minh họa (id là giá trị mẫu):

```json
{"type":"ready","protocol":"superstep-chat","v":1,"seq":0}
{"type":"run_started","run_id":"r1","v":1,"seq":1}
{"type":"token","delta":"Hello","v":1,"seq":2}
{"type":"turn","turn_id":"t2","role":"assistant","status":"ok","run_id":"r1","v":1,"seq":3}
{"type":"done","status":"ok","run_id":"r1","v":1,"seq":4}
```

## Trả lời Human và hủy

Sau `question` và `done` có `status:"waiting"`, mở socket **mới**, xác thực
lại rồi gửi câu trả lời cho cùng phiên:

```json
{"type":"answer","chat_session_id":"session-id","node":"human-node-id","response":"yes","locale":"vi"}
```

Dùng `node` của câu hỏi và kiểu câu trả lời node Human chấp nhận (ví dụ văn
bản hoặc boolean để duyệt). Schema giao thức còn cho phép object biểu mẫu;
điều đó tự nó không bổ sung runtime biểu mẫu. Người chat không được trả lời
câu hỏi dành cho reviewer (`CHAT_ANSWER_BY_REVIEWER`). Không gửi tệp kèm câu
trả lời. Để hủy run đang chạy, gửi `{"type":"cancel"}` trên socket đó.
Ngắt kết nối cũng yêu cầu hủy; đọc lịch sử để biết kết quả cuối.

## Lịch sử và kết nối lại

`GET .../sessions` liệt kê phiên của bạn; `GET .../sessions/{sid}` gồm các
lượt đã lưu. Sau stream hoặc gián đoạn, gọi
`GET .../sessions/{sid}/turns?after=<id-lượt-cuối-đã-lưu>` để lấy lượt mới
hơn theo thứ tự; bỏ `after` để lấy tất cả. Kết quả nằm trong `data.turns`.
Cursor không tồn tại hoặc thuộc phiên khác trả `404 CHAT_TURN_NOT_FOUND`.

Dùng id lượt đã lưu để đối chiếu với câu trả lời stream tạm thời. Việc lưu
có thể trễ: poll có backoff nếu lượt cuối chưa được lưu. Không có replay
socket hay khóa idempotency cho tin nhắn. Gửi lại sau ngắt kết nối có thể
tạo run khác, nên đọc lịch sử trước. Kết nối bị gián đoạn có thể không có
`done` cuối; không thể dùng `seq` để tiếp tục stream đó.

## Tệp và đánh giá

1. Đọc `page.attachments` (`enabled`, `kinds`, `max_files`, `max_mb`).
2. Upload mỗi tệp bằng một `POST .../sessions/{sid}/attachments`, trường
   multipart `file`; giữ `data.id`. Trình duyệt tự đặt boundary Content-Type.
3. Đưa các id vào `message.attachments`. Tệp phải thuộc phiên đó và chưa
   gửi. Tệp đã gửi không được dùng lại hay xóa qua endpoint tệp chưa gửi.
4. Tải bằng `GET .../attachments/{aid}` có xác thực (byte). Xóa tệp chưa
   gửi bằng `DELETE .../attachments/{aid}`. DELETE JSON trả `data.ok`,
   không nhận trường xác nhận.

Tài liệu gồm PDF hoặc UTF-8 `.txt`, `.md`, `.csv`; ảnh gồm PNG, JPEG, WebP.
Cài đặt chat và giới hạn của operator cùng áp dụng. Upload cũng tiêu thụ
quota tin nhắn. Xem [Tệp đính kèm](chat.md#tep-inh-kem).

Đánh giá lượt assistant có trạng thái `ok` hoặc `error` bằng
`PUT .../sessions/{sid}/turns/{tid}/rating`, body `{"value":"up"}` hoặc
`{"value":"down","comment":"Thiếu ngày giao hàng"}`. Nhận xét cho đánh
giá down là tùy chọn, tối đa 1.000 ký tự; đánh giá up không có nhận xét.
`DELETE` cùng đường dẫn để bỏ đánh giá. Dùng `turn_id` đã lưu, đọc lịch sử
nếu stream không có frame `turn`.

## Lỗi và giới hạn

Xử lý theo `error.code`, không theo nội dung thông điệp.
`CHAT_SESSION_NOT_FOUND` còn che phiên của người khác. Lỗi token và chính
sách origin nằm trong [hướng dẫn xác thực](chat-third-party-auth.md); toàn
bộ mã nằm ở [Mã lỗi](../reference/errors.md).

`429 RATE_LIMITED` có HTTP `Retry-After` tính bằng giây (lỗi socket có
`error.details.retry_after`). Backoff trước khi mở socket khác hoặc thử
ghi lại. Giới hạn đọc/gửi theo IP, gửi theo khách hoặc user bên ngoài, và
quota mỗi ngày UTC của chat cùng áp dụng. Operator cấu hình
`STUDIO_PUBLIC_CHAT_RATE_*`; xem [Cấu hình](../reference/configuration.md).
