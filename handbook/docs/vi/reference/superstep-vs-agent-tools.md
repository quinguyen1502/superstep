# Superstep và n8n, Dify, CrewAI, PydanticAI

Khi chọn công cụ cho workflow AI, nhiều nhóm xem n8n, Dify, CrewAI và
PydanticAI bên cạnh Superstep. Các công cụ này có phần giống nhau, nhưng mỗi
cái được xây dựng quanh một ý tưởng khác: n8n là nền tảng tự động hóa tổng
quát, Dify là nền tảng ứng dụng LLM, CrewAI và PydanticAI là framework Python.
Trang này so sánh công bằng để bạn chọn đúng công cụ hoặc kết hợp chúng. Thông
tin về các sản phẩm khác lấy từ tài liệu, trang web và file giấy phép của chính
họ (liệt kê ở mục [Nguồn](#nguon)), kiểm tra ngày 25/10/2026; tính năng, gói và
giấy phép có thể thay đổi, nên hãy xem lại các trang đó trước khi quyết định.
Về LangSmith, xem [Superstep và LangSmith](superstep-vs-langsmith.md).

## Tóm tắt mỗi sản phẩm

| Sản phẩm | Là gì |
| --- | --- |
| **Superstep** | Studio trực quan, tự host cho workflow LangGraph (giấy phép MIT), có xuất code, API tương thích LangGraph, kênh human-in-the-loop và giao diện tiếng Việt. |
| **n8n** | Nền tảng tự động hóa workflow với trình soạn trực quan, thư viện tích hợp ứng dụng lớn và các node AI (agent, tool, memory) dựa trên khái niệm của LangChain. |
| **Dify** | Nền tảng mã nguồn mở để dựng ứng dụng LLM: agent, workflow có agent và chatbot trên dữ liệu của bạn, xuất bản thành web app, API hoặc MCP server. |
| **CrewAI** | Framework Python mã nguồn mở cho hệ nhiều agent (Crew gồm các agent đóng vai, chạy trong Flow hướng sự kiện), kèm nền tảng thương mại CrewAI AMP thêm triển khai, tracing và Crew Studio không cần code. |
| **PydanticAI** | Framework agent Python có kiểu (typed) của đội Pydantic, đi kèm Pydantic Graph, Pydantic Evals, tích hợp durable execution và nền tảng quan sát Logfire. |

## Bảng so sánh tóm tắt

| | Superstep | n8n | Dify | CrewAI | PydanticAI |
| --- | --- | --- | --- | --- | --- |
| Cách tiếp cận chính | Trình soạn graph trực quan; Code node tùy chọn | Trình soạn workflow trực quan; Code node tùy chọn | Trình dựng ứng dụng và workflow trực quan | Code Python; Crew Studio không cần code trong AMP | Code Python; đặc tả agent bằng YAML/JSON |
| Chạy trên LangGraph | Có: workflow được biên dịch thành `StateGraph` của LangGraph | Không; node AI theo khái niệm của LangChain | Không | Không (tài liệu có hướng dẫn chuyển từ LangGraph sang) | Không (có Pydantic Graph riêng) |
| Giấy phép | MIT | Sustainable Use License (công khai mã nguồn, giới hạn ở dùng nội bộ và phi thương mại); file enterprise theo giấy phép riêng | Apache 2.0 có sửa đổi (không vận hành dịch vụ nhiều tenant khi chưa được phép; giữ logo và bản quyền ở frontend) | MIT (framework); AMP là thương mại | MIT |
| Tự host | Có, miễn phí | Có, bản Community miễn phí; có gói enterprise trả phí | Có, Community Edition với Docker Compose | Framework chạy ở đâu cũng được; AMP là nền tảng được quản lý | Thư viện chạy ở đâu cũng được; Logfire là dịch vụ host sẵn có gói miễn phí |
| Human in the loop | Human node: duyệt trong studio, Slack, Telegram, WhatsApp, email hoặc Teams, có hạn chót | Duyệt lời gọi tool của AI Agent; duyệt qua Slack bằng "send and wait" | Node Human Input tạm dừng workflow | `@human_feedback` trong Flow; endpoint resume trong AMP | Duyệt lời gọi tool; chờ lâu nhờ engine durable |
| Chạy bền vững và du hành thời gian | Checkpoint trong database, job worker có lease, fork run đã xong từ một checkpoint | Queue mode với worker | Nguồn không đề cập | Lưu state Flow bằng `@persist`, khôi phục từ state đã lưu | Durable execution trên Temporal, DBOS, Prefect và các engine khác; step persistence để lưu, tiếp tục và fork |
| Test, eval, quan sát | Test workflow, eval LangSmith, trace OpenTelemetry | Evaluations (test case, metric); OpenTelemetry khi tự host | Log, dashboard, annotation; tích hợp LangSmith, Langfuse, Opik, Phoenix và khác | Tracing của AMP; nhiều tích hợp bên thứ ba | Pydantic Evals; OpenTelemetry gốc, Logfire |
| API và SDK | API chạy công khai, SDK Python `superstep` và TypeScript `@superstep/sdk`, một phần Agent Server API tại `/api/lg` | REST API và webhook | REST API, CLI `difyctl`, xuất bản MCP server | Thư viện Python; REST API của AMP | Thư viện Python; stream AG-UI và Vercel AI |
| Xuất code | Dự án LangGraph Python hoặc LangGraph.js chạy được | Không | Không | Không áp dụng (code trước) | Không áp dụng (code trước) |

## Superstep

- **LangGraph trực quan.** Graph được vẽ trên canvas (13 loại node, state có
  kiểu với reducer, vòng lặp, nhánh song song, subgraph, Human node) và biên
  dịch thành `StateGraph` của LangGraph. Code node Python và TypeScript chạy
  trong sandbox Docker khóa chặt (trên host khi dùng nền tảng được quản lý) khi
  bạn cần code. Xem [Node](../guide/nodes.md).
- **Xuất code và tương thích LangGraph.** Mọi workflow xuất được thành dự án
  LangGraph chạy được (`langgraph.json`, chạy bằng `langgraph dev`, xem
  [Xuất ra Python](../guide/python-export.md)), và một phần Agent Server API
  tại `/api/lg` cho phép client `langgraph-sdk` chính thức chạy workflow (xem
  [API tương thích LangGraph](../run/agent-server-api.md)).
- **Human in the loop ở nơi mọi người đang làm việc.** Human node tạm dừng run
  từ một checkpoint; duyệt trong studio, Slack, Telegram, WhatsApp, email hoặc
  Teams, có nhắc nhở, chuyển cấp và hết hạn (xem
  [Duyệt bởi người](../run/human-approval.md)).
- **Độ tin cậy và debug.** Checkpoint trong database, job worker có lease, tác
  dụng phụ effectively-once, chạy từng bước và du hành thời gian: xem các
  checkpoint của run đã xong, sửa state và fork một run mới.
- **Test và trace.** Test workflow có kiểm tra (xem
  [Test workflow](../run/tests.md)), tùy chọn dataset và experiment trên
  LangSmith, trace OpenTelemetry (xem [Trace](../run/traces.md)).
- **Chạy như dịch vụ, không chỉ là studio.** Token API, webhook có ký, lịch
  cron, trigger qua chat, và API công khai với SDK Python và TypeScript (xem
  [API công khai và SDK](../run/public-api.md)).
- **Tự host, MIT.** Mặc định SQLite hoặc Postgres với pgvector, Redis và worker
  tùy chọn, image Docker trên GHCR và triển khai một chạm lên PaaS (xem
  [Triển khai](../operate/deploy.md)). Giao diện và handbook tiếng Việt và
  tiếng Anh.

Những gì Superstep không cố trở thành: số tích hợp ứng dụng ít hơn nhiều so với
n8n hay Dify (kết nối qua HTTP, MCP server, email và các kênh chat), không có
dịch vụ cloud host sẵn và không có marketplace.

## n8n

n8n là nền tảng tự động hóa workflow: trình soạn trực quan nối các ứng dụng và
dịch vụ qua node tích hợp, trigger và logic luồng, có code khi cần. Phần AI cho
phép nối các nhà cung cấp LLM, thêm agent, tool, memory, vector store và MCP
server, và mô tả cách n8n hiện thực các khái niệm của LangChain. Tool của AI
Agent có thể yêu cầu người duyệt (workflow tạm dừng và gửi yêu cầu tới Slack,
Telegram hoặc n8n Chat), và Evaluations kiểm tra workflow AI bằng test case và
metric. n8n chạy dưới dạng n8n Cloud hoặc tự host (npm, Docker, Docker Compose,
nhà cung cấp cloud), có queue mode để mở rộng.

Giấy phép của n8n là Sustainable Use License: bạn chỉ được dùng hoặc sửa phần
mềm "only for your own internal business purposes or for non-commercial or
personal use", và các file đánh dấu `.ee` cần giấy phép n8n Enterprise. Đây là
mã nguồn công khai (source-available), không phải giấy phép mã nguồn mở theo
OSI.

Điểm mạnh của n8n: rất nhiều tích hợp và trigger có sẵn, tự động hóa nghiệp vụ
trưởng thành và thư viện mẫu.

## Dify

Dify là nền tảng mã nguồn mở để dựng ứng dụng AI: agent, workflow có agent và
chatbot dùng dữ liệu của bạn (knowledge base có truy xuất), xuất bản thành web
app, nhúng, REST API hoặc MCP server. Workflow có các node như LLM, truy xuất
knowledge, HTTP request, tool và Human Input (tạm dừng workflow để hỏi người).
Plugin bổ sung model, tool và trigger, và Marketplace để chia sẻ chúng. Giám sát
gồm log, dashboard, annotation và tích hợp LangSmith, Langfuse, Opik, W&B Weave,
Arize và Phoenix. Dify chạy trên Dify Cloud hoặc bản Community Edition tự host
với Docker Compose.

Giấy phép là Apache 2.0 kèm điều kiện: vận hành môi trường nhiều tenant (mỗi
tenant là một workspace) cần được cho phép bằng văn bản, và phải giữ logo và
thông tin bản quyền trong console và ứng dụng.

Điểm mạnh của Dify: nền tảng ứng dụng LLM trọn gói với RAG, nhiều nhà cung cấp
model, giao diện ứng dụng có sẵn và hệ sinh thái plugin.

## CrewAI

CrewAI là framework Python mã nguồn mở (MIT) cho hệ nhiều agent. **Flow** định
nghĩa cấu trúc: state, các bước hướng sự kiện, rẽ nhánh và vòng lặp; **Crew**
là nhóm agent đóng vai cùng làm một việc trong một bước của Flow. State của Flow
có thể được lưu bằng `@persist`, và `@human_feedback` (CrewAI 1.8.0 trở lên)
tạm dừng Flow để người duyệt, từ chối hoặc yêu cầu sửa. Quan sát qua tracing
của CrewAI trên AMP và các tích hợp như Langfuse, Arize Phoenix, MLflow, Opik
và Datadog.

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

## Dùng cùng nhau

- **Gọi Superstep từ bất cứ đâu.** n8n, Dify (node HTTP request) hay một chương
  trình CrewAI hoặc PydanticAI có thể chạy workflow Superstep qua API công khai
  hoặc SDK, ví dụ để đặt một bước đã được review và có duyệt bởi người vào một
  quy trình tự động lớn hơn.
- **Gọi chúng từ Superstep.** Node HTTP và MCP có thể gọi webhook của n8n, API
  ứng dụng Dify hoặc agent bạn tự phục vụ.
- **Chuyển sang code.** Khi workflow trực quan vượt quá canvas, xuất nó thành
  dự án LangGraph và tiếp tục bằng code.

## Khi nào nên chọn công cụ khác

- Chọn **n8n** khi việc chủ yếu là nối các ứng dụng nghiệp vụ (CRM, bảng tính,
  nhắn tin) kèm vài bước AI, bạn cần thư viện tích hợp có sẵn lớn, và
  Sustainable Use License phù hợp cách bạn dùng.
- Chọn **Dify** khi bạn muốn nền tảng ứng dụng LLM trọn gói với knowledge base,
  giao diện chat có sẵn, marketplace plugin và cloud host sẵn, và các điều kiện
  giấy phép (không dịch vụ nhiều tenant, giữ thương hiệu) phù hợp.
- Chọn **CrewAI** khi nhóm viết Python và bài toán hợp với các agent tự chủ
  cộng tác theo vai trò, có thể kèm nền tảng được quản lý.
- Chọn **PydanticAI** khi lập trình viên muốn thư viện agent có kiểu, code
  trước, mạnh về test, eval và durable execution, và không cần trình soạn trực
  quan.
- Chọn **Superstep** khi bạn muốn LangGraph bên dưới (có xuất code và API tương
  thích LangGraph), trình soạn trực quan mà người không lập trình cũng review
  được, duyệt rõ ràng qua Slack, Telegram, WhatsApp, email hoặc Teams, giấy
  phép MIT và tự host không cần hợp đồng, hoặc giao diện tiếng Việt.

## Nguồn

- [n8n: Integrate AI](https://docs.n8n.io/advanced-ai/)
- [n8n: Human-in-the-loop for tools](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools/)
- [n8n: Choose how to use n8n](https://docs.n8n.io/choose-how-to-use-n8n/)
- [Giấy phép n8n](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Tài liệu Dify](https://docs.dify.ai/en/introduction)
- [Dify: Human Input node](https://docs.dify.ai/en/self-host/use-dify/nodes/human-input)
- [Giấy phép Dify](https://github.com/langgenius/dify/blob/main/LICENSE)
- [Giới thiệu CrewAI](https://docs.crewai.com/en/introduction)
- [CrewAI: Human feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)
- [CrewAI AMP](https://docs-platform.crewai.com/platform/en/introduction)
- [Giấy phép CrewAI](https://github.com/crewAIInc/crewAI/blob/main/LICENSE)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Giấy phép Pydantic AI](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)
