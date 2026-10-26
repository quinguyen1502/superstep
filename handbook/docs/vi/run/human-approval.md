# Duyệt bởi người

Node **Human** dừng run ở trạng thái `waiting` và đặt câu hỏi trong `prompt`.
Câu trả lời ghi vào `output_field` của node, nên Condition phía sau có thể rẽ
nhánh theo nó.

![Run đang chờ duyệt](../images/human-waiting.png)

## Trả lời trong studio

Logs trong tab **Chạy** hiện câu hỏi kèm **Duyệt** (`approved`), **Từ chối** (`rejected`),
hoặc **Gửi phản hồi** bằng văn bản tự do. Ở đây chỉ chủ của run mới mở, trả lời
hoặc huỷ run được.

## Trang Duyệt

**Duyệt** (`/approvals`, biểu tượng hình người trên thanh trên) liệt kê mọi
bước đang chờ bạn, ở tất cả workflow: run của bạn, và run mà bạn là **người
duyệt** của node Human đang chờ. Mỗi dòng hiện workflow, bước, câu hỏi, người
chạy, thời gian đã chờ và kênh đã gửi yêu cầu. Trả lời bằng **Duyệt**, **Từ
chối** hoặc văn bản, ngay trên dòng đó.

![Trang Duyệt](../images/approvals.png)

- Ghi email người duyệt vào ô **Người duyệt** của node Human. Ô này dùng được cả
  khi node có hoặc không có kênh duyệt. Mỗi địa chỉ phải là một tài khoản trong
  studio.
- Người duyệt chỉ thấy yêu cầu: không thấy workflow, trace hay dữ liệu của run.
  **Mở run** chỉ hiện với chủ run, và với chủ workflow hoặc admin.
- Câu trả lời đầu tiên được tính, dù đến từ editor, trang Duyệt hay nút
  trên chat. Các câu trả lời sau bị từ chối. Trả lời ở đây sẽ đóng yêu cầu trên
  chat và sửa lại tin nhắn.
- Nhãn trên thanh trên đếm số bước đang chờ bạn, và trang **Workflows** hiện
  link tới trang này khi còn bước đang chờ.

![Workflows có run đang chờ](../images/workflows.png)

Checkpoint nằm trong database, nên khởi động lại server vẫn chạy tiếp run từ
chỗ đã dừng. Thời gian chờ không tính vào thời gian chạy của run. Chờ lâu hơn
`STUDIO_WAIT_TTL` giây (mặc định 7 ngày; `0` là không bao giờ hết hạn) thì run
thành `expired`, và tiếp tục khi đó trả về `410 RUN_EXPIRED`.

```text
GET  /api/approvals/inbox                       # các bước đang chờ bạn, chủ run hoặc người duyệt
POST /api/approvals/inbox/{run_id}  {"response": "approved"}
GET  /api/runs/pending                          # run của chính bạn đang chờ
WS   /ws/run   {"resume_run_id": "…", "response": "approved"}
POST /api/runs/{id}/cancel
```

## Hạn chờ

Node Human có thể có **Hạn chờ** (công tắc dưới phần kênh duyệt). Nếu không đặt,
bước này chờ đến khi có người trả lời hoặc đến `STUDIO_WAIT_TTL`.

![Cài đặt hạn chờ trên node Human](../images/human-deadline.png)

| Cài đặt | Tác dụng |
| --- | --- |
| **Chờ tối đa** | Bước này chờ bao lâu, tính bằng phút, giờ hoặc ngày. |
| **Nhắc lại mỗi** | Không bắt buộc. Gửi lời nhắc theo chu kỳ này, tối đa 5 lần. |
| **Khi hết hạn** | **Từ chối** hoặc **Duyệt**: run đi tiếp như thể đã có câu trả lời đó. **Chuyển cho người duyệt khác**: xem bên dưới. |
| **Chuyển cho** | Email của người dùng studio, dùng với **Chuyển cho người duyệt khác**. |

- **Lời nhắc** đến chủ run và người duyệt dưới dạng thông báo (chuông, và
  email nếu họ bật). Với node có kênh duyệt, lời nhắc còn là một tin nhắn mới
  có nút mới; tin nhắn cũ ghi là đã nhắc lại, và nút của nó ngừng hoạt động.
- **Từ chối** và **Duyệt** khi hết hạn đi theo các nhánh bình thường của node.
  Trace của run (`run_resumed`, `by: {"channel": "deadline"}`) và Audit log
  (**Hết hạn chờ**) ghi rõ là do hạn chờ, không phải do người trả lời.
- **Chuyển cho người duyệt khác** chỉ xảy ra một lần. Những người được ghi tên trở
  thành người duyệt, nhận yêu cầu trên kênh và trong trang **Duyệt** của họ,
  và có thêm một khoảng thời gian như trên. Nếu vẫn không ai trả lời, bước này bị
  từ chối. Địa chỉ không có tài khoản studio sẽ bị bỏ qua và ghi vào log.
