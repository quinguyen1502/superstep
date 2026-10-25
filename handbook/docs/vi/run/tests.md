# Kiểm thử workflow

Tab **Test** trong trình soạn thảo lưu các test case của workflow: input, câu
trả lời cho các node Human, và những gì run phải cho ra. Chạy chúng sau mỗi lần
sửa để biết cái gì vẫn chạy đúng và thay đổi nào làm hỏng.

![Tab Test sau khi Chạy tất cả](../images/tests.png)

## Trước khi bắt đầu

- Cần quyền sửa workflow để thêm, sửa và chạy test. Người xem thấy được các
  test case và kết quả.
- Worker đang chạy: mỗi test case được đưa vào hàng đợi như một run.
- Test chạy trên một phiên bản đã lưu. Lưu trước để test thay đổi mới nhất.
- Repo LangGraph đã import không có tab Test.

## Test case

**Thêm test case** mở trình soạn của một test case.

![Một test case](../images/test-case.png)

| Phần | Nội dung |
| --- | --- |
| Tên | Test case nói về gì, ví dụ "Từ chối nghỉ phép". |
| Input | Input của run, dạng JSON. |
| Câu trả lời cho Human node | Với mỗi node Human, các câu trả lời theo thứ tự: Duyệt, Từ chối hoặc trả lời bằng chữ. Node chờ thêm lần nữa, ví dụ sau khi viết lại, sẽ nhận câu kế tiếp. Node Agent có công cụ cần duyệt cũng được liệt kê: mỗi lần gọi một câu trả lời. |
| Điều kiện | Những gì run phải cho ra. Tất cả phải đạt. |

| Điều kiện | Đạt khi |
| --- | --- |
| Trạng thái run | Run kết thúc `ok`, `error` hoặc `waiting`, như đã chọn. Không có điều kiện trạng thái thì run phải kết thúc `ok`. |
| Trường state | Một trường bằng, chứa, không chứa hoặc khớp mẫu (biểu thức chính quy), hoặc rỗng hay không rỗng. Object và danh sách so sánh dạng JSON. |
| Node | Một node có chạy, hoặc không chạy. |
| Gọi công cụ | Một [node Agent](../guide/agent.md) đã gọi, hoặc không gọi, một công cụ. Lần gọi được tính khi nó đã chạy, kể cả khi công cụ bị lỗi; lần gọi bị từ chối, bị refused hoặc có tham số sai thì không tính. |
| Thời gian | Run chạy không quá số giây này. |
| Chi phí | Run tốn không quá số US$ này. Không kiểm khi model chưa có giá. |

Mỗi workflow có tối đa 50 test case (`STUDIO_TEST_CASES_MAX`), mỗi test case tối
đa 30 điều kiện và 20 câu trả lời cho mỗi node Human.

## Chạy test

- **Chạy tất cả** chạy mọi test case trên phiên bản đã lưu hiện tại; nút chạy trên
  một test case chỉ chạy test case đó.
- Tối đa 4 test case chạy cùng lúc (`STUDIO_TEST_PARALLEL`). Mỗi workflow chỉ có
  một run test tại một thời điểm; **Huỷ** để dừng.
- **Dùng model mock offline** chạy mọi node LLM, Agent và Decision bằng mock offline:
  không gọi model, không tốn tiền, lần nào cũng ra cùng câu trả lời. Khi tắt,
  test dùng model thật và credential của chúng.
- Mỗi test case hiện đạt hay không đạt, mỗi điều kiện hiện giá trị mong đợi và
  thực tế. **Mở run** mở trace của run test.
- Khi một node Human chờ mà test case không còn câu trả lời cho nó, test case
  không đạt và ghi rõ node nào đang chờ.

Run test không hiện trong lịch sử run (**Chạy → Xem tất cả**). Bật **Run test** ở đó để xem chúng.

## Run test không gửi gì

Run test là một run bình thường của workflow, cùng node, giới hạn và trace, nên
test kiểm đúng những gì run thật làm. Chỉ những gì tới tay người khác bị tắt:

| Không | Thay vào đó |
| --- | --- |
| Gửi email | Node Send email chạy thử: output cho thấy thư lẽ ra sẽ gửi. |
| Gửi yêu cầu duyệt tới kênh, hay thêm bước vào hộp thư Duyệt | Câu trả lời của test case tiếp tục run. |
| Gửi thông báo | — |
| Gọi API callback | — |

Node Tool, HTTP, MCP, Code và Retriever, cùng các công cụ của node Agent, vẫn
chạy thật. Hãy trỏ chúng tới hệ thống thử nghiệm khi chúng thay đổi dữ liệu.

