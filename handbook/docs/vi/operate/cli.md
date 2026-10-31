# CLI

`superstep` cài, nâng cấp và sao lưu một instance trên máy có Docker và
Compose v2. Phiên bản gói là phiên bản server. Trên dòng `0.1.0` gói Python chỉ
là SDK; bản phát hành `v*` chuyển gói đó sang phiên bản server. Đăng nhập,
`pull`, `push`, `run`, `test` và `mcp` nằm ở các mục bên dưới. Các lệnh đó dùng
personal access token, không dùng Docker.

## Cài đặt

Trình cài một dòng là `scripts/install.sh`. Script từ chối Windows gốc và bảo
dùng WSL. Khi chưa có `uv`, script cài uv (bước này không cần Python), rồi chạy
`uv tool install 'superstep[cli]==<version>'`.

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

Gói cũng cài `sstep`, tên ngắn chạy đúng lệnh đó: `sstep status` giống
`superstep status`.

`superstep install` hỏi topology (`single` hoặc `full`), URL công khai và email
admin. `--yes` cùng các cờ đó thì bỏ qua câu hỏi. Image all-in-one là
`ghcr.io/quinguyen1502/superstep`. Stack đầy đủ dùng `superstep-api` và
`superstep-web`. Lần cài thứ hai vào instance đã có sẽ từ chối ghi đè.

