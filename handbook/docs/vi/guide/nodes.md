# Các loại node

| Node | Dùng để | Ghi vào |
| --- | --- | --- |
| [Start](#start-va-end), [End](#start-va-end) | Điểm vào và điểm ra của graph | — |
| [LLM](#llm) | Gọi model với prompt template | `output_field` |
| [Agent](#agent) | Model tự chọn và gọi các công cụ bạn cho phép, tới khi trả lời được | `output_field`, `steps_field` (tuỳ chọn) |
| [Decision (Jev)](#decision-jev) | Câu trả lời có kiểu từ TypeSafe Jev | mỗi câu hỏi một trường, cộng `output_field` |
| [Retriever](#retriever) | Tìm trong kho tri thức | `output_field` (danh sách) |
| [Tool](#tool) | Hàm Python, request HTTP, hoặc code Python của bạn | `output_field` |
| [MCP tool](#mcp-tool) | Gọi công cụ trên máy chủ MCP | `output_field` |
| [Send email](#send-email) | Gửi một email qua SMTP | `output_field` (tuỳ chọn) |
| [Condition](#condition) | Chọn một edge đi ra theo giá trị của trường | — |
| [For each](#for-each) | Lặp qua một danh sách, từng phần tử | `item_field`, `index_field` |
| [Human](#human) | Dừng tới khi có người trả lời | `output_field` |
| [Join](#join) | Chờ mọi nhánh đi vào | — |
| [Subgraph](#subgraph) | Chạy một workflow đã lưu bên trong workflow này | các trường dùng chung |
| [Code (imported)](#code-imported) | Node chỉ đọc từ repo đã import | — |

## Cấu hình thực thi

Node LLM, Agent, Decision, Retriever, Tool, MCP tool và Human có mục **Thực
thi** trong cấu hình:

| Cấu hình | Tác dụng |
| --- | --- |
| Số lần thử | Retry policy của LangGraph: thử node tối đa bao nhiêu lần. |
| Chờ giữa các lần (giây) | Khoảng chờ ban đầu giữa các lần thử. |
| Timeout (giây) | Dừng lần thử đó; retry sẽ chạy lại. |
| Cache TTL (giây) | Cache node của LangGraph: cùng input trong thời gian TTL thì dùng lại kết quả. |

Để trống là tắt.

## Start và End

Graph nào cũng có đúng một Start. Node End kết thúc một nhánh. Không xoá và
không sao chép được hai node này. Start nhận input của run làm state ban đầu.

## LLM

| Cấu hình | Ghi chú |
| --- | --- |
| Credential | Một nhà cung cấp trong **Credentials**. Để trống thì dùng `OPENAI_API_KEY`, không có nữa thì dùng mock offline. |
| Model | Chọn trong danh sách model của nhà cung cấp, hoặc gõ tay. |
| Prompt template | Văn bản có tham chiếu `{{state.field}}` và filter. |
| Trường output | Trường của state nhận câu trả lời. |

Trong lúc chạy, từng đoạn token tới dưới dạng sự kiện `node_token` và hiện ở
dòng Logs lẫn tab Output. Các đoạn này không lưu vào lịch sử run; văn bản cuối
cùng thì có. Lỗi từ nhà cung cấp (401, timeout, …) thành sự kiện `error` của
node, không làm sập server.

## Agent

Một prompt nhiệm vụ, danh sách công cụ (MCP, HTTP, hàm có sẵn, tìm trong kho
tri thức) và số vòng tối đa. Model gọi công cụ tới khi trả lời được; một công cụ
có thể cần người duyệt trước mỗi lần gọi. Xem [Node Agent](agent.md).

## Decision (Jev)

Hỏi Jev của [TypeSafe](https://typesafe.ai) về `text` và nhận câu trả lời có kiểu (một
template; nếu đúng bằng một `{{state.x}}` thì gửi giá trị kèm kiểu). Mỗi câu
hỏi có `id`, `instructions` và một kiểu:

| Kiểu | Cấu hình | Câu trả lời |
| --- | --- | --- |
| `choice` | 2–255 `options` | nhãn của một lựa chọn |
| `score` | 2–10 `levels`, từ thấp tới cao | số từ 0 tới chỉ số của mức cuối; có thể nằm giữa hai mức |
| `noul` | — | số từ 0 (sai) tới 1 (đúng) |

`field` của câu hỏi nhận câu trả lời, nên Condition có thể rẽ nhánh theo một
lựa chọn. `output_field` (object) nhận mọi câu trả lời kèm xác suất và độ tin
cậy. Node dùng credential TypeSafe, rồi tới `TYPESAFE_API_KEY`, rồi tới câu trả
lời mẫu offline (`choice` chọn lựa chọn đầu tiên được nhắc trong văn bản). Giá
là $0.042 cho mỗi triệu token input; token output miễn phí. Run được khôi phục
dùng lại câu trả lời cũ.

## Retriever

| Cấu hình | Ghi chú |
| --- | --- |
| Kho tri thức | Một [kho tri thức](knowledge.md) của bạn. |
| Query | Một template, thường là `{{state.message}}`. |
| Top K | 1–20 kết quả. |
| Trường output | Nhận một danh sách `{text, score, filename, …}`. |

## Tool

Node Tool có ba chế độ.

=== "Function"

    Gọi một hàm Python đăng ký bằng `@register_tool` trong
    `backend/app/engine/tools.py`, ví dụ `lookup_order`. `GET /api/tools` liệt kê
    các hàm đã đăng ký. Hàm nào khai báo tham số `idempotency_key` sẽ nhận key
    của node.

=== "HTTP"

    `method`, `url` và `body` dạng template. URL phải trỏ tới địa chỉ công khai:
    địa chỉ loopback, private, link-local và metadata bị chặn với
    `HTTP_TOOL_URL_BLOCKED`, trừ khi `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`. Request
    đi thẳng tới IP đã kiểm tra, không theo redirect, và hết giờ sau
    `STUDIO_HTTP_TOOL_TIMEOUT` giây (mặc định 30). Request mang
    `Idempotency-Key`, `X-Studio-Run-Id` và `X-Studio-Attempt`.

=== "Code Python"

    `main(state)` do bạn viết, chạy trong sandbox. Xem [Chế độ Code](code-mode.md).

## MCP tool

`server_id`, `tool`, `arguments` và `output_field`. Chuỗi trong arguments là
template; argument nào đúng bằng một `{{state.x}}` thì giữ nguyên kiểu, nên
`{{state.items | length}}` truyền đi một số. Xem [Máy chủ MCP](mcp.md).

## Send email

Gửi một email qua credential SMTP (**Credentials → SMTP**: host, port,
STARTTLS / SSL / không, tên đăng nhập, người gửi; mật khẩu được mã hoá).

![Node Send email trong một run](../images/email-node.png)

- `to`, `cc`, `bcc` và `reply_to` là template, các địa chỉ cách nhau bằng dấu
  phẩy; một `{{state.x}}` cũng có thể chứa danh sách. Tối đa 50 người nhận.
- `subject` và `body` là template. Với định dạng **HTML**, giá trị lấy từ state
  được escape và có thêm phần văn bản thường.
- `output_field` (tuỳ chọn, object) nhận
  `{sent, dry_run, to, cc, bcc, subject, message_id, refused}`.
- **Không có credential thì node chạy thử (dry run):** không gửi gì, kết quả
  chứa nội dung thư kèm `preview` dạng văn bản.
- Run được khôi phục không bao giờ gửi lại, và `Message-ID` lấy từ idempotency
  key của node.
- Host SMTP private hoặc loopback cần `STUDIO_SMTP_ALLOW_PRIVATE=1` (ví dụ
  Mailpit ở `localhost:1025`).
- Các node của một chủ workflow gửi tới tối đa
  `STUDIO_EMAIL_NODE_HOURLY_LIMIT` người nhận mỗi giờ (mặc định 100).

Đặt node Human phía trước để duyệt bản nháp email.

## Condition

Đặt **Trường state để rẽ nhánh** là một trường của state. Nhãn các edge đi ra được so với giá trị
của trường:

1. khớp chính xác;
2. khớp không phân biệt hoa thường, sau khi bỏ khoảng trắng và dấu câu;
3. khớp nguyên một từ trong giá trị, nhãn dài nhất thắng.

Thứ tự nhãn không quan trọng: `Disapprove.` chọn `disapprove`, không chọn
`approve`. Hai nhãn nguyên từ dài bằng nhau là mơ hồ. Edge **default** (tuỳ
chọn) dùng khi không khớp hoặc khớp mơ hồ.

Condition là node duy nhất được có edge quay về chính nó, và cùng với For each
là cách duy nhất để đóng một vòng lặp.

## Nhánh song song

Nhiều edge đi ra từ một node không phải Condition sẽ chạy trong cùng một
superstep. Trường được nhiều nhánh ghi cần reducer (`append`, `merge` hoặc
`add`); thiếu reducer thì không qua được kiểm tra. Dùng [Join](#join) để chờ
mọi nhánh.

## For each

| Cấu hình | Ghi chú |
| --- | --- |
| `items_field` | Trường kiểu danh sách để lặp qua. |
| `item_field` | Nhận phần tử hiện tại. |
| `index_field` | Tuỳ chọn, kiểu integer hoặc number: chỉ số tính từ 0. |
| `max_items` | 1–1000, mặc định 100. List dài hơn thì node lỗi. |

Node cần hai edge đi ra có nhãn `each` và `done`; trình soạn thảo tự đặt nhãn
`each` cho edge đầu tiên bạn vẽ và `done` cho edge thứ hai. Nhánh `each` là
thân vòng lặp và phải quay về node For each. Mỗi lần ghé, node ghi phần tử kế
tiếp rồi đi theo `each`; sau phần tử cuối thì đi theo `done`.

![Vòng For each sau khi chạy](../images/loop-run.png)

Các phần tử chạy lần lượt, nên dừng ở Human, khôi phục và idempotency key đều
hoạt động theo từng phần tử. Gom kết quả vào một trường danh sách có reducer
`append`. Vòng lặp lồng nhau được; danh sách bên trong bắt đầu lại cho mỗi phần tử
bên ngoài. Các bước của vòng lặp không tính vào `STUDIO_RECURSION_LIMIT`, giới
hạn đó chỉ áp cho các vòng lặp khác.

## Human

`prompt` (template) và `output_field`. Run chờ ở trạng thái `waiting` tới khi
có người trả lời **Duyệt** (`approved`), **Từ chối** (`rejected`) hoặc nhập văn
bản tự do. Xem [Duyệt bởi người](../run/human-approval.md).

## Join

Chờ mọi nhánh đi vào, rồi chạy một lần. Cần ít nhất hai edge đi vào, và không
nhận edge đi thẳng từ Condition.

## Subgraph

`workflow_id` của một workflow đã lưu của bạn. State dùng chung theo tên
trường. Node bên trong hiện trong trace dạng `Subgraph › node` (id `sub/node`).
Vòng tham chiếu, workflow con không tồn tại hoặc là workflow import, và lồng
sâu quá năm cấp đều lỗi khi lưu và khi chạy (`WORKFLOW_INVALID`).

## Code (imported)

Node chỉ đọc sinh ra khi [import repo](../operate/import.md). Panel phải hiện
mã nguồn gốc. Sửa canvas không làm thay đổi file đã import.
