# API trigger và webhook

Workflow nào cũng có thể được một dịch vụ khác khởi chạy qua HTTP. Để chạy
bằng tin nhắn Slack hoặc Telegram, xem [Chạy từ chat](chat-triggers.md).
SDK cho Python, TypeScript và toàn bộ mã lỗi nằm ở
[API công khai và SDK](public-api.md).

![Chạy qua API](../images/api-trigger.png)

## Trước khi bắt đầu

- Quyền chủ trên workflow: bạn sở hữu nó, hoặc bạn là admin. Editor của một
  workflow được chia sẻ chạy được nhưng không tạo được token.
- Workflow đã lưu. Run qua API dùng phiên bản đã lưu mới nhất.
- Worker đang chạy (mặc định worker chạy ngay trong process API).

## Tạo token

**⋯ → API** trong trình soạn thảo tạo token của workflow (`wft_…`) và secret
ký (`whsec_…`). Mỗi thứ chỉ hiện một lần. Thu hồi lúc nào cũng được; khi xoay
secret, secret cũ vẫn dùng được thêm `STUDIO_SECRET_GRACE` giây (mặc định một
ngày).

## Khởi chạy run

```bash
curl -X POST http://localhost:8080/api/hooks/workflows/<wid>/runs \
  -H "Authorization: Bearer wft_..." -H "Content-Type: application/json" \
  -d '{"input": {"message": "hi"}, "mode": "sync"}'
```

| Trường | Nghĩa |
| --- | --- |
| `input` | State ban đầu. |
| `mode` | `async` (mặc định) trả về ngay `202 {run_id, status: "queued"}`. `sync` chờ `final_state`, tối đa `STUDIO_SYNC_WAIT_MAX` giây (mặc định 30), quá thì trả `202` kèm `poll_url`. |
| `callback_url` | Tuỳ chọn. Nhận một POST có `X-Studio-Event: run.finished` khi run kết thúc. |

Hỏi trạng thái bằng `GET /api/hooks/workflows/<wid>/runs/<run_id>`. Token sai
trả về `401 TRIGGER_TOKEN_INVALID`. Run gọi qua API có nhãn **API** trong Lịch
sử.

## Kiểm tra callback

Mỗi callback mang header `X-Studio-Signature: t=<timestamp>,v1=<hex>`, trong
đó `v1` là HMAC-SHA256 của `"<t>.<raw body>"` với secret ký. Từ
chối timestamp lệch quá năm phút. Trong lúc xoay secret, header mang hai giá
trị `v1`; chấp nhận request khi một trong hai khớp.

```python
import hashlib, hmac, time

def verify(secret: str, header: str, body: bytes, tolerance=300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    if abs(time.time() - int(parts["t"])) > tolerance:
        return False
    mac = hmac.new(secret.encode(), f'{parts["t"]}.'.encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, parts["v1"])
```

## Lần gửi và retry

Mỗi lần gửi được lưu kèm trạng thái, số lần thử, mã HTTP và độ trễ, trong mục
**Lần gửi** của hộp thoại API, có nút **Gửi lại**. Lỗi mạng và phản hồi không
phải 2xx sẽ retry với độ trễ
`min(STUDIO_WEBHOOK_BACKOFF_BASE^n, STUDIO_WEBHOOK_BACKOFF_MAX)`, tối đa
`STUDIO_WEBHOOK_MAX_ATTEMPTS` lần. Bên nhận nên loại trùng theo `run_id` cộng
loại sự kiện.

URL callback đi qua lớp chặn SSRF: hostname được phân giải một lần, mọi địa
chỉ đều được kiểm tra, rồi kết nối đi thẳng tới IP đó và không theo redirect.
Địa chỉ private lỗi ngay trừ khi `STUDIO_ALLOW_PRIVATE_CALLBACKS=1`.

## Giới hạn tần suất

Mỗi token khởi chạy được `STUDIO_TRIGGER_RATE_LIMIT` run trong mỗi
`STUDIO_TRIGGER_RATE_WINDOW` giây (mặc định 60 run mỗi 60 giây). Vượt giới hạn
thì API trả về `429 RATE_LIMITED` kèm `Retry-After`. Hỏi trạng thái không bị
giới hạn. Bộ đếm dùng chung qua Redis; không có Redis thì mỗi process tự đếm.

## Run qua API chạy ở đâu

Run trong hàng đợi chạy trên worker. Xem
[Triển khai bằng Compose](../operate/deploy.md#worker-va-hang-oi) để chạy
worker thành process riêng.
