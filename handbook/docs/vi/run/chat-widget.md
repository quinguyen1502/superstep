# Widget chat

Thêm bong bóng vào website bằng `widget.js`. Script mở chat đã xuất bản trong
iframe của Studio; không đưa React vào trang chủ. Để ứng dụng React hiển thị
chat trực tiếp, xem [Bộ giao diện React chat](chat-react.md).

## Xuất bản và cho phép website

Xuất bản trang Chat, bật truy cập ẩn danh và/hoặc người dùng bên thứ ba (`app`),
rồi thêm origin chính xác của website vào **Các site được nhúng chat này**.
Ví dụ, cho phép `https://shop.example.com`; origin HTTP localhost cũng dùng được
khi phát triển. Origin khác không thể nhúng trang.

```html
<script src="https://studio.example.com/c/widget.js"
  data-slug="support" data-language="vi" data-position="right" async></script>
```

Snippet `data-slug` cũ vẫn hoạt động. Bong bóng lưu HMAC của khách ẩn danh trên
website của bạn, dưới khoá `superstep-chat:<slug>`. Script khác trên website đó
có thể dùng danh tính này, nên chỉ nhúng trên website bạn tin cậy. Khi storage
bị chặn, danh tính chỉ tồn tại trong trang hiện tại. Iframe thuần dùng storage
riêng được trình duyệt phân vùng và có thể bị trình duyệt xoá.

## Xếp lệnh trước khi script tải xong

```html
<script>
  window.Superstep = { q: [
    ['init', { slug: 'support', open: true, language: 'vi', position: 'right' }],
    ['on', 'ready', function (event) { console.log(event.slug) }]
  ] }
</script>
<script src="https://studio.example.com/c/widget.js" async></script>
```

Có thể dùng mảng tuple: `window.Superstep = [['init', { slug: 'support' }]]`.
Hàng đợi chạy một lần theo thứ tự; đăng ký handler trước sự kiện cần nhận.
Dùng tối đa 100 lệnh trong hàng đợi, rồi gọi API đã tải. Tải script lần nữa sẽ
dùng lại API hiện có. Data attribute được áp dụng trước lệnh trong hàng đợi.
Với hàng đợi inline, áp dụng nonce/hash theo CSP của website.

## Đăng nhập người dùng của bạn

Backend ký JWT ngắn hạn từ phiên đăng nhập đã xác thực. App secret ở trên
server. Xem [Xác thực bên thứ ba](chat-third-party-auth.md) để biết claim,
helper ký token, cách xoay key và mã lỗi.

Có hai cấu hình origin riêng:

| Cấu hình | Ví dụ cho widget này | Mục đích |
| --- | --- | --- |
| Chat `embed_origins` | `https://shop.example.com` | Cho phép website cha nhúng chat và dùng bridge được kiểm tra |
| Origin được phép của app key | `https://studio.example.com` | Cho phép HTTP/socket phát ra trong iframe của Studio |

Key chỉ cho phép website cha sẽ từ chối request từ iframe. Client React/headless
trực tiếp dùng origin của ứng dụng. Danh sách origin của key rỗng giữ chính sách
không giới hạn/native. GET cùng origin không có `Origin` cần Fetch Metadata cùng
origin và referrer thuộc origin của API; cấu hình đúng `STUDIO_PUBLIC_URL` khi
qua proxy và giữ lại metadata này.

Sau khi API đã tải và ứng dụng chủ đăng nhập thành công:

```js
await window.Superstep.identify(async function () {
  const response = await fetch('/api/auth/chat-token', {
    method: 'POST', credentials: 'same-origin',
  })
  const body = await response.json()
  if (!response.ok || !body.success) throw new Error('Token request failed')
  return body.data.token
})

// Khi đăng xuất ứng dụng chủ, xoá cả danh tính app trong widget:
await window.Superstep.logout()
```

Endpoint mẫu dùng envelope; điều chỉnh biểu thức trả về nếu endpoint của bạn có
cấu trúc khác. Endpoint phải xác thực và bảo vệ request cấp token, lấy danh tính
trên server, trả `Cache-Control: no-store`. Không đưa secret, PAT hay workflow
token vào HTML, biến Vite, storage trình duyệt hoặc endpoint cấp token công khai.

`identify` nhận JWT dạng chuỗi hoặc hàm trả JWT/promise. Nên dùng provider để SDK
lấy token mới và thử lại một lần khi token hết hạn. Gọi lại `identify` khi đổi
người dùng. Promise hoàn tất khi tải xong lịch sử của người đó, hoặc reject với
`code` an toàn khi lỗi. `logout` huỷ danh tính trước và khôi phục lịch sử ẩn danh
của website khi bật truy cập ẩn danh. Provider đang chờ không thể đưa tin nhắn của
người cũ trở lại sau khi đăng xuất/đổi người dùng. Provider/bridge hết thời gian
chờ sau 10 giây với `HTTP_ERROR`; ứng dụng cần xử lý promise danh tính.
JWT và callback chỉ ở bộ nhớ, không vào URL, storage hay metadata sự kiện công
khai. Bridge nội bộ kiểm tra origin, đúng cửa sổ, channel tài liệu và epoch danh
tính; không tự gửi token qua bridge postMessage dùng wildcard.

