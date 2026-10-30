# Triển khai bằng Compose

## Cài bằng CLI

Trên máy có Docker, cài lệnh rồi tạo instance từ trang [CLI](cli.md):

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

Các mục bên dưới là layout Compose của topology `full` và danh sách kiểm tra
cho production. Nút triển khai lên nền tảng vẫn nằm trong tài liệu deploy của
repo.

## Các dịch vụ

| Dịch vụ | Image | Vai trò |
| --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg17` | Workflow, run, checkpoint, phiên bản, vector |
| `redis` | `redis:7-alpine` | Run bus, hàng đợi job, bộ đếm giới hạn tần suất, thông báo trực tiếp |
| `api` | `./backend` | FastAPI. Chạy migration Alembic và seed khi khởi động |
| `worker` | `./backend`, `python -m app.worker` | Chạy job trong hàng đợi: run qua API, lịch chạy, run khôi phục, gửi webhook |
| `web` | `./frontend` | nginx phục vụ bản build Vite và chuyển `/api`, `/ws` sang API |
| `jaeger` | `jaegertracing/all-in-one` | Tuỳ chọn, bật bằng `--profile tracing` |

```bash
cp .env.example .env   # đặt JWT_SECRET và POSTGRES_PASSWORD; không commit .env
docker compose up --build
python scripts/compose_smoke.py http://localhost:8080
```

UI ở `http://localhost:8080` (`WEB_PORT`). `.env.example` liệt kê mọi biến; các
biến hay dùng nhất có ở [Cấu hình](../reference/configuration.md).

## Danh sách kiểm tra cho production

| Cấu hình | Lý do |
| --- | --- |
| `STUDIO_ENV=production` | Từ chối `JWT_SECRET` mẫu, không tạo tài khoản demo, và vô hiệu hoá tài khoản đó nếu còn mật khẩu demo. |
| `JWT_SECRET` | Ký phiên đăng nhập. Dài và ngẫu nhiên. |
| `STUDIO_SECRET_KEY` | Khoá Fernet cho credential đã lưu. Nên đặt rõ ràng; mất khoá thì credential cũ không đọc được nữa. |
| `STUDIO_ADMIN_EMAILS` | Tạo admin đầu tiên (production không có admin demo). |
| `STUDIO_PUBLIC_URL` | URL công khai dùng cho link trong email, yêu cầu duyệt và webhook. |
| `STUDIO_CORS_ORIGINS` | Chỉ cần khi trình duyệt ở origin khác gọi API. Production mặc định không cho origin nào. |
| `STUDIO_TRUSTED_PROXIES` | CIDR của các proxy phía trước, để đọc đúng IP client cho giới hạn tần suất. |
| TLS | Kết thúc HTTPS ở phía trước `web`. Cookie phiên là `Secure` trong production. |

`STUDIO_SECRET_KEY` để trống sẽ được sinh một lần vào volume `apidata`
(`/data/secret.key`). Cách này chạy được, nhưng hãy sao lưu volume cùng với
database.

## Nâng cấp từ v0.1.0

v0.1.0 có tên LangGraph Studio, và project Compose của nó là
`langgraph-studio`. Project giờ là `superstep`, nhưng volume vẫn giữ tên của
v0.1.0 (`langgraph-studio_pgdata`, `_redisdata`, `_apidata`), nên database,
hàng đợi và khoá bí mật tự sinh được giữ nguyên. Hãy dừng stack cũ trước khi
chạy stack mới, nếu không Compose sẽ chạy thêm một bộ container thứ hai trên
cùng cổng và volume:

```bash
docker compose -p langgraph-studio down   # giữ volume; đừng thêm -v
git pull && docker compose up -d --build
```

Kiểm tra thêm những chỗ còn dùng tên cũ:

- **Telemetry:** `OTEL_SERVICE_NAME` mặc định giờ là `superstep`. Đặt
  thành `langgraph-studio` để giữ các dashboard hiện có.
- **Email:** tiêu đề bắt đầu bằng `[Superstep]`. Hãy cập nhật bộ lọc thư.
- **Chạy ở máy (không Docker):** khoá và thư mục import chuyển sang
  `~/.superstep/`. `~/.langgraph-studio/` vẫn được dùng khi thư mục mới chưa có.
- **File:** template đã export và node đã sao chép từ v0.1.0 vẫn nhập và dán được.

## Database

`GET /api/health` cho biết `database` (`postgresql` hoặc `sqlite`) và
`run_bus` (`redis` hoặc `memory`). Khi phát triển ở máy, để trống
`DATABASE_URL` để dùng SQLite `backend/studio.db`, và để trống `REDIS_URL` để
run bus nằm trong bộ nhớ.

