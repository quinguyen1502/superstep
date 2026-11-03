# Xác thực chat cho ứng dụng bên thứ ba

Cho người đã đăng nhập ứng dụng của bạn chat bằng danh tính riêng. Backend
của bạn ký user JWT ngắn hạn bằng app key của từng chat; trình duyệt hoặc
app di động chỉ nhận JWT đó. Superstep kiểm tra token tại chỗ. Không cần
endpoint đổi token.

## Thiết lập app key

1. Lưu workflow và bật **Chat** trong cài đặt. Bật tùy chọn cho user ứng
   dụng bên thứ ba (`app`) và chọn slug công khai. Có thể đồng thời cho
   phép khách `anonymous` hoặc tài khoản studio `signed_in`.
2. Với quyền chủ workflow hoặc admin, tạo app key trong cài đặt Chat.
   Đặt nhãn và, với app web, chỉ định origin như `https://shop.example.com`
   (giao thức, host và cổng tùy chọn; không có path).
3. Sao chép `key_id` và `secret` hiện một lần vào kho bí mật của backend.
   Danh sách key chỉ có metadata, không trả lại secret. Mất secret thì tạo key khác.
4. Backend xác thực người dùng bằng hệ thống đăng nhập của bạn, lấy id ổn
   định rồi ký token cho người đó. Endpoint riêng chỉ trả user JWT, được
   bảo vệ bằng session ứng dụng, với `Cache-Control: no-store`.
5. Gửi JWT qua [Chat API](chat-api.md). HTTP trên trình duyệt dùng
   `credentials:'omit'`; socket gửi frame `auth` trước tin nhắn.

Endpoint quản lý của chủ workflow/admin tách khỏi Chat API công khai:

```text
GET    /api/workflows/{wid}/chat/app-keys
POST   /api/workflows/{wid}/chat/app-keys
DELETE /api/workflows/{wid}/chat/app-keys/{key_id}
```

Body tạo key: `{"label":"Shop backend","origins":["https://shop.example.com"]}`.
`data.secret` của kết quả tạo chỉ hiện một lần. Thu hồi trên UI yêu cầu gõ
tên đang hiển thị của mục đó; API DELETE không có trường confirm. Tạo và
thu hồi đều được ghi audit.

## Hợp đồng token

Header là `{"alg":"HS256","typ":"JWT","kid":"<key_id>"}`. Chữ ký là
HMAC-SHA256 trên `base64url(header).base64url(claims)`, dùng **byte UTF-8 của
secret đúng như được hiển thị**. Không giải mã base64 secret. Mọi phần JWT
dùng base64url không có padding `=`.

| Claim | Giá trị |
| --- | --- |
| `iss` | `key_id` của app, giống header `kid` |
| `aud` | Chính xác `superstep-chat:<slug>` |
| `sub` | Id user bên ngoài ổn định, 1–128 ký tự, luôn là chuỗi |
| `name` | Tên hiển thị tùy chọn, tối đa 80 ký tự |
| `iat` | Giây Unix lúc phát hành, kiểu số |
| `exp` | Giây Unix hết hạn; sau `iat` và không quá 3.600 giây sau đó |
| `nbf` | Giây Unix bắt đầu hiệu lực, tùy chọn |
| `jti` | Id tùy chọn; phiên bản này chưa có danh sách chặn từng token |
| `meta` | Object JSON tùy chọn, tối đa 1.024 byte khi mã hóa UTF-8 gọn; input không tin cậy cho workflow |

Ví dụ phát hành token 10 phút. Đồng bộ đồng hồ: kiểm tra cho phép lệch 60
giây với `iat`, `exp`, `nbf`. Chỉ HS256 được chấp nhận; từ chối `none`, thuật
toán khác, key lạ, sai audience và sai chữ ký. Toàn token tối đa 8.192 ký
tự. Metadata phải vừa giới hạn riêng lẫn giới hạn token đó.

## Ký trên server của bạn

