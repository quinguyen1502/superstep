# CLI

`superstep` cài, nâng cấp và sao lưu một instance trên máy có Docker và
Compose v2. Phiên bản gói là phiên bản server. Trên dòng `0.1.0` gói Python chỉ
là SDK; bản phát hành `v*` chuyển gói đó sang phiên bản server.

## Cài đặt

Trình cài một dòng là `scripts/install.sh`. Script từ chối Windows gốc và bảo
dùng WSL. Khi chưa có `uv`, script cài uv (bước này không cần Python), rồi chạy
`uv tool install 'superstep[cli]==<version>'`.

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

`superstep install` hỏi topology (`single` hoặc `full`), URL công khai và email
admin. `--yes` cùng các cờ đó thì bỏ qua câu hỏi. Image all-in-one là
`ghcr.io/quinguyen1502/superstep`. Stack đầy đủ dùng `superstep-api` và
`superstep-web`. Lần cài thứ hai vào instance đã có sẽ từ chối ghi đè.

Ghim một bản phát hành bằng cách lấy đúng tag rồi curl script, hoặc đặt
`SUPERSTEP_VERSION`.

## Nâng cấp

```bash
superstep upgrade --check
superstep upgrade
```

Lệnh này sao lưu, kéo image đúng phiên bản của nó (hoặc nạp `--images`), khởi
động lại và chờ `/api/health`. Health lỗi thì khôi phục bản sao lưu đó và tag
image trước. Log nằm ở `upgrade-failed-<utc>.log` trong thư mục instance.
Migration schema là việc của Alembic và không bị đảo ngược.

## Sao lưu

```bash
superstep backup
superstep restore <archive>
superstep backup --schedule daily --keep 7
```

`restore` yêu cầu gõ đúng tên instance. `--yes` chỉ bỏ qua khi `--name` trùng
tên đó. Archive mang database, `.env`, `compose.yml` và secret key, nên
credential đã lưu vẫn giải mã được sau khi restore vào một thư mục mới.

## Smoke test trên CI

`.github/workflows/cli.yml` chạy test của gói Python trên pull request. Workflow
này không phát hành. `.github/workflows/image.yml` chạy `scripts/cli_smoke.py`
trên image all-in-one vừa build: cài `single` khỏe, lần cài thứ hai bị từ chối,
sao lưu rồi restore vào thư mục mới, nâng cấp bị buộc lỗi health, và `doctor`
trên một fixture.

Lỗi bị buộc là `SUPERSTEP_UPGRADE_HEALTH_FAIL=1`. Biến này là hook của smoke
test, không phải cờ cho người vận hành. `doctor` trên fixture báo `STUDIO_ENV`
chưa đặt, `JWT_SECRET` còn là giá trị mẫu, và thiếu Docker socket.
