# Mở studio cục bộ ra internet

Slack, Telegram và WhatsApp gọi lại studio qua internet, và Telegram chỉ nhận
HTTPS. Studio chạy trên máy bạn cần một địa chỉ HTTPS công khai cho việc đó:
một tunnel. Studio biết địa chỉ này qua đúng một biến, `STUDIO_PUBLIC_URL`.

!!! warning "Tunnel công khai toàn bộ studio"
    Ai có địa chỉ đều tới được trang đăng nhập và API, không chỉ các đường dẫn
    callback. Đừng mở tunnel cho studio còn tài khoản demo
    (`admin@example.com` / `admin123`) hoặc `JWT_SECRET` mặc định. Dùng tài
    khoản và secret thật (xem [Tài khoản và bảo mật](accounts.md)), giới hạn
    truy cập tunnel khi nhà cung cấp cho phép, và tắt tunnel khi xong. Không bao
    giờ tắt kiểm tra chữ ký callback để callback chạy được.

## Chọn cổng cục bộ

Tunnel phải trỏ tới tiến trình trả lời `/api`.

| Cách chạy studio | Địa chỉ cục bộ cần tunnel |
| --- | --- |
| Phát triển (API `uvicorn`) | `http://localhost:8000` |
| Docker Compose (cổng nginx) | `http://localhost:8080` (hoặc `WEB_PORT` của bạn) |
| Image đơn | `http://localhost:8000` (hoặc `PORT` của bạn) |

API phát triển chỉ phục vụ `/api`. Trang mở từ link công khai (trang quay lại
của **Add to Slack**, link trong email và Teams) cần cổng Compose hoặc image,
nơi phục vụ cả ứng dụng web. Ví dụ bên dưới dùng 8000.

## Địa chỉ tạm thời hay cố định

Quick tunnel nhận địa chỉ ngẫu nhiên mới mỗi lần khởi động. Sau mỗi lần khởi
động lại, bạn phải cập nhật lại `STUDIO_PUBLIC_URL` và cài đặt của nhà cung
cấp. Dùng địa chỉ cố định (named tunnel của Cloudflare, dev domain hoặc domain
đặt trước của ngrok, dev tunnel bền vững) cho mọi thứ dùng quá một phiên.

## Cloudflare Tunnel

Quick tunnel, không cần tài khoản, địa chỉ `trycloudflare.com` tạm thời
([tài liệu Cloudflare](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)):

```bash
cloudflared tunnel --url http://localhost:8000
```

Ai có URL đều vào được studio, và tunnel dừng khi `cloudflared` dừng. Quick
tunnel không hỗ trợ Server-Sent Events, nên cập nhật run trực tiếp trong trình
duyệt mở qua tunnel có thể không chạy; callback là request thường nên vẫn chạy.

Để có hostname cố định trên domain trong tài khoản Cloudflare, tạo named tunnel
quản lý cục bộ
([tài liệu Cloudflare](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/)):

```bash
cloudflared tunnel login
cloudflared tunnel create studio
```

Viết `~/.cloudflared/config.yml` với UUID và file credentials mà `create` in ra:

```yaml
url: http://localhost:8000
tunnel: <Tunnel-UUID>
credentials-file: /home/you/.cloudflared/<Tunnel-UUID>.json
```

Rồi gán hostname và chạy:

```bash
cloudflared tunnel route dns studio studio.example.com
cloudflared tunnel run studio
```

Cloudflare Access có thể đặt bước đăng nhập trước hostname; để các đường dẫn
callback dưới `/api/approvals/callback/` truy cập được cho nhà cung cấp.

## ngrok

Cài agent, thêm authtoken một lần, rồi mở endpoint
([tài liệu ngrok](https://ngrok.com/docs/getting-started/)):

```bash
ngrok config add-authtoken <your-token>
ngrok http 8000
```

Mỗi tài khoản có một dev domain mà `ngrok http` dùng lại qua các lần khởi động.
Để dùng một domain đặt trước hoặc domain riêng:

```bash
ngrok http 8000 --url https://studio.example.ngrok.app
```

## Microsoft Dev Tunnels

Đăng nhập bằng tài khoản Microsoft, Microsoft Entra ID hoặc GitHub
([tài liệu Dev Tunnels](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started)).
Tunnel mặc định là riêng tư; nhà cung cấp không đăng nhập được, nên callback
cần quyền truy cập ẩn danh.

Tunnel tạm thời, bị xoá khi lệnh dừng:

```bash
devtunnel user login
devtunnel host -p 8000 --allow-anonymous
```

Tunnel bền vững giữ nguyên địa chỉ:

```bash
devtunnel create --allow-anonymous
devtunnel port create -p 8000
devtunnel host
```

Dùng địa chỉ `https://…devtunnels.ms` được in ra cho cổng đó.

## Đặt địa chỉ và khởi động lại

1. Sao chép origin HTTPS mà tunnel in ra, không có đường dẫn hay dấu `/` cuối,
   ví dụ `https://studio.example.com`.
2. Đặt nó ở nơi API đọc biến môi trường (shell, `.env` hoặc file Compose):

    ```bash
    STUDIO_PUBLIC_URL=https://studio.example.com
    ```

3. Khởi động lại API và worker. Trong **Cài đặt → Kênh**, ghi chú
   "Chưa đặt STUDIO_PUBLIC_URL" biến mất.

## Cập nhật callback của nhà cung cấp

Địa chỉ là một phần của mọi callback, nên cập nhật nhà cung cấp mỗi khi nó đổi
(xem [Kênh duyệt](channels.md)):

| Nhà cung cấp | Ở đâu | URL |
| --- | --- | --- |
| Slack | Request URL trong **Interactivity & Shortcuts** | `{STUDIO_PUBLIC_URL}/api/approvals/callback/slack` |
| Slack (Add to Slack) | OAuth redirect URL | `{STUDIO_PUBLIC_URL}/api/approvals/slack/oauth/callback` |
| Telegram | Bấm lại **Đăng ký webhook** trên kết nối | `{STUDIO_PUBLIC_URL}/api/approvals/callback/telegram/{channel_id}` |
| WhatsApp | Callback URL webhook của Meta app | `{STUDIO_PUBLIC_URL}/api/approvals/callback/whatsapp/{channel_id}` |

[Chạy từ chat](../run/chat-triggers.md) dùng cùng events URL của Slack và
webhook Telegram, nên đăng ký lại cả chúng.

## Kiểm tra

- `curl https://studio.example.com/api/health` từ mạng khác trả về OK.
- **Kiểm tra kết nối** trên kết nối ở **Cài đặt → Kênh** gửi được tin nhắn.
- Bước kiểm tra request URL của Slack thành công; `getWebhookInfo` của Telegram
  hiện URL mới và không có lỗi gần đây; xác minh webhook của Meta thành công.
- Duyệt một yêu cầu thử và xác nhận run tiếp tục.
