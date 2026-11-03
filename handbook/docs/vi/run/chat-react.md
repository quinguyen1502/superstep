# Bộ giao diện React chat

Dùng `@superstep/react` để hiển thị chat của workflow đã xuất bản trong ứng dụng
React của bạn. Gói này dùng chung thành phần chat với Studio và dùng
`@superstep/sdk/chat` cho HTTP, nội dung truyền dần, file và đánh giá. Backend của
bạn xác thực người dùng bằng token ngắn hạn; họ không cần tài khoản Studio.
Nếu muốn thêm bong bóng vào website, xem [Widget chat](chat-widget.md).

## Chuẩn bị chat và package

1. Xuất bản trang Chat của workflow và bật **Người dùng ứng dụng bên thứ ba** (`app`).
2. Tạo app key. Cho phép origin chính xác của ứng dụng, ví dụ
   `https://shop.example.com`. Giữ secret trên backend.
3. Tạo endpoint cấp token có xác thực, lấy ID người dùng từ phiên đăng nhập trên
   server và trả JWT ngắn hạn. Xem [Xác thực chat bên thứ ba](chat-third-party-auth.md).
4. Dùng các phiên bản đã được duyệt, tương thích của `@superstep/react` và
   `@superstep/sdk`, với peer dependency React/React DOM từ 18, i18next và react-i18next.

Phát hành package là bước riêng. Repo chuẩn bị TypeScript SDK 0.2.0 và bộ giao diện
React 0.1.0; hướng dẫn này không đồng nghĩa với một bản phát hành npm mới.
Để thử checkout trước khi có bản phát hành package được duyệt:

```sh
npm ci
npm run build
scripts/chat_host_e2e.sh
```

Server mẫu chạy cục bộ cung cấp trang SDK headless ở `/`, React ở `/react/` và
widget ở `/widget.html`. Script kiểm thử dừng server khi hoàn tất. README của
các ví dụ hướng dẫn chạy với Studio phát triển của bạn; thay phần đăng nhập mẫu
Lan/Minh bằng xác thực của ứng dụng trước khi triển khai.

## Hiển thị chat đầy đủ

Import stylesheet đã build một lần. Ứng dụng chủ không cần cấu hình Tailwind.
Đặt chiều cao cho vùng chat:

```tsx
import { Chat } from '@superstep/react'
import '@superstep/react/styles.css'

async function getToken() {
  const response = await fetch('/api/auth/chat-token', {
    method: 'POST', credentials: 'same-origin',
  })
  const body = await response.json()
  if (!response.ok || !body.success) throw new Error('Token request failed')
  return body.data.token
}

export function Support({ user }: { user: { id: string } }) {
  return <Chat
    slug="support"
    baseUrl="https://studio.example.com"
    identityKey={user.id}
    getToken={getToken}
    locale="vi"
    theme={{ colorScheme: 'system', radius: 12 }}
    style={{ height: 640 }}
  />
}
```

Endpoint mẫu dùng envelope `{success, data, error}`. Điều chỉnh biểu thức trả về
nếu endpoint của bạn có cấu trúc khác. Không trả app secret, PAT hay workflow token
cho callback này. Request dùng cookie của ứng dụng chủ; SDK chỉ gửi Bearer token
nhận được tới Studio và không gửi cookie trong HTTP request.

`Chat` có lịch sử/tạo cuộc trò chuyện, nội dung trả lời truyền dần, câu trả lời
Human, tải file lên/xuống, đánh giá và thông báo lỗi. Câu hỏi dành cho người duyệt
chỉ cho đọc. Lịch sử Human được khôi phục có prompt đã lưu và điều khiển nhập văn
bản/duyệt/từ chối; trường có cấu trúc và lựa chọn hiển thị khi có trong câu hỏi
được truyền từ server.

## Danh tính, lịch sử và lỗi

- Đổi `identityKey` khi đổi người dùng, hoặc mount lại chat. Chỉ đổi `getToken`
  sẽ làm mới token và giữ cuộc trò chuyện hiện tại.
- `getToken` có thể trả chuỗi hoặc promise. SDK gọi callback cho các thao tác
  và thử lại token hết hạn một lần. SDK không gửi lại thao tác ghi chưa rõ kết quả;
  kết nối lại chỉ khôi phục lịch sử đã lưu.
- `sessionId` không truyền sẽ khôi phục chat mới nhất; `null` bắt đầu trống;
  chuỗi sẽ tải chat đó. Đổi prop sẽ đặt lại tài nguyên và bản nháp.
