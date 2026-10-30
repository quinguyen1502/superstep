# Biến môi trường khi triển khai lên PaaS

[English](env-vars.md) · [Hướng dẫn triển khai](README.vi.md)

Các biến quan trọng với image all-in-one. Danh sách đầy đủ (kênh duyệt, SMTP, MCP, tracing) nằm trong
[`.env.example`](../../.env.example).

## Bắt buộc

| Biến | Mặc định trong image | Mục đích |
|---|---|---|
| `JWT_SECRET` | không có | Ký token phiên đăng nhập. Production không khởi động nếu thiếu. |
| `STUDIO_SECRET_KEY` | không có | Mã hoá các credential đã lưu. Production không khởi động nếu thiếu, trừ khi `/data/secret.key` đã có từ lần khởi động trước. Khoá Fernet được dùng nguyên vẹn; giá trị khác (ví dụ khoá do nền tảng sinh) được chuyển thành khoá Fernet bằng SHA-256. Không bao giờ đổi sau lần khởi động đầu. |
| `STUDIO_ADMIN_EMAILS` | rỗng | Danh sách email admin, cách nhau bằng dấu phẩy. Khi chưa có admin nào, email đầu tiên được tạo tài khoản lúc khởi động. |

## Nên đặt

| Biến | Mặc định trong image | Mục đích |
|---|---|---|
| `STUDIO_ADMIN_PASSWORD` | rỗng | Mật khẩu cho admin đầu tiên đó. Rỗng = tự sinh và ghi vào log một lần. Cần từ 8 ký tự, có chữ và số. Chỉ dùng khi tạo tài khoản. |
| `STUDIO_DEMO_MODE` | rỗng | `true` chạy bản demo công khai ([demo.vi.md](demo.vi.md)): mỗi lần đăng nhập một tài khoản khách chỉ cho xem, workflow mẫu được tạo lại mỗi lần khởi động, node Code/HTTP/Send email tắt, model dùng mock. Không dùng cho công việc thật. |
| `STUDIO_DEMO_VISITOR_TTL` | `86400` | Chỉ ở chế độ demo: số giây trước khi tài khoản khách bị xoá cùng các run và cuộc trò chuyện. |
| `STUDIO_DEMO_RUN_RATE_LIMIT` | `20` | Chỉ ở chế độ demo: số run mỗi IP mỗi phút (0 = tắt). |
| `STUDIO_PUBLIC_URL` | rỗng | Địa chỉ https của ứng dụng (link trong email, callback Slack/Telegram). |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | rỗng | Nhà cung cấp LLM mặc định. Rỗng = câu trả lời mẫu; người dùng cũng có thể thêm credential trong Cài đặt. |

## Cơ sở dữ liệu và hàng đợi

| Biến | Mặc định trong image | Mục đích |
|---|---|---|
| `DATABASE_URL` | rỗng = SQLite tại `STUDIO_DB` | Chấp nhận URL `postgres://`, `postgresql://` và `postgresql+psycopg://` (hai dạng đầu được chuyển sang driver psycopg). Tìm kiếm vector trong kho tri thức dùng pgvector khi có. |
| `STUDIO_DB` | `/data/studio.db` | File SQLite. Đặt `/data` trên volume lưu trữ lâu dài. |
| `REDIS_URL` | rỗng | Tuỳ chọn. Rỗng = bus và hàng đợi run nằm trong bộ nhớ của process web (một instance). Đặt biến này để chạy worker riêng (`python -m app.worker`) hoặc nhiều instance web. |
| `STUDIO_WORKER` | `1` | `0` = process web không nhận run trong hàng đợi (để worker xử lý). |
| `STUDIO_AGENT_PARALLEL_TOOLS` | `4` | Số lời gọi công cụ trong một vòng của Agent được chạy cùng lúc. Kẹp trong 1..8. Giá trị không hợp lệ giữ ở 1. Một node Agent có thể tắt gọi song song. |

## Node Code

| Biến | Mặc định trong image | Mục đích |
|---|---|---|
| `STUDIO_ENABLE_CODE_NODES` | `1` | `0` để tắt chế độ Code. |
| `STUDIO_CODE_RUNTIME` | `subprocess` | Chạy trực tiếp trên server: code chạy trực tiếp trên máy chủ, không có Docker giới hạn quyền. Chỉ nên dùng cho code tin cậy. Image không có Docker daemon nên `docker` không dùng được ở đây. `remote` gửi lời gọi Code tới [dịch vụ sandbox](sandbox.vi.md). |
| `STUDIO_SANDBOX_URL`, `STUDIO_SANDBOX_TOKEN` | rỗng | Dịch vụ sandbox và token dùng chung (từ 16 ký tự), cho `STUDIO_CODE_RUNTIME=remote`. |
| `STUDIO_CODE_NO_NETWORK` | rỗng (`1` trong image sandbox) | `1` = code Python bị từ chối socket, process mới và ctypes (audit hook bên trong trình thông dịch). |
| `STUDIO_CODE_LANGUAGES` | `python,typescript` | Các ngôn ngữ được cung cấp. TypeScript chạy trên Deno có sẵn trong image. |
| `STUDIO_CODE_TS_DENO_DIR`, `STUDIO_CODE_TS_PACKAGES` | `/opt/deno-cache`, `npm:zod@3,npm:date-fns@4` | Các package TypeScript được cache trong image. Giữ nguyên trừ khi bạn tự build image. |
| `STUDIO_CODE_PACKAGES` | `pydantic,python-dateutil` | Các package Python hiển thị cho người dùng là import được. |
| `STUDIO_CODE_MAX_SECONDS` | `30` | Giới hạn thời gian mỗi lần gọi. |

## Mạng và nền tảng

| Biến | Mặc định trong image | Mục đích |
|---|---|---|
| `PORT` | `8000` | Cổng máy chủ lắng nghe. Render, Heroku và Railway tự đặt. |
| `STUDIO_TRUSTED_PROXIES` | `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10` | Các proxy được bỏ qua trong `X-Forwarded-For` khi xác định IP client (giới hạn tần suất, nhật ký kiểm toán). Mặc định gồm các dải riêng và dải dùng chung mà router PaaS kết nối từ đó. Nếu đứng sau CDN như Cloudflare, hãy thêm các dải của CDN. |
| `STUDIO_ENV` | `production` | Chế độ production: không có tài khoản demo, cookie phiên Secure, bắt buộc khoá bí mật. |
| `STUDIO_COOKIE_SECURE` | `1` ở production | Chỉ đặt `0` khi bạn phục vụ ứng dụng qua HTTP thường. |
| `STUDIO_STATIC_DIR` | `/app/static` | Giao diện đã build do API phục vụ. Rỗng = chỉ API. |
| `STUDIO_SECRET_KEY_FILE` | `/data/secret.key` | File khoá dùng khi `STUDIO_SECRET_KEY` rỗng (chỉ cho bản cài đặt cũ). |

Tracing (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `STUDIO_TRACE_URL`) và LangSmith
(`LANGSMITH_*`) hoạt động giống như trong `docker-compose.yml`; hãy trỏ tới collector được host.