- Nút trên chat hết hạn đúng hạn chờ nếu hạn chờ đến trước.
- Hạn chờ phải ngắn hơn `STUDIO_WAIT_TTL` (gấp đôi nếu có chuyển tiếp); nếu không,
  bước kiểm tra workflow sẽ báo lỗi.
- Trang **Duyệt** hiện hạn của từng bước, hoặc **Quá hạn**, bước gần hạn nhất
  lên đầu.

Thời gian tính theo đồng hồ thực, không có giờ làm việc. Hạn chờ được kích hoạt từ
vòng bảo trì của worker, mỗi mốc một lần, kể cả khi có nhiều worker hoặc sau khi
khởi động lại. Hạn đã qua trong lúc server tắt sẽ được xử lý ngay khi server chạy lại.

## Thông báo

Chuông liệt kê thông báo chưa đọc và nhận thông báo trực tiếp qua
`/ws/notifications`, dự phòng bằng cách hỏi lại mỗi 30 giây. Mỗi người tự chọn
loại thông báo ở **Cài đặt → Hồ sơ**.

| Kênh | Thiết lập |
| --- | --- |
| Chuông trong app | Luôn bật |
| Email | `SMTP_HOST` (và `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` hoặc `SMTP_SSL`); link dùng `STUDIO_PUBLIC_URL` |
| Webhook | `STUDIO_NOTIFY_WEBHOOK_URL` nhận JSON cho mỗi run `waiting` hoặc `expired`, có chữ ký bằng `STUDIO_NOTIFY_WEBHOOK_SECRET` nếu đặt |

## Duyệt qua chat

Node Human cũng có thể gửi yêu cầu tới một **kênh duyệt**:

| Kênh | Mang theo | Câu trả lời |
| --- | --- | --- |
| Slack | Nút Duyệt / Từ chối | bấm nút bằng tài khoản Slack đã xác minh |
| Telegram | Nút Duyệt / Từ chối | bấm nút bằng tài khoản Telegram đã xác minh |
| WhatsApp | Hai nút trả lời | trả lời từ số điện thoại đã xác minh |
| Email | Link Duyệt / Từ chối tới `/approve?token=…` | xác nhận trong studio sau khi đăng nhập |
| Microsoft Teams | Adaptive Card có link | xác nhận trong studio sau khi đăng nhập |

Quy tắc giống nhau ở mọi kênh: chỉ chủ run hoặc người duyệt có tên trên node,
mỗi yêu cầu một câu trả lời, và có hạn (`STUDIO_APPROVAL_TTL`, mặc định 86400
giây). Token của nút được ký HMAC và chỉ dùng một lần. Tin nhắn theo ngôn ngữ
của chủ run. Trả lời trong studio sẽ vô hiệu hoá nút trên chat; huỷ hoặc hết
hạn sẽ đóng yêu cầu. Chưa cấu hình kênh nào thì không gửi gì.

Cách thiết lập từng kênh ở [Kênh duyệt](../operate/channels.md).

## Duyệt từ node Agent

[Node Agent](../guide/agent.md#duyet-truoc-khi-goi-cong-cu) có thể hỏi trước khi
gọi một công cụ bật **Cần duyệt**. Run chờ đúng như ở node Human: bước này, tên
là `Agent › công cụ`, hiện công cụ và các tham số, và được gửi tới panel run,
trang **Duyệt** và kênh duyệt đặt trên node Agent, cùng người duyệt và hạn chờ
của nó. **Duyệt** để chạy lần gọi. **Từ chối**, hoặc trả lời bằng chữ, là từ
chối, và model được báo như vậy, với đoạn chữ làm lý do. Mỗi lần gọi đều hỏi
lại.

## Duyệt bên trong workflow được gọi

Khi node Agent gọi một workflow khác làm công cụ (xem
[Workflow làm công cụ](../guide/agent.md#workflow-lam-cong-cu)), node Human hoặc
công cụ cần duyệt bên trong workflow đó vẫn hỏi như thường. Yêu cầu ghi tên cả
hai workflow, ví dụ `Đội hỗ trợ › Refund desk`, ở trang **Duyệt** và trong tin
nhắn trên kênh. Run gọi nó cũng đứng chờ nhưng không được liệt kê: nó tự chạy
tiếp khi run được gọi xong.

## Mẫu thường gặp

```text
Start → LLM (soạn trả lời) → Human (duyệt bản nháp?) → Condition theo decision
      ├─ approved → Send email → End
      └─ rejected → End
```

Mẫu khởi đầu **Approval flow** có sẵn hình dạng này.
