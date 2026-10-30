# Triển khai Superstep lên PaaS

[English](README.md) · [Biến môi trường](env-vars.vi.md)

Superstep có một **image all-in-one** (`Dockerfile` ở thư mục gốc, phát hành tại `ghcr.io/quinguyen1502/superstep`).
Một container phục vụ giao diện, `/api` và WebSocket `/ws/run` trên `$PORT`, nên phù hợp với các nền tảng chỉ định
tuyến một cổng cho mỗi dịch vụ. `docker-compose.yml` của repo (Postgres, Redis, api, worker, nginx) vẫn là cách
triển khai đầy đủ tính năng trên máy chủ của bạn.

## Máy chủ Docker của bạn

Trên máy có Docker, cài CLI rồi chạy `superstep install`. Lệnh này ghi một
project Compose cho image all-in-one hoặc stack đầy đủ. Các nút nền tảng bên
dưới giữ nguyên.

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

Trang handbook là Vận hành → CLI.

| | Image all-in-one (PaaS) | `docker-compose.yml` (máy chủ riêng) |
|---|---|---|
| Cơ sở dữ liệu | SQLite trong `/data` (cần volume lưu trữ lâu dài), hoặc Postgres qua `DATABASE_URL` | Postgres 17 + pgvector |
| Worker + Redis | Tuỳ chọn (mặc định tắt, run được thực thi trong process web) | Bật |
| Node Code | Bật, **Chạy trực tiếp trên server** (runtime subprocess, Python + TypeScript/Deno) | Sandbox Docker (sau khi bạn build image) |
| Tài khoản demo | Không có (chế độ production) | `admin@example.com` / `admin123` ở chế độ dev |

## Trước khi triển khai

- **Admin đầu tiên.** Chế độ production không có tài khoản demo. Đặt `STUDIO_ADMIN_EMAILS` là email của bạn. Ở lần
  khởi động đầu, tài khoản này được tạo với quyền admin. Mật khẩu dùng một lần được in **một lần** trong log của dịch
  vụ (`Created the admin account ... (sign in and change it now): <mật khẩu>`). Muốn tự chọn mật khẩu, đặt
  `STUDIO_ADMIN_PASSWORD` (từ 8 ký tự, có chữ và số). Hãy đổi mật khẩu sau lần đăng nhập đầu tiên.
- **Khoá bí mật.** Bắt buộc có `JWT_SECRET` và `STUDIO_SECRET_KEY`. Các mẫu bên dưới tự sinh cả hai.
  `STUDIO_SECRET_KEY` mã hoá các credential đã lưu: nếu đổi hoặc mất khoá này, chúng không giải mã được nữa.
- **Node Code chạy trực tiếp trên server.** Node Code được bật với runtime subprocess. Code đang chạy trực tiếp trên
  máy chủ, không có Docker giới hạn quyền: code có thể dùng mạng và đọc những gì process máy chủ đọc được (kể cả biến
  môi trường và `/data`). Chỉ nên dùng cho người dùng và code tin cậy, hoặc đặt `STUDIO_ENABLE_CODE_NODES=0`, hoặc chạy
  chúng trong [dịch vụ sandbox](sandbox.vi.md) riêng.
- **URL công khai.** Đặt `STUDIO_PUBLIC_URL` là địa chỉ https của dịch vụ. Link trong email và callback
  Slack/Telegram cần giá trị này.
- **Gói miễn phí sẽ ngủ.** Dịch vụ ngủ sẽ ngắt WebSocket đang mở và làm trễ lịch chạy, webhook. Ngoài mục đích dùng
  thử, hãy dùng instance luôn bật.

## Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/quinguyen1502/superstep)