- Khi đăng xuất ứng dụng chủ, unmount chat của người dùng bên thứ ba. Nếu bật
  truy cập ẩn danh, tạo instance riêng với `visitorToken` và `onVisitorToken`.
  Có thể lưu HMAC ẩn danh đó trên ứng dụng chủ. Không kết hợp với `getToken`.
- Phương thức bất đồng bộ của controller có thể reject và đặt `chat.error`;
  xử lý promise khi dùng bố cục riêng. Lỗi SDK có mã như `CHAT_TOKEN_EXPIRED`,
  `CHAT_APP_KEY_REVOKED`, `CHAT_ORIGIN_FORBIDDEN`. Request khác origin bị từ chối
  có thể hiện thành lỗi mạng. Xem [lỗi xác thực](chat-third-party-auth.md#loi-va-gioi-han).
- Đổi danh tính sẽ huỷ thao tác cũ và xoá tin nhắn/bản nháp/hộp thoại cũ.
  Unmount giải phóng đăng ký và huỷ thao tác đang chờ; StrictMode chạy lại effect
  vẫn giữ tài nguyên đang dùng.

## Tự ghép bố cục

```tsx
import {
  useChat, ChatProvider, MessageList, QuestionCard, Composer,
} from '@superstep/react'

function CustomSupport({ user }: { user: { id: string } }) {
  const chat = useChat({
    slug: 'support', baseUrl: 'https://studio.example.com',
    identityKey: user.id, getToken, locale: 'vi',
  })
  return <ChatProvider chat={chat} locale="vi"
    theme={{ colorScheme: 'dark' }} style={{ height: 640 }}>
    <MessageList />
    <QuestionCard />
    <Composer />
  </ChatProvider>
}
```

`useChat` cung cấp `page`, `sessions`, `turns`, `text`, `question`, `sessionId`,
`loading`, `busy`, `status`, `error`, `waiting`, `answeredBy`. Các thao tác gồm
`refresh`, `load`, `start`, `send`, `answer`, `cancel`, `upload`, `removeFile`,
`download`, `rate`. `Rating` nhận một turn từ `chat.turns`. Hộp thoại xác nhận dùng
chung yêu cầu nhập đúng tên file/đánh giá trước khi xoá; API DELETE giữ nguyên.

`MessageList` nhận React node `empty`; `Composer` nhận `idPrefix`.
`ChatProvider` có thể bọc các thành phần trình bày dùng chung mà không có
controller, nhưng thành phần dùng controller vẫn cần `chat`. `embed: true` trên
`useChat` đánh dấu các session mới là chat nhúng. Tích hợp React trực tiếp thường
không đặt tuỳ chọn này; iframe của widget tự đặt.

## Giao diện và ngôn ngữ

`locale` nhận `en` hoặc `vi`. Mỗi provider có bản dịch riêng; đổi ngôn ngữ không
ảnh hưởng ứng dụng chủ hay chat khác. Ghi đè khoá dạng dấu chấm bằng
`messages={{ 'chat.placeholder': 'Hỏi đội hỗ trợ' }}`.

`theme` nhận `primary`, `primaryForeground`, `radius`, `font`, `colorScheme`
(`light`, `dark`, `system`). CSS variable ở root gồm `--ss-background`,
`--ss-foreground`, `--ss-primary`, `--ss-primary-foreground`, `--ss-border`,
`--ss-radius`, `--ss-font`. Provider React có thể dùng biến của ứng dụng chủ như
`var(--brand)`. Stylesheet sinh ra được giới hạn trong `.superstep-chat`, gồm
preflight, utility, Markdown, biến và keyframe. Hộp thoại/select/tooltip mở trong
root của provider. Style từ ứng dụng chủ vẫn có thể kế thừa vào chat; không có
ranh giới Shadow DOM.

## Chạy ví dụ

`examples/react-chat` dùng package đã build mà không cần alias tới source Studio
hay plugin Tailwind. Ví dụ có cả `<Chat>` và bố cục tự ghép với ngôn ngữ/giao diện
riêng. Node host dùng chung giữ secret ký token trên server và dùng phiên
đăng nhập không để lộ dữ liệu trong cookie HttpOnly.

```sh
PW_CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  scripts/chat_host_e2e.sh
```

Bỏ `PW_CHROME` khi đã cài Chromium của Playwright. CI chạy kiểm thử chung cho
React/widget/headless với React 18 và 19: truyền dần nội dung, trả lời Human,
file, đánh giá, cách ly danh tính/lịch sử, đăng xuất, từ chối origin và thu hồi
key. Ảnh chỉ là artifact CI tạm thời, không thêm vào Git.