Lệnh cũng hỏi lưu tệp đính kèm chat ở đâu: `db` (trong database, mặc định)
hoặc `fs` (một thư mục trên volume dữ liệu) với một máy, và thêm `s3` (bucket
tương thích S3) với stack đầy đủ. Với `--yes`, dùng
`--attachment-storage db|fs|s3`; với `s3` thêm `--s3-bucket` và khi cần
`--s3-endpoint`, `--s3-region`, `--s3-prefix`, `--s3-path-style` và
`--s3-access-key-id`. Secret key không bao giờ là cờ: nó được đọc từ
`--s3-secret-stdin`, từ `SUPERSTEP_S3_SECRET_ACCESS_KEY`, hoặc từ một câu hỏi
ẩn, và chỉ được ghi vào `.env` (quyền 600). `superstep deploy` nhận cùng các cờ
này. `superstep doctor` cho biết nơi lưu và nó có hoạt động không, kèm lý do
ngắn của server khi lỗi, không bao giờ hiện key. Xem
[Chat: Tệp đính kèm](../run/chat.md#tep-inh-kem).

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

Tệp đính kèm chat đi theo nơi lưu của chúng (xem
[Chat: Tệp đính kèm](../run/chat.md#tep-inh-kem)):

| Nơi lưu | Trong archive |
| --- | --- |
| `db` | Nằm trong bản dump database. |
| `fs` | Luôn có, dưới dạng `attachments.tar`. |
| `s3` | Chỉ khi chạy `superstep backup --include-attachments`. Nếu không, manifest ghi bucket và prefix, và lệnh nhắc bạn sao lưu bucket riêng. Sao lưu theo lịch (`--schedule`) không bao giờ chép các object trong bucket; manifest của chúng cũng ghi bucket và prefix. |

`restore` từ chối archive có nơi lưu tệp đính kèm khác với
`STUDIO_ATTACHMENT_STORAGE` của instance. `--force` vẫn khôi phục và giữ các
thiết lập `STUDIO_ATTACHMENT_*` của instance; tệp được ghi về nơi lưu mà bản ghi
của nó chỉ tới, rồi `superstep attachments migrate` chuyển chúng đi.

## Nơi lưu tệp đính kèm

```bash
superstep attachments migrate --to fs --dry-run
superstep attachments migrate --to fs
```

`migrate` chuyển tệp đính kèm chat sang `db`, `fs` hoặc `s3`. Mỗi tệp được chép,
đọc lại và kiểm tra (kích thước và SHA-256), rồi bản ghi được chuyển sang bản
mới và bản cũ bị xoá. Tệp nào lỗi thì ở nguyên chỗ cũ và được liệt kê; khi đó mã
thoát là 1. Lần chạy bị ngắt vẫn để mọi tệp đọc được, và chạy lại lệnh sẽ làm
tiếp; khi không còn gì thì lệnh không làm gì. `--batch N` đặt số tệp đọc mỗi đợt
(mặc định 100). Đặt `STUDIO_ATTACHMENT_STORAGE` cùng nơi lưu đó để tệp mới cũng
lưu ở đó. Admin cũng làm được qua API với `GET /api/admin/attachments` và
`POST /api/admin/attachments/migrate`.

## Đăng nhập

Các lệnh workflow không đọc `instance.json`.

```bash
superstep login --url http://localhost:8000
superstep whoami
superstep logout
```

`login` in một URL và một mã, rồi mở trình duyệt. Duyệt hoặc từ chối trên
`/cli/authorize` khi bạn đã đăng nhập studio. Không có gì được gửi cho đến khi
bạn bấm nút. Lệnh ghi `url`, `token` và `account` vào `~/.superstep/cli.json`
và đặt file ở mode `0600`. Lệnh không in token. `logout` xóa `token` và
`account` khỏi file đó. Lệnh không thu hồi token. Thu hồi trong Settings, mục
Tokens (`/settings/tokens`).

Với script hoặc CI, tạo token trong Settings rồi export hai biến. Biến môi
trường thắng file. Đừng commit token.

```bash
export SUPERSTEP_URL=http://localhost:8000
export SUPERSTEP_TOKEN
```

## Workflow trong Git

```bash
superstep pull ./workflows
superstep push ./workflows
superstep push ./workflows --force
```

`pull` ghi một file `<id>.json` cho mỗi workflow nhìn thấy và
`.superstep/lock.json`. Lệnh không xóa file local mà server không còn. `push`
cập nhật studio. Nếu workflow bị sửa trên studio sau lần `pull`, `push` thoát
khác 0 và không ghi gì. `--force` ghi đè sửa đó. Lock từ server khác cũng bị
từ chối, trừ khi có `--force`. `push` không xóa workflow trên server mà không
có file local.

```bash
superstep workflows list
superstep workflows export demo --format json
superstep workflows import ./demo.json
```

`import` chỉ nhận JSON của workflow. File `.py`, `.ts` hoặc `.zip` bị từ chối
và server không được gọi.

## Chạy

```bash
superstep run inbox --input sample.json --follow
superstep runs list
superstep runs show RUN_ID
superstep runs cancel RUN_ID
```

`run` mở cùng socket với bảng chạy và giữ socket đến khi lần chạy kết thúc.
Thoát 0 là `ok` hoặc `paused`. Thoát 1 là `error`. Thoát 2 là `waiting`: câu
hỏi được in ra và CLI không trả lời. Thoát 3 là hết giờ. Mặc định là 300 giây,
rồi CLI gửi cancel. Thoát 4 là `cancelled`.

## Kiểm tra trên CI

Cài CLI, export `SUPERSTEP_URL` và `SUPERSTEP_TOKEN`, rồi chạy bộ kiểm tra.
`--mock` chạy nút LLM ngoại tuyến. File JUnit là `superstep-junit.xml` trừ khi
`--junit` chỉ đường khác. Tiến trình thoát 1 khi một ca thất bại hoặc suite bị
hủy hay lỗi.

```bash
pip install 'superstep[cli]'
export SUPERSTEP_URL=http://localhost:8000
export SUPERSTEP_TOKEN
superstep test --all --mock --junit superstep-junit.xml
```

## MCP

`superstep mcp` nói MCP trên stdin và stdout. Chạy `superstep login` trước, hoặc
đặt `SUPERSTEP_URL` và `SUPERSTEP_TOKEN`. Bật MCP cho workflow trong studio.
Lệnh không tạo workflow token và không nhét token vào cấu hình client.

```json
{
  "mcpServers": {
    "superstep": {
      "command": "superstep",
      "args": ["mcp", "Support"]
    }
  }
}
```

Thay `Support` bằng tên workflow. Nhiều tên là một tiến trình.

## Smoke test trên CI

`.github/workflows/cli.yml` chạy test của gói Python trên pull request. Workflow
này không phát hành. `.github/workflows/image.yml` chạy `scripts/cli_smoke.py`
trên image all-in-one vừa build: cài `single` khỏe, lần cài thứ hai bị từ chối,
sao lưu rồi restore vào thư mục mới, nâng cấp bị buộc lỗi health, và `doctor`
trên một fixture.

Lỗi bị buộc là `SUPERSTEP_UPGRADE_HEALTH_FAIL=1`. Biến này là hook của smoke
test, không phải cờ cho người vận hành. `doctor` trên fixture báo `STUDIO_ENV`
chưa đặt, `JWT_SECRET` còn là giá trị mẫu, và thiếu Docker socket.