| Blueprint | Tạo ra | Nút |
|---|---|---|
| [`render.yaml`](../../render.yaml) (mặc định) | Web service + ổ đĩa 1 GB tại `/data` (SQLite) | [Deploy](https://render.com/deploy?repo=https://github.com/quinguyen1502/superstep) |
| [`deploy/render/render.postgres.yaml`](../../deploy/render/render.postgres.yaml) | Web service + Render Postgres 17 | [Deploy](https://render.com/deploy?repo=https://github.com/quinguyen1502/superstep&path=deploy/render/render.postgres.yaml) |
| [`deploy/render/render.full.yaml`](../../deploy/render/render.full.yaml) | Web + worker + Render Postgres + Render Key Value | [Deploy](https://render.com/deploy?repo=https://github.com/quinguyen1502/superstep&path=deploy/render/render.full.yaml) |

1. Bấm một nút, đăng nhập Render và điền `STUDIO_ADMIN_EMAILS` (tuỳ chọn thêm `STUDIO_PUBLIC_URL`,
   `OPENAI_API_KEY`). `JWT_SECRET` và `STUDIO_SECRET_KEY` được tự sinh.
2. Khi deploy xong, mở **Logs** và sao chép mật khẩu admin dùng một lần.
3. Đặt `STUDIO_PUBLIC_URL` là `https://<service>.onrender.com` (hoặc tên miền của bạn) nếu bạn đã bỏ qua.

Lưu ý: ổ đĩa cần instance trả phí (Starter trở lên), và dịch vụ có ổ đĩa chỉ chạy được một instance. Render xoá
database Postgres miễn phí sau 30 ngày. Các blueprint đặt `autoDeployTrigger: off` để bản của bạn không tự deploy lại
mỗi khi repo này thay đổi; dùng **Manual Deploy** để cập nhật.

## Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/quinguyen1502/superstep)

[`app.json`](../../app.json) + [`heroku.yml`](../../heroku.yml) build image trên container stack và thêm
**Heroku Postgres** (Essential 0). Heroku không có ổ đĩa lưu trữ lâu dài nên không dùng được SQLite.

1. Bấm nút, nhập `STUDIO_ADMIN_EMAILS`, deploy.
2. `heroku logs --app <app> | grep "admin account"` hiện mật khẩu dùng một lần.
3. `heroku config:set STUDIO_PUBLIC_URL=https://<app>.herokuapp.com --app <app>`

Worker tuỳ chọn: `heroku addons:create heroku-redis:mini --app <app>` (đặt `REDIS_URL`), rồi
`heroku ps:scale worker=1 --app <app>`. Có thể thêm `heroku config:set STUDIO_WORKER=0` để run trong hàng đợi chỉ do
dyno worker xử lý (process worker bỏ qua biến này).

## Railway

[`railway.json`](../../railway.json) build `Dockerfile` ở thư mục gốc kèm health check. Hiện chưa có template công
khai; hãy deploy từ repo:

1. **New Project → Deploy from GitHub repo**, chọn bản fork của bạn hoặc `quinguyen1502/superstep`.
2. **Variables**: `JWT_SECRET` và `STUDIO_SECRET_KEY` (giá trị ngẫu nhiên, ví dụ `openssl rand -hex 32`),
   `STUDIO_ADMIN_EMAILS`.
3. SQLite: **thêm volume** cho dịch vụ, gắn tại `/data`. Hoặc Postgres: thêm database Postgres và đặt
   `DATABASE_URL=${{Postgres.DATABASE_URL}}` (dùng Postgres có pgvector nếu bạn cần tìm kiếm vector).
4. **Settings → Networking → Generate Domain**, rồi đặt `STUDIO_PUBLIC_URL` bằng địa chỉ đó.

Worker tuỳ chọn: thêm Redis (`REDIS_URL=${{Redis.REDIS_URL}}` cho cả hai dịch vụ) và một dịch vụ thứ hai từ cùng
repo với lệnh khởi động `python -m app.worker`.

## Fly.io

[`fly.toml`](../../fly.toml) chạy image đã phát hành với volume 1 GB tại `/data` (SQLite) và health check. Fly không
có nút deploy; hãy dùng CLI:

```sh
fly launch --copy-config --no-deploy --name <app>         # giữ fly.toml, chọn tổ chức và vùng của bạn
fly volumes create superstep_data --size 1 --region sin --app <app>
fly secrets set --app <app> JWT_SECRET=$(openssl rand -hex 32) STUDIO_SECRET_KEY=$(openssl rand -hex 32) \
  STUDIO_ADMIN_EMAILS=you@example.com STUDIO_PUBLIC_URL=https://<app>.fly.dev
fly deploy --app <app>
fly logs --app <app> | grep "admin account"
```

Chạy `fly secrets list` để kiểm tra khoá đã được lưu; Fly không bao giờ hiện lại giá trị bí mật, nên hãy giữ một bản
`STUDIO_SECRET_KEY`. Dùng Postgres thay cho SQLite: tạo cluster Fly Managed Postgres (hoặc Postgres bất kỳ), đặt
`DATABASE_URL` bằng `fly secrets set` và xoá khối `[[mounts]]`. `auto_stop_machines = "stop"` giúp tiết kiệm chi phí
nhưng ngắt WebSocket đang mở và làm trễ lịch chạy; đặt `"off"` nếu cần ứng dụng luôn bật. Chỉ giữ một machine khi
dùng SQLite (mỗi volume thuộc về một machine).

## DigitalOcean App Platform

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/quinguyen1502/superstep/tree/main)

[`.do/deploy.template.yaml`](../../.do/deploy.template.yaml) deploy image đã phát hành cùng database Postgres được
quản lý (App Platform không có volume lưu trữ lâu dài) và đặt `STUDIO_PUBLIC_URL` là URL của ứng dụng. Ở màn hình
xem lại, thay hai giá trị bí mật `change-me` bằng chuỗi ngẫu nhiên và đặt `STUDIO_ADMIN_EMAILS`. Mật khẩu admin dùng
một lần nằm trong **Runtime Logs**. Database development đủ cho dùng thử; hãy chuyển sang cluster được quản lý khi
chạy thật.

## Koyeb

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=docker&image=ghcr.io/quinguyen1502/superstep:latest&name=superstep&ports=8000;http;/&env%5BSTUDIO_ADMIN_EMAILS%5D=&env%5BJWT_SECRET%5D=&env%5BSTUDIO_SECRET_KEY%5D=&env%5BDATABASE_URL%5D=)

Nút này deploy image đã phát hành trên cổng 8000. Điền `STUDIO_ADMIN_EMAILS`, `JWT_SECRET`, `STUDIO_SECRET_KEY`
(chuỗi ngẫu nhiên) và `DATABASE_URL`: hãy tạo database Koyeb Postgres trước (hoặc dùng Postgres bất kỳ), vì instance
miễn phí không có volume. Đặt health check HTTP `/api/health` trên cổng 8000. Instance miễn phí giảm về 0 sau một giờ
không có truy cập.

## Zeabur

[`deploy/zeabur/template.yaml`](../../deploy/zeabur/template.yaml) chạy image đã phát hành với volume tại `/data`.
Mẫu này chưa được đưa lên marketplace; hãy deploy bằng CLI:

```sh
npx zeabur@latest template deploy -f deploy/zeabur/template.yaml
```

Lệnh sẽ hỏi tên miền, email admin và `STUDIO_SECRET_KEY`; `JWT_SECRET` được tự sinh. Muốn dùng Postgres, thêm dịch
vụ Zeabur PostgreSQL vào project và đặt `DATABASE_URL` bằng chuỗi kết nối của nó.

## Northflank

Chưa có mẫu được phát hành. Gói miễn phí Developer Sandbox (2 dịch vụ, 2 job, 1 addon) vẫn yêu cầu thêm phương thức
thanh toán mặc định trước khi tạo bất kỳ dịch vụ hay addon nào (API trả về `409 Please complete your account by
adding a default payment method`), nên hãy thêm trước. Trong giao diện Northflank:

1. **Create service → Deployment**, image ngoài `ghcr.io/quinguyen1502/superstep:latest`, cổng 8000 (HTTP, public).
2. **Secret group** liên kết với dịch vụ, gồm `JWT_SECRET`, `STUDIO_SECRET_KEY` (chuỗi ngẫu nhiên) và
   `STUDIO_ADMIN_EMAILS`.
3. Lưu trữ: thêm volume tại `/data` (SQLite), hoặc tạo **PostgreSQL addon** và liên kết chuỗi kết nối thành
   `DATABASE_URL`.
4. Health check: HTTP `/api/health` trên cổng 8000. Sao chép mật khẩu admin dùng một lần từ log của dịch vụ.

## Coolify và Dokploy (tự host)

Hai công cụ này chạy trên máy chủ của bạn, và đây là cách duy nhất để node Code chạy trong sandbox Docker. Hướng dẫn
đầy đủ: [Tự host với Coolify hoặc Dokploy](self-hosted.vi.md).

## Máy chủ Docker bất kỳ

```sh
export JWT_SECRET=$(openssl rand -hex 32) STUDIO_SECRET_KEY=$(openssl rand -hex 32)
echo "$STUDIO_SECRET_KEY"
docker run -d -p 8000:8000 -v superstep-data:/data -e JWT_SECRET -e STUDIO_SECRET_KEY \
  -e STUDIO_ADMIN_EMAILS=you@example.com ghcr.io/quinguyen1502/superstep:latest
docker logs <container> | grep "admin account"
```

Hãy lưu `STUDIO_SECRET_KEY` vừa in ra ở nơi an toàn: mọi lần khởi động đều cần đúng giá trị này.

## Image

`.github/workflows/image.yml` build image ở mọi pull request, khởi động image trên SQLite và trên Postgres, quét bằng
Trivy (thất bại khi có lỗ hổng nghiêm trọng đã có bản vá) và phát hành lên GHCR từ `develop` (`:develop`,
`:sha-<commit>`) và từ tag phát hành (`:1.2.3`, `:1.2`, `:latest`; `:1` từ bản 1.0). Không có khoá bí mật nào nằm
trong image.
