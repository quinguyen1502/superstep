# Superstep và n8n, Dify, Langflow, Flowise

n8n, Dify, Langflow và Flowise là những lựa chọn gần Superstep nhất: giống
Superstep, chúng cho phép dựng workflow AI trên canvas trực quan thay vì viết
code. Chúng khác nhau ở thứ nằm dưới canvas, ở giấy phép và ở cách run tạm
dừng, tiếp tục và được trace. Trang này so sánh công bằng để bạn chọn đúng công
cụ. Thông tin về các sản phẩm khác lấy từ tài liệu và file giấy phép của chính
họ (liệt kê ở mục [Nguồn](#nguon)), kiểm tra ngày 25/10/2026; tính năng, gói và
giấy phép có thể thay đổi, nên hãy xem lại các trang đó trước khi quyết định.
Nếu bạn muốn viết agent bằng code, xem
[Superstep và CrewAI, PydanticAI](superstep-vs-agent-frameworks.md); về
LangSmith, xem [Superstep và LangSmith](superstep-vs-langsmith.md).

## Tóm tắt mỗi sản phẩm

| Sản phẩm | Là gì |
| --- | --- |
| **Superstep** | Studio trực quan, tự host cho workflow LangGraph (giấy phép MIT), có xuất code, API tương thích LangGraph, kênh human-in-the-loop và giao diện tiếng Việt. |
| **n8n** | Nền tảng tự động hóa workflow với trình soạn trực quan, thư viện tích hợp ứng dụng lớn và các node AI (agent, tool, memory) dựa trên khái niệm của LangChain. |
| **Dify** | Nền tảng mã nguồn mở cho ứng dụng LLM: agent, workflow có agent và chatbot trên dữ liệu của bạn, xuất bản thành web app, API hoặc MCP server. |
| **Langflow** | Nền tảng low-code mã nguồn mở (MIT) để dựng và triển khai agent và workflow AI với trình dựng trực quan, API và MCP server. |
| **Flowise** | Trình dựng trực quan mã nguồn mở cho agent AI và luồng LLM (Chatflow và Agentflow), tự host hoặc dùng Flowise Cloud. |

## Bảng so sánh tóm tắt

Thứ chạy workflow, giấy phép và nơi chạy:

| Sản phẩm | Dưới canvas | Giấy phép | Hosting |
| --- | --- | --- | --- |
| Superstep | Biên dịch thành `StateGraph` của LangGraph | MIT | Tự host (Docker, PaaS); miễn phí |
| n8n | Engine riêng của n8n; node AI theo khái niệm của LangChain | Sustainable Use License (công khai mã nguồn; giới hạn ở dùng nội bộ và phi thương mại); file `.ee` cần giấy phép Enterprise | n8n Cloud hoặc bản Community tự host; có gói enterprise trả phí |
| Dify | Engine workflow riêng của Dify | Apache 2.0 kèm điều kiện (không vận hành dịch vụ nhiều tenant khi chưa được phép; giữ logo và bản quyền) | Dify Cloud hoặc Community Edition tự host (Docker Compose) |
| Langflow | Component của Langflow; component LangChain là bundle tùy chọn | MIT | Tự host (Docker, Kubernetes, nền tảng cloud) hoặc Langflow Desktop |
| Flowise | Agentflow V2: node gốc của Flowise; Multi-Agents và Sequential Agents của Agentflow V1 cũ dựa trên LangGraph | Apache 2.0, trừ thư mục enterprise và các file có thông báo riêng | Flowise Cloud hoặc tự host (npm, Docker, hướng dẫn cho các cloud) |

Cách run tạm dừng, tiếp tục và được kiểm tra:

| Sản phẩm | Human in the loop | Chạy bền vững | Test, eval, quan sát |
| --- | --- | --- | --- |
| Superstep | Human node, và duyệt trước khi node Agent gọi công cụ; duyệt trong studio, Slack, Telegram, WhatsApp, email hoặc Teams, có hạn chót | Checkpoint trong database (SQLite hoặc Postgres): run đang dừng và run trong hàng đợi đang chạy tiếp tục sau khi khởi động lại hay worker sập; du hành thời gian: fork run đã xong từ một checkpoint | Test workflow, eval LangSmith, trace OpenTelemetry |
| n8n | Duyệt lời gọi tool của AI Agent; duyệt qua Slack bằng "send and wait" | Queue mode với worker | Evaluations (test case, metric); OpenTelemetry khi tự host |
| Dify | Node Human Input | Nguồn không đề cập | Log, dashboard, annotation; LangSmith, Langfuse, Opik, Phoenix và khác |
| Langflow | Component Human Input; duyệt lời gọi tool của agent | HITL dừng tại một checkpoint và tiếp tục từ đó; ngoài ra nguồn không đề cập | Playground; tích hợp LangSmith, Langfuse, Opik, Arize |
| Flowise | Node Human Input; "Require Human Input" cho tool của agent | Agentflow V2 lưu checkpoint nên run đang dừng tiếp tục được sau khi khởi động lại | Evaluations; Langfuse, LangWatch, Lunary, Opik, Arize, Phoenix |

Cách gọi và mang đi nơi khác:

| Sản phẩm | API, SDK, MCP | Xuất code |
| --- | --- | --- |
| Superstep | API chạy công khai, SDK Python `superstep` và TypeScript `@superstep/sdk`, một phần Agent Server API tại `/api/lg` | Dự án LangGraph Python hoặc LangGraph.js chạy được |
| n8n | REST API và webhook | Không (workflow xuất ra JSON) |
| Dify | REST API, CLI `difyctl`, xuất bản ứng dụng thành MCP server | Không |
| Langflow | API chạy flow, webhook, MCP server và client, Flow DevOps Toolkit SDK | Không (flow xuất ra JSON) |
| Flowise | REST API (Prediction và các API khác) | Nguồn không đề cập |

## Superstep

- **LangGraph trực quan.** Graph được vẽ trên canvas (14 loại node, state có
  kiểu với reducer, vòng lặp, nhánh song song, subgraph, Human node) và biên
  dịch thành `StateGraph` của LangGraph. Code node Python và TypeScript chạy
  trong sandbox Docker khóa chặt (trên host khi dùng nền tảng được quản lý) khi
  bạn cần code. Xem [Node](../guide/nodes.md).
- **Node Agent nằm trong graph.** Model tự chọn và gọi các công cụ bạn liệt kê
  (công cụ của máy chủ MCP, yêu cầu HTTP, hàm có sẵn, tìm trong kho tri thức)
  trong số vòng đã đặt; công cụ nào cũng có thể cần duyệt trước mỗi lần gọi.
  Mỗi lần gọi model hay công cụ là một bước có checkpoint, nên hiện trong trace
  và không chạy lại sau khi khởi động lại (xem [Node Agent](../guide/agent.md)).
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

Những gì Superstep không cố trở thành: số tích hợp có sẵn ít hơn nhiều so với
bốn công cụ kia (kết nối qua HTTP, MCP server, email và các kênh chat), không
có dịch vụ cloud host sẵn và không có marketplace. Node Agent của Superstep là
một agent với các công cụ bạn liệt kê: không có nhóm nhiều agent hay chuyển
việc giữa các agent, và chưa xuất được sang TypeScript.

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

## Langflow

Langflow là nền tảng low-code viết bằng Python, giấy phép MIT, để dựng và triển
khai agent và workflow bằng trình dựng trực quan. Flow gồm các component; một
component Agent có thể dùng bất kỳ component nào làm tool, kể cả agent khác và
MCP server, và component LangChain có sẵn dưới dạng bundle tùy chọn. Flow chạy
qua Langflow API hoặc webhook, có thể phục vụ qua một Langflow MCP server, và
được thử trong Playground. Human-in-the-Loop "pauses a flow, creates a
checkpoint, and waits for a human decision", tại component Human Input hoặc khi
agent định gọi một tool cần duyệt. Trace có thể gửi tới LangSmith, Langfuse,
Opik hoặc Arize. Flow xuất ra JSON, và Flow DevOps Toolkit SDK giúp quản lý
phiên bản, test và triển khai flow từ terminal. Langflow chạy cục bộ, dưới dạng
Langflow Desktop, hoặc triển khai bằng Docker, Kubernetes hay nền tảng cloud.

Điểm mạnh của Langflow: thư viện component lớn, giấy phép MIT, MCP theo cả hai
chiều và component tùy chỉnh bằng Python.

## Flowise

Flowise là trình dựng trực quan cho agent AI và luồng LLM. Chatflow dựng
chatbot và luồng RAG từ các node dựa trên LangChain; Agentflow V2 dựng workflow
nhiều bước và nhiều agent từ các node gốc của Flowise với flow state dùng
chung. Tài liệu cho biết Agentflow V1 (đang ngừng dần) dựa vào framework bên
ngoài, và Multi-Agents, Sequential Agents của nó dựa trên LangGraph; V2 thì
không còn như vậy. Trong Agentflow V2, human-in-the-loop (node Human Input, hoặc
"Require Human Input" cho tool của agent) tạm dừng thực thi, và "each
checkpoint is saved, allowing the workflow to resume from the same point even
after an application restart". Flowise có Evaluations, tích hợp phân tích
(Langfuse, LangWatch, Lunary, Opik, Arize, Phoenix) và REST API. Flowise chạy
trên Flowise Cloud hoặc tự host bằng npm, Docker hay theo hướng dẫn cho nhiều
cloud.

Giấy phép là Apache 2.0, trừ thư mục `packages/server/src/enterprise` và các
file có thông báo bản quyền riêng.

Điểm mạnh của Flowise: dựng chatbot và RAG nhanh, canvas agent dễ tiếp cận với
human input có checkpoint, và nhiều hướng dẫn triển khai.

## Dùng cùng nhau

- **Gọi Superstep từ chúng.** n8n, Dify, Langflow hay Flowise có thể chạy
  workflow Superstep qua HTTP bằng API công khai, ví dụ để đặt một bước đã được
  review và có duyệt bởi người vào một quy trình tự động lớn hơn.
- **Gọi chúng từ Superstep.** Node HTTP và MCP, hoặc công cụ HTTP và MCP của
  node Agent, có thể gọi webhook của n8n, API ứng dụng Dify, Langflow MCP
  server hoặc endpoint prediction của Flowise.

## Khi nào nên chọn công cụ khác

- Chọn **n8n** khi việc chủ yếu là nối các ứng dụng nghiệp vụ (CRM, bảng tính,
  nhắn tin) kèm vài bước AI, bạn cần thư viện tích hợp có sẵn lớn, và
  Sustainable Use License phù hợp cách bạn dùng.
- Chọn **Dify** khi bạn muốn nền tảng ứng dụng LLM trọn gói với knowledge base,
  giao diện chat có sẵn, marketplace plugin và cloud host sẵn, và các điều kiện
  giấy phép (không dịch vụ nhiều tenant, giữ thương hiệu) phù hợp.
- Chọn **Langflow** khi bạn muốn trình dựng trực quan giấy phép MIT với thư
  viện component lớn, component tùy chỉnh bằng Python và phục vụ qua MCP.
- Chọn **Flowise** khi bạn muốn dựng nhanh chatbot, RAG và luồng agent, tự host
  hoặc trên Flowise Cloud.
- Chọn **Superstep** khi bạn muốn LangGraph bên dưới (có xuất code và API tương
  thích LangGraph), duyệt rõ ràng qua Slack, Telegram, WhatsApp, email hoặc
  Teams, du hành thời gian trên checkpoint, giấy phép MIT và tự host không cần
  hợp đồng, hoặc giao diện tiếng Việt.

## Nguồn

- [n8n: Integrate AI](https://docs.n8n.io/advanced-ai/)
- [n8n: Human-in-the-loop for tools](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools/)
- [n8n: Choose how to use n8n](https://docs.n8n.io/choose-how-to-use-n8n/)
- [Giấy phép n8n](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Tài liệu Dify](https://docs.dify.ai/en/introduction)
- [Dify: Human Input node](https://docs.dify.ai/en/self-host/use-dify/nodes/human-input)
- [Giấy phép Dify](https://github.com/langgenius/dify/blob/main/LICENSE)
- [Mục lục tài liệu Langflow](https://docs.langflow.org/llms.txt)
- [Langflow: Human-in-the-Loop](https://docs.langflow.org/human-in-the-loop)
- [Langflow: LangChain bundle](https://docs.langflow.org/bundles-langchain)
- [Langflow: Import and export flows](https://docs.langflow.org/concepts-flows-import)
- [Giấy phép Langflow](https://github.com/langflow-ai/langflow/blob/main/LICENSE)
- [Flowise: Agentflow V2](https://docs.flowiseai.com/using-flowise/agentflowv2)
- [Flowise: Sequential Agents (V1)](https://docs.flowiseai.com/using-flowise/agentflowv1/sequential-agents)
- [Flowise: Human in the loop](https://docs.flowiseai.com/tutorials/human-in-the-loop)
- [Giấy phép Flowise](https://github.com/FlowiseAI/Flowise/blob/main/LICENSE.md)
