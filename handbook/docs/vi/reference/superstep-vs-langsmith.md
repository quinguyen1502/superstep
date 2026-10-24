# Superstep và LangSmith

Superstep và LangSmith đều làm việc với agent LangGraph, nhưng giải quyết những
bài toán khác nhau và dùng chung với nhau rất tốt. Trang này so sánh hai bên
theo mục đích mà mỗi sản phẩm được xây dựng, để bạn chọn đúng công cụ hoặc kết
hợp cả hai. Thông tin về LangSmith lấy từ chính các trang của LangChain (liệt kê
ở mục [Nguồn](#nguon)), kiểm tra ngày 24/10/2026; giá và gói có thể thay đổi,
nên hãy xem lại các trang đó trước khi quyết định.

## Tóm tắt mỗi sản phẩm

| Sản phẩm | Là gì |
| --- | --- |
| **Superstep** | Công cụ dựng workflow kiểu LangGraph trực quan, tự host (giấy phép MIT), có xuất code, kênh human-in-the-loop và giao diện tiếng Việt. |
| **LangSmith Studio** | IDE cho agent viết bằng code của LangChain: hiển thị, chạy và debug graph theo Agent Server API, kèm tracing, đánh giá (eval) sâu và triển khai được quản lý. |
| **LangSmith Agent Builder** | Cách dựng agent không cần code của LangChain: mô tả mục tiêu bằng lời, nó tự lên hướng dẫn, chọn tool và subagent. |

## Superstep

- **Trực quan trước tiên.** Graph được vẽ trên canvas: node, cạnh, state schema
  có kiểu, vòng lặp, nhánh song song và subgraph. Người chỉnh sửa không cần
  viết code; khi cần thì có node Code.
- **Tự host và mã nguồn mở.** Giấy phép MIT. Chạy bằng Docker Compose hoặc trên
  PaaS trong hạ tầng của bạn; dữ liệu nằm ở đó.
- **Xuất code.** Mọi workflow xuất được thành file LangGraph Python hoặc
  LangGraph.js (xem [Xuất ra Python](../guide/python-export.md)).
- **Human in the loop ngay nơi mọi người đang làm việc.** Node Human tạm dừng run
  và hỏi câu trả lời qua Slack, WhatsApp, hộp duyệt hoặc web chat (xem
  [Duyệt bởi người](../run/human-approval.md) và [Chat](../run/chat.md)).
- **Giao diện và tài liệu tiếng Việt và tiếng Anh.**
- **Công cụ chạy có sẵn.** Chạy từng bước, lịch sử run, kiểm thử workflow với
  điều kiện kiểm tra (xem [Kiểm thử workflow](../run/tests.md)) và trace
  OpenTelemetry.

## LangSmith Studio

Theo tài liệu của Studio, Studio là "a specialized agent IDE" (một IDE chuyên
cho agent) dành cho các agent theo giao thức Agent Server API, tích hợp tracing,
đánh giá và prompt engineering. Các tính năng được liệt kê gồm hiển thị graph,
chạy và tương tác với agent, quản lý assistant và thread, chỉnh prompt, chạy
experiment trên một dataset, quản lý bộ nhớ dài hạn, debug state bằng time
travel và triển khai một cú nhấp lên LangSmith Cloud. Studio làm việc với graph
đã triển khai trên LangSmith hoặc chạy cục bộ qua Agent Server (ví dụ
`langgraph dev`), và có chế độ graph và chế độ chat.

Điểm mạnh của LangSmith:

- **Tracing và đánh giá chuyên sâu.** LangSmith là nền tảng quan sát và đánh
  giá của LangChain; dataset, experiment, feedback và chỉnh prompt là tính năng
  cốt lõi.
- **Triển khai được quản lý.** Gói Plus có LangSmith Deployment (một deployment
  serverless nhỏ miễn phí), dùng thêm thì tính theo mức sử dụng.
- **Toàn quyền bằng code.** Graph là code Python hoặc JavaScript của chính bạn.

## LangSmith Agent Builder

LangChain công bố Agent Builder chính thức phát hành (GA) ngày 13/01/2026. Đây
là sản phẩm không cần code: bạn mô tả mục tiêu bằng lời của mình, nó viết
hướng dẫn, chọn tool và thêm subagent khi cần. Agent học từ phản hồi qua bộ
nhớ, có thể xin phép trước các thao tác nhạy cảm, chia sẻ và sao chép được
trong workspace, kết nối tool qua máy chủ MCP từ xa và gọi được qua API. Bài
công bố cho biết nó có trên mọi gói LangSmith. Trên trang giá hiện tại, sản
phẩm không cần code để dựng agent "using everyday language, not code" được
liệt kê với tên **LangSmith Fleet**.

Agent Builder và Superstep đều là cách dựng agent không cần viết code, theo hai
hướng khác nhau: Agent Builder để agent tự lên các bước từ mục tiêu; Superstep
để bạn vẽ các bước, nên mọi đường đi, nhánh và bước duyệt đều rõ ràng và xem
lại được.

## Giá và hosting

| | Superstep | LangSmith (Studio, Deployment, Agent Builder) |
| --- | --- | --- |
| Giấy phép | MIT, mã nguồn mở | Dịch vụ thương mại |
| Giá | Miễn phí; bạn trả tiền máy chủ và API model của mình | Developer $0 (1 seat, gồm 5k base trace mỗi tháng), Plus $39 mỗi seat mỗi tháng (gồm 10k base trace mỗi tháng), Enterprise giá riêng; dùng vượt mức thì trả theo mức sử dụng |
| Tự host | Có, luôn luôn | Chỉ gói Enterprise (tự host và hybrid); Developer và Plus chỉ chạy trên cloud |
| Nơi lưu dữ liệu | Hạ tầng của bạn | Cloud của LangChain (Mỹ hoặc EU), hoặc VPC của bạn với Enterprise tự host |

Trang tổng quan về tự host LangSmith ghi rằng "Self-hosted deployments require
an Enterprise plan and the LangSmith license key delivered with that plan" (tự
host cần gói Enterprise và license key đi kèm gói đó), với ba mô hình: toàn bộ
nền tảng, hybrid và Agent Server độc lập.

## Dùng cùng nhau

Superstep nói "ngôn ngữ" LangGraph, nên bạn không phải chọn một bên:

| Tính năng | Mang lại gì |
| --- | --- |
| **Xuất dự án LangGraph chạy được** | Tải workflow về thành dự án có `langgraph.json`, dependency và `.env.example`; `langgraph dev` phục vụ được nó, nên bạn có thể mở trong LangSmith Studio hoặc triển khai lên LangSmith. |
| **API tương thích LangGraph** | Một phần Agent Server API (assistant, thread, run, streaming, interrupt) tại `/api/lg`, để client `langgraph-sdk` chính thức và `RemoteGraph` chạy được workflow Superstep. |
| **Eval và link trace LangSmith** | Khi có API key LangSmith, các run test workflow được gửi sang LangSmith thành dataset và experiment, và run được trace sang LangSmith có link tới trace của nó. |
| **Du hành thời gian** | Xem các checkpoint của một run trong bảng Run, sửa state và fork một run mới từ đó, như Studio làm với graph viết bằng code. |

Một cách dùng phổ biến: người dùng nghiệp vụ và người duyệt dựng và duyệt
workflow trong Superstep, lập trình viên xuất chúng thành dự án LangGraph khi
cần code tuỳ biến, và cả nhóm dùng LangSmith để tracing và đánh giá cho cả hai.

## Nên chọn gì

- Chọn **Superstep** khi bạn cần tự host mà không cần hợp đồng Enterprise, một
  trình chỉnh sửa trực quan cho người không lập trình, bước duyệt qua Slack,
  WhatsApp hoặc web chat, giao diện tiếng Việt, hoặc giấy phép mã nguồn mở.
- Chọn **LangSmith Studio** khi agent được viết bằng code và bạn muốn tracing,
  đánh giá và triển khai được quản lý của LangChain ở cùng một nơi.
- Chọn **LangSmith Agent Builder** khi bạn muốn agent tự lên các bước từ mục
  tiêu viết bằng lời, do LangChain host.

## Nguồn

- [LangSmith Studio](https://docs.langchain.com/langsmith/studio)
- [Bảng giá LangSmith](https://www.langchain.com/pricing)
- [Deploy to self-hosted](https://docs.langchain.com/langsmith/deploy-to-self-hosted-overview)
- [Now GA: LangSmith Agent Builder](https://www.langchain.com/blog/langsmith-agent-builder-generally-available)
