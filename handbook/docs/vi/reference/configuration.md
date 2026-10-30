# Cấu hình

Backend đọc cấu hình từ biến môi trường. `.env.example` ở thư mục gốc của repo
liệt kê mọi biến mà Compose truyền vào; trang này gom chúng theo nhóm.

## Cốt lõi

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_ENV` | `dev` | `production` từ chối `JWT_SECRET` mẫu và không tạo tài khoản demo |
| `JWT_SECRET` | giá trị mẫu | Ký token phiên |
| `JWT_TTL_SECONDS` | `86400` | Thời hạn phiên |
| `STUDIO_SECRET_KEY` | tự sinh | Khoá Fernet cho secret đã lưu |
| `STUDIO_SECRET_KEY_FILE` | `~/.superstep/secret.key` | Nơi lưu khoá tự sinh |
| `DATABASE_URL` | SQLite `backend/studio.db` | URL SQLAlchemy, ví dụ `postgresql://…` |
| `STUDIO_DB` | `backend/studio.db` | Đường dẫn SQLite khi `DATABASE_URL` trống |
| `REDIS_URL` | trống | Run bus, hàng đợi và bộ đếm; trống thì nằm trong bộ nhớ |
| `STUDIO_PUBLIC_URL` | trống | URL công khai cho link trong email, yêu cầu duyệt và webhook |
| `STUDIO_CORS_ORIGINS` | `*` khi phát triển, không có khi production | Các origin trình duyệt được phép |
| `STUDIO_COOKIE_SECURE` | `1` khi production | Cờ `Secure` của cookie phiên |
| `WEB_PORT` | `8080` | Compose: cổng của dịch vụ `web` |

## Tài khoản

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_ADMIN_EMAILS` | trống | Admin khởi tạo |
| `STUDIO_DEFAULT_ROLE` | `editor` | Vai trò của tài khoản mới (`editor` hoặc `viewer`) |
| `STUDIO_LOGIN_MAX_FAILURES` | `5` | Số lần đăng nhập sai trước khi khoá |
| `STUDIO_LOGIN_WINDOW` | `900` | Khung thời gian đếm (giây) |
| `STUDIO_LOGIN_LOCK` | `900` | Thời gian khoá (giây) |
| `STUDIO_PASSWORD_RESET_TTL` | `3600` | Thời hạn link đặt lại (giây) |

## Model

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `OPENAI_API_KEY` | trống | Dự phòng cho node LLM và embedding không có credential |
| `OPENAI_BASE_URL` | trống | Base URL cho phần dự phòng đó |
| `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL` | trống | Dự phòng cho node Decision |
| `STUDIO_PRICES` | trống | JSON ghi đè giá, USD cho 1 triệu token `{"prefix": [in, out]}` |
| `STUDIO_PRICES_FILE` | trống | Như trên, đọc từ file |

## Run và giới hạn

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_RECURSION_LIMIT` | `25` | Số bước mỗi run |
| `STUDIO_RUN_TIMEOUT` | `120` | Thời gian chạy (giây); run import mặc định 300 |
| `STUDIO_EVENT_MAX_BYTES` | `262144` | Một sự kiện |
| `STUDIO_RUN_MAX_BYTES` | `2097152` | Sự kiện lưu cho mỗi run |
| `STUDIO_INPUT_MAX_BYTES` | `262144` | Input của run |
| `STUDIO_WORKFLOW_MAX_BYTES` | `1048576` | JSON workflow |
| `STUDIO_WAIT_TTL` | `604800` | Run đang chờ hết hạn sau thời gian này (giây); `0` là không bao giờ |
| `STUDIO_VERSION_KEEP` | `0` | Số phiên bản giữ cho mỗi workflow; `0` giữ tất cả |
| `STUDIO_TEST_CASES_MAX` | `50` | Số [test case](../run/tests.md) mỗi workflow |
| `STUDIO_TEST_PARALLEL` | `4` | Số test case của một run test chạy cùng lúc |
| `STUDIO_ENABLE_DEMO_TOOLS` | `0` | Đăng ký `sleep_demo` để thử huỷ và timeout |