Các ví dụ dùng thư viện chuẩn là helper độc lập. Source SDK còn có
`mintChatToken` từ `@superstep/sdk/server` và Python `mint_chat_token`; dùng phiên
bản package tương thích đã duyệt hoặc checkout đã build. Gọi helper trên server
với key/secret từ kho bí mật và `sub`/tên từ user ứng dụng **đã xác thực**. Không ký danh tính theo id tùy ý do trình
duyệt gửi lên. Mỗi helper trả token; HTTP handler riêng trả token đó cho
đúng user. Không ghi secret và token trả về vào log.

=== "Node.js (18+)"

    ```javascript
    --8<-- "handbook/snippets/chat/mint-token.mjs"
    ```

=== "Python (3.9+)"

    ```python
    --8<-- "handbook/snippets/chat/mint-token.py"
    ```

=== "Go (1.18+)"

    ```go
    --8<-- "handbook/snippets/chat/mint-token.go"
    ```

=== "PHP"

    ```php
    --8<-- "handbook/snippets/chat/mint-token.php"
    ```

Ví dụ đối số helper Node:
`{keyId, secret, slug:'support', userId:currentUser.id, name:currentUser.name}`.
Giữ id ổn định giữa các thiết bị và khi đổi tên. Mọi key của cùng chat dùng
chung không gian id user: cùng `sub` có cùng lịch sử qua cả hai key luân
chuyển. Thêm tiền tố tenant vào `sub` nếu ứng dụng cần tách các khách hàng
có id trùng nhau.

## Giao thức, origin và làm mới token

HTTP gửi `Authorization: Bearer <jwt>`. Với WebSocket v1, chờ `ready`, gửi
`{"type":"auth","token":"<jwt>"}` rồi một `message` hoặc `answer`.
`?token=` là dự phòng tương thích; ưu tiên frame vì URL có thể vào log proxy.
Không đưa **secret** app vào URL hay client.

Với HTTP từ trình duyệt khác origin, preflight phải yêu cầu Authorization;
request thực tế được kiểm tra chữ ký token và origin theo key. CORS không
cho phép credentials. Socket khác origin cũng cần app token hợp lệ và
Origin được phép; socket cũ vẫn chỉ cùng origin.

Danh sách origins trống cho phép mọi origin, kể cả client native/server
không gửi Origin. Danh sách không trống bắt buộc Origin khớp và từ chối
request không có Origin. Key chỉ dùng web nên đặt origin cụ thể. Danh sách
này kiểm soát người gọi API/socket trực tiếp; cài đặt `embed_origins` riêng
của chat kiểm soát site được nhúng `/c/{slug}` trong iframe.

Lấy JWT mới trước khi hết hạn hoặc khi nhận `CHAT_TOKEN_EXPIRED`, qua
endpoint riêng đã xác thực của bạn. Thử xác thực lại một lần với token mới;
tránh lặp vô hạn. Socket kiểm tra token trước thao tác và không cắt stream
đang chạy khi token hết hạn. Kết nối hoặc request HTTP mới kiểm tra lại.
Sau stream bị ngắt, đọc lại lịch sử trước khi gửi lại tin nhắn.

[API widget](chat-widget.md) hỗ trợ `identify` qua bridge kiểm tra trang cha/frame.
Origin trong app key là origin của iframe Studio; `embed_origins` cho phép website
cha riêng. Client [bộ giao diện React](chat-react.md) và SDK headless trực tiếp
dùng origin của ứng dụng.

## Danh tính và lịch sử trong workflow

Khai báo trường state tên `chat` kiểu **object** trong workflow để giữ input
được chèn vào. Tin nhắn mới từ user app cung cấp:

```json
{"chat":{"user":{"id":"cust_42","name":"Lan","kind":"app"},"meta":{"plan":"standard"}}}
```

Ví dụ `{{state.chat.user.name}}` đọc tên hiển thị. Tên và metadata là dữ
liệu không tin cậy: không biến chúng thành system instruction hay quyết
định phân quyền. Run vẫn dùng credential của chủ workflow. Câu trả lời
Human tiếp tục run cũ; không tạo input tin nhắn mới.

Lịch sử, tệp và đánh giá được giới hạn theo `(chat, id user bên ngoài)`,
không theo thiết bị hay id key đang dùng. User app khác, khách ẩn danh và
user studio không đọc được lịch sử đó qua endpoint phiên công khai. App
token hợp lệ ưu tiên hơn cookie ẩn danh; nó không chuyển hay gộp lịch sử
ẩn danh. Đổi `sub` là đổi phạm vi lịch sử user.