## API và giao diện

| API | Kết quả |
| --- | --- |
| `init(options)` | Tạo/cập nhật widget; đổi slug/baseUrl sẽ xoá danh tính app |
| `open()`, `close()`, `toggle()` | Điều khiển khung chat; bong bóng vẫn hiện |
| `identify(tokenOrGetToken)` | Đổi sang người dùng app và chờ tải lịch sử |
| `logout()` | Xoá danh tính app và chờ lịch sử ẩn danh |
| `on(event, handler)` | Đăng ký; trả hàm huỷ đăng ký |
| `off(event, handler)` | Huỷ đăng ký đó |

`init` yêu cầu `slug`. `baseUrl` mặc định là origin HTTP(S) của script.
Các tuỳ chọn và data attribute:

| Tuỳ chọn | Attribute | Giá trị |
| --- | --- | --- |
| `open` | `data-open` | `true` để mở sẵn |
| `language` | `data-language` (alias `data-lang`) | `en`, `vi`; mặc định theo trình duyệt |
| `position` | `data-position` | `left`, `right` |
| `color` | `data-color` | Màu CSS dùng được cả trong iframe và trên trang chủ |
| `logo` | `data-logo` | URL ảnh HTTP(S) hoặc data URL base64 PNG/JPEG/WebP, tối đa 350.000 ký tự |

Đổi giao diện vẫn giữ chat hiện tại. Chuỗi màu/logo rỗng khôi phục mặc định;
giá trị giao diện không hợp lệ bị bỏ qua. Khác provider React, biến CSS của trang
chủ không đi qua iframe: cần truyền màu cụ thể. Iframe theo chế độ sáng/tối của
trình duyệt. CSP của trang chủ cần cho phép ảnh/script/frame/style liên quan;
bong bóng dùng style inline được giới hạn phạm vi.

## Sự kiện

| Sự kiện | Payload và thời điểm |
| --- | --- |
| `ready` | `{ slug }` sau khi khởi tạo lịch sử và đổi danh tính thành công |
| `open`, `close` | `{ slug }` khi đổi trạng thái hiện; `init({open:true})` ban đầu không phát sự kiện |
| `message`, `answer` | `{ slug, sessionId, turn: { id, role, text, status? } }` cho turn người dùng/trợ lý mới được lưu sau khi gửi hoặc trả lời Human |
| `error` | `{ slug, code }` khi lỗi khởi tạo danh tính hoặc kết nối |

Khôi phục lịch sử không phát lại sự kiện turn mới. Payload không có frame xác
thực, metadata người dùng hay credential file. Subscriber ném lỗi không làm
hỏng handler khác. Ví dụ:

```js
const unsubscribe = window.Superstep.on('answer', function (event) {
  console.log(event.sessionId, event.turn.id)
})
// Khi không dùng nữa:
unsubscribe()
```

## Thử sample host

Chạy `scripts/chat_host_e2e.sh` từ root của repo. Server mẫu cục bộ cung cấp `/`
(SDK headless), `/react/` và `/widget.html`. Trang widget dùng lại điều khiển của
portal mẫu và phiên đăng nhập không để lộ dữ liệu; bong bóng/iframe do
`widget.js` của Studio đã build cung cấp. Thay đăng nhập mẫu trước khi triển
khai ứng dụng của bạn. Phát hành package cần được duyệt riêng.

E2e kiểm tra chat ẩn danh, token do server cấp, hai người dùng/lịch sử, câu trả lời
Human, sự kiện nội dung truyền dần và đăng xuất về danh tính khách ban đầu.
Trường hợp thu hồi key của ví dụ headless chạy cuối trên fixture mới. Bộ kiểm
thử còn kiểm tra từ chối origin, file và đánh giá. Ảnh en/vi/sáng/tối chỉ là
artifact CI tạm thời. Trang `/c/<slug>?embed=1` có API trong frame để wrapper
native dùng sau; hướng dẫn theo nền tảng là phần việc riêng.


## Sửa tin nhắn đã gửi

Các thao tác tin nhắn dùng chung [luồng sửa tin nhắn](chat.md): xác nhận chạy mới trong một nhánh độc lập, giữ nguyên bản gốc và dùng liên kết nguồn để quay lại. Câu trả lời Human không phải tin nhắn gốc được sửa. Với giao diện tự dựng, `useChat().edit(turnId, text, operationId)` cần cùng bước xác nhận chạy lại; giữ mã thao tác khi phục hồi lần chạy bị gián đoạn. Xem [hợp đồng API](chat-api.md) về tiếp nhận thao tác và phục hồi kết quả.


Tạo lại dùng chung luồng xác nhận tạo nhánh: **Tạo lại câu trả lời** trên câu trả lời cuối đã kết thúc mở nhánh độc lập và hỏi lại Human/người duyệt. `useChat().regenerate(answerId, operationId?)` trả kết quả chat thông thường. Xem [cách dùng chat](chat.md#tao-lai-cau-tra-loi-cuoi) và [tiếp nhận/phục hồi API](chat-api.md#chuan-bi-tao-lai-cau-tra-loi).