## So sánh với phiên bản trước

Mỗi kết quả được so với run test gần nhất đã xong trên một phiên bản cũ hơn.
Thanh phía trên danh sách hiện số lượng và phiên bản đó; mỗi test case có nhãn
của nó.

![Một test mới lỗi so với phiên bản 1](../images/tests-compare.png)

| Nhãn | Nghĩa |
| --- | --- |
| Mới lỗi | Trước đạt, giờ không đạt. |
| Đã sửa | Trước không đạt, giờ đạt. |
| Vẫn lỗi / Vẫn đạt | Không đổi. |
| Mới | Chưa có kết quả trước, ví dụ test case mới thêm. |

Sửa test case không làm mất lịch sử của nó. Khi chưa có kết quả trước, thanh sẽ
báo như vậy: **Chạy trên phiên bản** chạy test trên một phiên bản cũ đã lưu để
có kết quả so sánh. **Lịch sử test** liệt kê các run test gần đây (phiên bản, ai chạy, lúc
nào, số đạt và không đạt) và mở lại được.

## Lưu một run thành test case

Một run chạy đúng là một test tốt. **Lưu thành test case** trên một run trong
lịch sử run (**Xem tất cả**), hoặc trên thanh trace của run, mở một test case mới với:

- input của run;
- các câu trả lời đã đưa cho node Human, theo thứ tự;
- các điều kiện run đó đạt: trạng thái, từng node đã chạy (trừ Start và End),
  và từng trường nó ghi. Giá trị dài hơn 200 ký tự được kiểm bằng "chứa" 200 ký
  tự đầu.

Bỏ những gì không cần rồi lưu.

## Điều kiện không còn khớp graph

Điều kiện nhắc tới node hoặc trường state mà graph không còn có được đánh dấu
**Không còn trong graph**, và không đạt với lý do đó khi chạy. Sửa hoặc bỏ
điều kiện đó. Điều kiện **Gọi công cụ** nhắc tới công cụ mà node Agent không còn
có cũng được đánh dấu như vậy.

## Mẫu có sẵn

Mỗi mẫu có sẵn đi kèm một đến ba test case, và workflow tạo từ mẫu có một bản
sao (xem [Mẫu workflow](../guide/templates.md)). Chúng đạt với model mock
offline. **Hỏi đáp RAG**, **Hỗ trợ có chuyển cấp** và **Agent hỗ trợ khách hàng**
cần chọn kho tri thức trước.
Mẫu bạn tự lưu không kèm test case.

## Gửi kết quả sang LangSmith

Khi máy chủ có `LANGSMITH_API_KEY` (và `LANGSMITH_ENDPOINT` nếu LangSmith tự
host), admin có thể bật **Cài đặt > Người dùng > LangSmith > Gửi kết quả kiểm
thử sang LangSmith**. Mỗi run test đã xong sẽ được gửi ở chế độ nền:

- các test case của workflow thành một dataset LangSmith tên
  `Superstep: <workflow> (<id>)`, mỗi case một example (input, điều kiện,
  câu trả lời soạn sẵn), được đồng bộ ở mỗi lần gửi;
- run test thành một experiment trên dataset đó, mỗi case một run (state cuối
  làm output) và feedback `passed` cùng một điểm cho mỗi điều kiện.

Khi đó bảng Kiểm thử có menu **LangSmith**: **Mở trong LangSmith** mở experiment,
và editor có thể chọn **Gửi sang LangSmith** để gửi lại một run test (một
experiment mới). Gửi lỗi chỉ được ghi
log, không làm thay đổi kết quả test.

Khi các run cũng được trace sang LangSmith (`LANGSMITH_TRACING=true`, xem
[Quan sát hệ thống](../operate/observability.md)), link **Mở trace** của mỗi run
mở trace của nó trong LangSmith, trừ khi đã đặt `STUDIO_TRACE_URL`.

## API

```text
GET|POST    /api/workflows/{wid}/tests
PUT|DELETE  /api/workflows/{wid}/tests/{tid}
POST        /api/workflows/{wid}/tests/run              {test_ids?, mock?, version?}
GET         /api/workflows/{wid}/tests/runs             (lịch sử)
GET         /api/workflows/{wid}/tests/runs/{sid}       (kết quả và so sánh)
POST        /api/workflows/{wid}/tests/runs/{sid}/cancel
POST        /api/workflows/{wid}/tests/runs/{sid}/langsmith   (gửi lại sang LangSmith)
POST        /api/workflows/{wid}/tests/from-run/{run_id}   (bản nháp, chưa lưu)
```