## Luân chuyển và thu hồi

Tối đa **hai key hoạt động cho mỗi chat** để luân chuyển không gián đoạn:

1. Tạo key thứ hai với origins mong muốn; lưu secret an toàn.
2. Triển khai bên phát hành token để ký bằng `kid` và secret mới.
3. Cho client làm mới token; cả hai key hoạt động đọc cùng lịch sử user.
4. Thu hồi key cũ trong cài đặt Chat. Thu hồi ngay khi nghi lộ secret.

Key được đọc mỗi lần xác thực, không cache; thu hồi từ chối ngay lần xác
thực tiếp theo. Stream đã xác thực không được kiểm tra lại giữa run. Tắt
Chat hoặc bỏ quyền `app` để từ chối mọi thao tác user app. Không có endpoint
thu hồi từng token; dùng thời hạn ngắn hoặc thu hồi key khi cần.

## Lỗi và giới hạn

| HTTP | Mã | Cách xử lý |
| --- | --- | --- |
| 401 | `CHAT_TOKEN_REQUIRED` | Gửi app token cho chế độ/origin yêu cầu |
| 401 | `CHAT_TOKEN_INVALID` | Kiểm tra cấu hình ký, audience, danh tính, đồng hồ; không thử lại mù quáng |
| 401 | `CHAT_TOKEN_EXPIRED` | Làm mới qua backend đã xác thực của bạn |
| 401 | `CHAT_APP_KEY_REVOKED` | Chuyển sang key hoạt động; điều tra nếu thu hồi bất ngờ |
| 403 | `CHAT_ORIGIN_FORBIDDEN` | Sửa origins được phép hoặc origin phía gọi |
| 404 | `CHAT_NOT_PUBLISHED` | Chat tắt, chưa công khai hoặc không khả dụng |
| 404 | `CHAT_SESSION_NOT_FOUND` | Phiên không tồn tại hoặc thuộc danh tính khác |
| 429 | `RATE_LIMITED` | Backoff theo `Retry-After` hoặc socket `error.details.retry_after` |

Trình duyệt khác origin chỉ đọc được lỗi hết hạn/thu hồi sau khi chữ ký và
origin hợp lệ. Credential/origin bị từ chối khác có thể hiện như lỗi mạng
CORS; kiểm tra status/code ở server mà không ghi JWT vào log.

Giới hạn đọc/gửi theo IP và quota ngày của chat vẫn áp dụng. Giới hạn gửi
theo user bên ngoài là `STUDIO_PUBLIC_CHAT_RATE_USER`, mặc định bằng giới
hạn gửi theo IP (mặc định 30 mỗi 60 giây). Upload tiêu thụ quota này; xác
thực token thất bại tính vào giới hạn gửi theo IP. Xem
[Cấu hình](../reference/configuration.md) và [Mã lỗi](../reference/errors.md).

## Checklist bảo mật

- Giữ secret app trong kho bí mật backend; không đưa secret, PAT hay
  workflow token vào bundle trình duyệt/di động, ảnh chụp, URL hoặc log.
- Bảo vệ endpoint ký bằng xác thực và kiểm soát CSRF của ứng dụng; xác
  định danh tính ở server và trả `Cache-Control: no-store`.
- Dùng HTTPS/WSS, thời hạn ngắn và origin web cụ thể. Khi phù hợp, chỉ giữ
  JWT trong bộ nhớ; xóa khi đăng xuất và tránh cache dùng chung.
- Luân chuyển key, audit việc dùng bất thường và thu hồi secret bị lộ ngay.
  Key bị lộ có thể giả mạo mọi user của chat đó cho tới khi bị thu hồi.
- Xem `name`/`meta` là dữ liệu không tin cậy và đặt giới hạn chi tiêu chat.
- Dùng id ổn định có phạm vi tenant; đổi key không tự tách lịch sử.


Tiếp tục với [bộ giao diện React](chat-react.md) hoặc [API widget](chat-widget.md). Hướng dẫn widget giải thích origin của iframe Studio trong app key, tách biệt với danh sách website cha được nhúng.
