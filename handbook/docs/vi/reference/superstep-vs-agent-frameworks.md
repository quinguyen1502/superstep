# Superstep và CrewAI, PydanticAI

Trang này dành cho các nhóm muốn viết agent bằng code thay vì vẽ trong một
studio trực quan. CrewAI và PydanticAI là framework agent Python theo hướng code
trước, cùng loại với chính LangGraph. Superstep không phải framework: đó là một
studio chạy trên LangGraph. Workflow của Superstep được biên dịch thành
`StateGraph` của LangGraph và xuất được thành code LangGraph, nên so sánh công
bằng là **Superstep cộng LangGraph** với **CrewAI** hoặc **PydanticAI**. Thông
tin về các sản phẩm khác lấy từ tài liệu và file giấy phép của chính họ (liệt
kê ở mục [Nguồn](#nguon)), kiểm tra ngày 25/10/2026; hãy xem lại các trang đó
trước khi quyết định. Về các trình dựng trực quan, xem
[Superstep và n8n, Dify, Langflow, Flowise](superstep-vs-visual-builders.md).

## Tóm tắt mỗi sản phẩm

| Sản phẩm | Là gì |
| --- | --- |
| **Superstep + LangGraph** | Dựng workflow LangGraph trực quan trong Superstep (MIT), chạy chúng như dịch vụ, và xuất thành dự án LangGraph Python hoặc LangGraph.js khi muốn tiếp tục bằng code. |
| **CrewAI** | Framework Python mã nguồn mở cho hệ nhiều agent (Crew gồm các agent đóng vai, chạy trong Flow hướng sự kiện), kèm nền tảng thương mại CrewAI AMP thêm triển khai, tracing và Crew Studio không cần code. |
| **PydanticAI** | Framework agent Python có kiểu (typed) của đội Pydantic, đi kèm Pydantic Graph, Pydantic Evals, tích hợp durable execution và nền tảng quan sát Logfire. |

## Bảng so sánh tóm tắt

| | Superstep + LangGraph | CrewAI | PydanticAI |
| --- | --- | --- | --- |
| Cách dựng | Vẽ graph, hoặc viết code LangGraph; xuất code để chuyển từ cách này sang cách kia | Code Python (Flow và Crew); Crew Studio không cần code trong AMP | Code Python; đặc tả agent bằng YAML/JSON |
| Mô hình cốt lõi | Graph tường minh: node, cạnh, state có kiểu, checkpoint | Flow (state, sự kiện, rẽ nhánh) gọi các Crew gồm agent đóng vai | Vòng lặp agent có kiểu; Pydantic Graph cho luồng điều khiển dạng graph |
| Giấy phép | MIT (Superstep và LangGraph) | MIT (framework); AMP là thương mại | MIT |
| Human in the loop | Human node và interrupt của LangGraph; duyệt trong studio, Slack, Telegram, WhatsApp, email hoặc Teams | `@human_feedback` trong Flow; endpoint resume trong AMP | Duyệt lời gọi tool; chờ lâu nhờ engine durable |
| Chạy bền vững và du hành thời gian | Checkpoint trong database, job worker có lease; fork run đã xong từ một checkpoint | Lưu state Flow bằng `@persist`, khôi phục từ state đã lưu | Durable execution trên Temporal, DBOS, Prefect và các engine khác; step persistence để lưu, tiếp tục và fork |
| Test, eval, quan sát | Test workflow, eval LangSmith, trace OpenTelemetry | Tracing của AMP; nhiều tích hợp bên thứ ba | Pydantic Evals; OpenTelemetry gốc, Logfire |
| Chạy như dịch vụ | Có sẵn: token API, webhook, lịch, API công khai với SDK Python và TypeScript | Dịch vụ do bạn tự dựng, hoặc triển khai trên AMP có REST API | Dịch vụ do bạn tự dựng; stream sự kiện AG-UI và Vercel AI cho frontend |

## Superstep liên quan thế nào tới framework code trước

- **Cùng loại với LangGraph, không phải với Superstep.** CrewAI và PydanticAI
  cạnh tranh với LangGraph ở vai trò thư viện để viết agent. Superstep dùng
  LangGraph làm runtime và thêm trình soạn, lịch sử run, duyệt, test và API
  xung quanh.
- **Bạn có thể rời canvas.** Mọi workflow Superstep xuất được thành dự án
  LangGraph chạy được (xem [Xuất ra Python](../guide/python-export.md)), và
  [API tương thích LangGraph](../run/agent-server-api.md) cho phép client
  LangGraph gọi workflow vẫn nằm trong Superstep.
- **Code ở chỗ cần code.** Code node Python và TypeScript dành cho các bước
  viết dễ hơn vẽ.
- **Kết hợp được.** Một chương trình CrewAI hoặc PydanticAI có thể chạy
  workflow Superstep qua [API công khai và SDK](../run/public-api.md), và node
  HTTP hoặc MCP của Superstep có thể gọi agent bạn tự phục vụ.

## CrewAI

CrewAI là framework Python mã nguồn mở (MIT) cho hệ nhiều agent. **Flow** định
nghĩa cấu trúc: state, các bước hướng sự kiện, rẽ nhánh và vòng lặp; **Crew**
là nhóm agent đóng vai cùng làm một việc trong một bước của Flow. State của Flow
có thể được lưu bằng `@persist`, và `@human_feedback` (CrewAI 1.8.0 trở lên)
tạm dừng Flow để người duyệt, từ chối hoặc yêu cầu sửa. Quan sát qua tracing
của CrewAI trên AMP và các tích hợp như Langfuse, Arize Phoenix, MLflow, Opik
và Datadog. Tài liệu có hướng dẫn chuyển dự án từ LangGraph sang CrewAI.

CrewAI AMP (Agent Management Platform) là phần thương mại: triển khai crew lên
hạ tầng được quản lý từ GitHub, CLI hoặc **Crew Studio** (giao diện không
code/ít code), gọi qua REST API, stream sự kiện qua webhook và theo dõi trace.

Điểm mạnh của CrewAI: nhiều agent cộng tác theo vai trò với ít code, và có
đường lên production được quản lý.

## PydanticAI

PydanticAI là framework agent Python của đội Pydantic (MIT): agent có kiểu,
output có cấu trúc được Pydantic kiểm tra, dependency injection và tool có
kiểu, nhiều nhà cung cấp model đổi bằng một chuỗi. Đi kèm: Pydantic Graph cho
luồng điều khiển dạng graph có kiểu, Pydantic Evals để chấm output và chuỗi lời
gọi tool, durable execution trên các engine như Temporal, DBOS và Prefect (có
duyệt lời gọi tool), step persistence để lưu, tiếp tục và fork một run, và
instrumentation theo chuẩn OpenTelemetry. Pydantic Logfire là nền tảng quan sát
của công ty (có gói miễn phí); dùng backend OpenTelemetry nào khác cũng được.

Điểm mạnh của PydanticAI: an toàn kiểu và dễ test cho lập trình viên, hỗ trợ
nhiều model, và chạy bền vững trên engine bạn đang vận hành.

## Khi nào nên chọn framework

- Chọn **CrewAI** khi nhóm viết Python và bài toán hợp với các agent tự chủ
  cộng tác theo vai trò, có thể kèm nền tảng được quản lý.
- Chọn **PydanticAI** khi lập trình viên muốn thư viện agent có kiểu, code
  trước, mạnh về test, eval và durable execution, và không cần trình soạn trực
  quan.
- Chọn **LangGraph thuần** khi bạn muốn LangGraph bằng code mà không cần
  studio; bản xuất từ Superstep là điểm khởi đầu.
- Chọn **Superstep** khi người không lập trình cũng cần đọc và sửa được
  workflow, mọi nhánh và bước duyệt cần tường minh và review được, bạn muốn có
  sẵn run, duyệt, test và API mà không phải tự dựng, hoặc muốn giao diện tiếng
  Việt, trong khi vẫn giữ đường chuyển sang code LangGraph.

## Nguồn

- [Giấy phép LangGraph](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)
- [Giới thiệu CrewAI](https://docs.crewai.com/en/introduction)
- [CrewAI: Human feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)
- [CrewAI AMP](https://docs-platform.crewai.com/platform/en/introduction)
- [Giấy phép CrewAI](https://github.com/crewAIInc/crewAI/blob/main/LICENSE)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Giấy phép Pydantic AI](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)