Migration lúc khởi động có khoá để nhiều process không migrate cùng lúc
(advisory lock của Postgres, hoặc `<db>.migrate.lock` với SQLite). Thay đổi
schema đi qua Alembic:

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "describe"
.venv/bin/alembic upgrade head
```

## Worker và hàng đợi

`STUDIO_WORKER=1` (mặc định khi không dùng Compose) chạy worker ngay trong
process API. Khi có `REDIS_URL`, worker có thể là process riêng
`python -m app.worker`; Compose đặt API là `STUDIO_WORKER=0` và chạy dịch vụ
`worker`.

```bash
docker compose up --scale worker=3
```

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_WORKER_CONCURRENCY` | 2 | Số job một worker chạy cùng lúc |
| `STUDIO_JOB_VISIBILITY_TIMEOUT` | 30 giây | Thời hạn giữ job; worker gia hạn trong lúc chạy |
| `STUDIO_JOB_REAP_EVERY` | 15 giây | Chu kỳ đưa các job hết hạn giữ về lại hàng đợi |
| `STUDIO_RECOVER_ON_START` | 1 | Hàng đợi trong bộ nhớ: đưa lại các run chưa xong vào hàng đợi khi server khởi động |
| `STUDIO_RECOVER_MAX_ATTEMPTS` | 3 | Số lần restart được cắt ngang một run trước khi việc khôi phục dừng với `RUN_INTERRUPTED` |

Với Redis, job có worker bị chết sẽ được đưa lại hàng đợi khi hết hạn giữ, và
chạy tiếp từ checkpoint cuối (`run_recovered` trong trace). Mỗi lần worker nhận
một run, `runs.lease_gen` tăng lên; mọi lần ghi phải mang fencing token đó, nên
worker đã mất quyền giữ không ghi được và tự dừng.

## Run qua các lần khởi động lại

Superstep lưu checkpoint của run trong database của chính nó (mặc định SQLite,
Postgres khi có `DATABASE_URL`), không phải trong saver bộ nhớ của LangGraph,
nên khởi động lại hay sập server đều không mất run đang dừng:

| Run | Sau khi khởi động lại |
| --- | --- |
| Đang dừng ở node Human | Vẫn đang chờ. Trả lời trong studio, kênh chat hoặc API như trước; run chạy tiếp từ checkpoint. |
| Đã được trả lời nhưng chưa chạy tiếp | Chạy tiếp với câu trả lời đó. Câu trả lời được giữ trên run cho tới khi run chạy tiếp, nên câu trả lời nhận ngay trước lúc khởi động lại không bị mất. |
| Run API, lịch, chat hoặc test đang chờ hoặc đang chạy | Chạy tiếp từ node đã xong cuối cùng. Job trong hàng đợi lưu checkpoint tiến độ sau mỗi node; node đang chạy dở chạy lại, các lần gọi đã xong không lặp lại ([side effect gần như đúng một lần](../reference/architecture.md#side-effect-gan-nhu-ung-mot-lan)). |
| Đang chạy trong editor | Kết thúc cùng kết nối của trình duyệt; run chỉ được lưu khi xong. Hãy chạy lại. |

Cách các run chưa xong quay lại tùy hàng đợi:

- **Redis** (`REDIS_URL`): job vẫn nằm trong Redis; khi hết hạn giữ, worker bất
  kỳ nhận lại.
- **Hàng đợi trong bộ nhớ** (không có `REDIS_URL`, một process): job trong bộ
  nhớ đã mất, nên khi khởi động server đưa mọi run `queued` hoặc `running` vào
  lại hàng đợi dưới dạng job khôi phục, cùng mọi câu trả lời đang giữ trên run
  chưa chạy tiếp. Chỉ đặt `STUDIO_RECOVER_ON_START=0` khi
  nhiều process API dùng chung một database mà không có Redis, vì process này
  sẽ nhận mất run của process kia.

Run đã bị restart cắt ngang `STUDIO_RECOVER_MAX_ATTEMPTS` lần (ví dụ một node
cứ làm sập server) không được chạy tiếp nữa: run kết thúc với `error`, mã
`RUN_INTERRUPTED`, giữ lại các sự kiện đến lúc đó. Các lần chạy tiếp sau node
Human hoặc sau khi duyệt tool của Agent không được tính.

## Model chạy ở máy khi dùng Compose

Trong Compose, `localhost` là chính container. `api` và `worker` đặt
`extra_hosts: host.docker.internal:host-gateway`, nên trỏ Ollama tới
`http://host.docker.internal:11434` và LM Studio tới
`http://host.docker.internal:1234/v1`. Trên Linux, chạy
`OLLAMA_HOST=0.0.0.0 ollama serve` và bật *Serve on Local Network* của LM
Studio; firewall có thể cần cho phép bridge của Docker.

## Docker socket

Compose gắn `/var/run/docker.sock` vào `api` và `worker`, phục vụ
[chế độ Code](code-runtime.md) và [import repo](import.md). Socket này tương
đương quyền root trên máy chạy Docker. Đừng bật hai tính năng đó trên máy bạn
không tin. Trên Linux, nếu user của container (uid 10001) không mở được
socket, đặt `STUDIO_DOCKER_GID="$(stat -c %g /var/run/docker.sock)"`.