## Worker và hàng đợi

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_WORKER` | `1` | Chạy worker trong process API |
| `STUDIO_WORKER_CONCURRENCY` | `2` | Số job mỗi worker |
| `STUDIO_JOB_VISIBILITY_TIMEOUT` | `30` | Thời hạn giữ job (giây) |
| `STUDIO_JOB_REAP_EVERY` | `15` | Chu kỳ đưa job hết hạn về hàng đợi (giây) |
| `STUDIO_RECOVER_ON_START` | `1` | Hàng đợi trong bộ nhớ: đưa lại run chưa xong vào hàng đợi khi khởi động ([run qua các lần khởi động lại](../operate/deploy.md#run-qua-cac-lan-khoi-ong-lai)) |
| `STUDIO_RECOVER_MAX_ATTEMPTS` | `3` | Số lần restart được cắt ngang một run trước khi run kết thúc với `RUN_INTERRUPTED` |

## API trigger và webhook

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_TRIGGER_RATE_LIMIT` | `60` | Số run mỗi token trong một khung; `0` là tắt |
| `STUDIO_TRIGGER_RATE_WINDOW` | `60` | Độ dài khung (giây) |
| `STUDIO_CHAT_TRIGGER_RATE_LIMIT` | `60` | Chat trigger: số run mỗi người gửi và trigger trong một khung; `0` là tắt |
| `STUDIO_PUBLIC_CHAT_RATE_VISITOR` | `10` | Trang chat công khai: số tin nhắn của mỗi khách chat trong một khung; `0` là tắt |
| `STUDIO_PUBLIC_CHAT_RATE_IP` | `30` | Trang chat công khai: số tin nhắn của mỗi IP trong một khung; `0` là tắt |
| `STUDIO_PUBLIC_CHAT_RATE_READ` | `120` | Trang chat công khai: số lần mở trang, đọc chat và tạo chat mới của mỗi IP trong một khung; `0` là tắt |
| `STUDIO_PUBLIC_CHAT_RATE_WINDOW` | `60` | Độ dài khung (giây) của trang chat công khai. Giới hạn theo ngày của từng chat nằm trong Cài đặt Chat |
| `STUDIO_CHAT_ATTACHMENT_MAX_MB` | `10` | Tệp đính kèm trong chat: dung lượng tối đa mỗi tệp (MB); mỗi chat chỉ được đặt thấp hơn |
| `STUDIO_CHAT_ATTACHMENT_MAX_FILES` | `5` | Tệp đính kèm trong chat: số tệp tối đa mỗi tin nhắn; mỗi chat chỉ được đặt thấp hơn |
| `STUDIO_SYNC_WAIT_MAX` | `30` | Thời gian chờ `sync` tối đa (giây) |
| `STUDIO_ALLOW_PRIVATE_CALLBACKS` | `0` | Cho phép callback tới địa chỉ private |
| `STUDIO_WEBHOOK_MAX_ATTEMPTS` | `5` | Số lần gửi |
| `STUDIO_WEBHOOK_BACKOFF_BASE` | `2` | Cơ số backoff (giây) |
| `STUDIO_WEBHOOK_BACKOFF_MAX` | `300` | Trần backoff (giây) |
| `STUDIO_SECRET_GRACE` | `86400` | Secret cũ còn hiệu lực sau khi xoay (giây) |

## Tool, email và MCP

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_HTTP_TOOL_ALLOW_PRIVATE` | `0` | Node HTTP Tool được gọi địa chỉ private |
| `STUDIO_HTTP_TOOL_TIMEOUT` | `30` | Timeout request của HTTP Tool (giây) |
| `STUDIO_SMTP_ALLOW_PRIVATE` | `0` | Node Send email được dùng host SMTP private |
| `STUDIO_EMAIL_NODE_HOURLY_LIMIT` | `100` | Số người nhận mỗi giờ cho mỗi chủ workflow |
| `STUDIO_MCP_STDIO` | `0` | Cho phép máy chủ MCP stdio (chỉ admin) |
| `STUDIO_MCP_ALLOW_PRIVATE` | `0` | Cho phép máy chủ MCP HTTP ở địa chỉ private |
| `STUDIO_MCP_TIMEOUT` | `30` | Timeout gọi MCP (giây) |

## Chế độ Code

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_ENABLE_CODE_NODES` | `0` | Bật chế độ Code |
| `STUDIO_CODE_RUNTIME` | `docker` | `docker`, hoặc `subprocess` (chạy trực tiếp trên server, không có Docker giới hạn quyền) |
| `STUDIO_CODE_IMAGE` | `studio-code:1` | Image sandbox |
| `STUDIO_CODE_PACKAGES` | theo image | Package hiện trong trình soạn thảo |
| `STUDIO_CODE_MEMORY` | `256m` | Bộ nhớ mỗi lần gọi |
| `STUDIO_CODE_CPUS` | `0.5` | CPU mỗi lần gọi |
| `STUDIO_CODE_PIDS` | `64` | Số process mỗi lần gọi |
| `STUDIO_CODE_MAX_SECONDS` | `30` | Trần thời gian mỗi lần gọi |
| `STUDIO_CODE_CONCURRENCY` | `4` | Số container cùng lúc trên mỗi process |
| `STUDIO_CODE_TEST_PER_MINUTE` | `20` | Số run thử mỗi người mỗi phút |

## Import repo

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_ENABLE_IMPORT` | `0` | Bật import |
| `STUDIO_IMPORT_RUNTIME` | Docker | `subprocess` chỉ dùng khi test (chạy trực tiếp trên server, không có Docker giới hạn quyền) |
| `STUDIO_IMPORT_DIR` | `~/.superstep/imports` | Thư mục job |
| `STUDIO_IMPORT_HOST_DIR` | trống | Đường dẫn trên host của thư mục đó khi dùng Compose |
| `STUDIO_IMPORT_IMAGE` | `python:3.12-slim` | Image sandbox |
| `STUDIO_IMPORT_MEMORY` | `1g` | Bộ nhớ |
| `STUDIO_IMPORT_CPUS` | `1` | CPU |
| `STUDIO_IMPORT_PIDS` | `256` | Số process |
| `STUDIO_IMPORT_NETWORK` | `bridge` | Mạng khi chạy (`bridge` hoặc `none`) |
| `STUDIO_IMPORT_SECRETS` | trống | Tên biến môi trường thêm vào sandbox |
| `STUDIO_INSPECT_TIMEOUT` | `120` | Thời gian kiểm tra (giây) |
| `STUDIO_IMPORT_MAX_AGE_HOURS` | `72` | Tuổi để dọn; `0` là tắt |
| `STUDIO_IMPORT_MAX_BYTES` | `209715200` | Kích thước mã nguồn tối đa |
| `STUDIO_DOCKER_GID` | `10001` | Compose: group id của Docker socket |

## Thông báo và duyệt

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `SMTP_HOST` | trống | Email của studio (thông báo, link đặt lại, duyệt qua email); trống là tắt mail |
| `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | `587`, trống, trống, `studio@localhost` | Cấu hình SMTP |
| `SMTP_STARTTLS`, `SMTP_SSL` | `1`, `0` | Bảo mật đường truyền |
| `STUDIO_NOTIFY_WEBHOOK_URL`, `STUDIO_NOTIFY_WEBHOOK_SECRET` | trống | Webhook JSON cho run đang chờ và hết hạn |
| `STUDIO_APPROVAL_TTL` | `86400` | Thời hạn của nút và link duyệt (giây) |
| `STUDIO_IDENTITY_CODE_TTL` | `600` | Thời hạn mã xác minh (giây) |
| `STUDIO_IDENTITY_CODE_ATTEMPTS` | `5` | Số lần thử mỗi mã |
| `STUDIO_IDENTITY_CODE_RESEND` | `30` | Thời gian chờ gửi lại (giây) |
| `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET` | trống | **Add to Slack** |
| `WHATSAPP_API_URL` | Graph API | Base URL của WhatsApp Cloud API |
| `STUDIO_TRUSTED_PROXIES` | các dải private | CIDR của proxy cho `X-Forwarded-For` |
| `STUDIO_CALLBACK_RATE_LIMIT_IP` | `60` | Callback công khai mỗi IP trong một khung |
| `STUDIO_CALLBACK_RATE_LIMIT_CHANNEL` | `300` | Mỗi kết nối trong một khung |
| `STUDIO_CALLBACK_RATE_WINDOW` | `60` | Độ dài khung (giây) |

## Trace

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | trống | Endpoint OTLP/HTTP; trống là tắt trace |
| `OTEL_EXPORTER_OTLP_HEADERS` | trống | Header OTLP |
| `OTEL_SERVICE_NAME` | `superstep` | Tên dịch vụ |
| `STUDIO_TRACE_URL` | trống | Mẫu link **Mở trace** có `{trace_id}` |
| `STUDIO_OTEL_METRICS` | `0` | Xuất thêm metric |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` | trống | Xuất sang LangSmith |
| `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` | trống | Project và endpoint của LangSmith |
