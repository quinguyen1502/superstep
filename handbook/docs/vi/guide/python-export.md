# Xuất ra Python

Tab **Code** trong trình soạn thảo hiện workflow dưới dạng một file Python
LangGraph: state, mỗi node một hàm, và graph được dựng từ các hàm đó. Dùng nó
để xem một graph trên canvas được viết bằng code thế nào, hoặc mang bản thử
nghiệm sang dự án của bạn. Tab cũng có thể viết graph dưới dạng TypeScript
LangGraph.js: xem [TypeScript (LangGraph.js)](#typescript-langgraphjs).

![Tab Code với node Manager approval đang được chọn](../images/code-tab.png)

## Mở code

- Mở tab **Code** ở panel dưới, hoặc chọn **Xem dạng code** trong menu **⋯**
  hay bảng lệnh (++ctrl+k++).
- Tab hiện **phiên bản đã lưu mới nhất**. Thay đổi chưa lưu được đánh dấu và có
  trong code sau khi **Lưu**.
- Chọn một node trên canvas: code của nó được tô sáng và cuộn tới. Start và End
  chỉ tới các cạnh `START` và `END` của chúng.
- **Sao chép** chép cả file; **Tải .py** lưu file, đặt tên theo workflow.
- Ai mở được workflow thì xem được code của nó. Repo LangGraph đã import vốn
  là code nên không có tab Code.

## Chạy file

```bash
pip install langgraph
python leave_request.py
```

File không cần gì từ Superstep. Nó chạy input mẫu (input của test case đầu
tiên nếu workflow có test case), in ra những gì mỗi node trả về, rồi state cuối:

```text
[read_the_request] {"details": "[mock:gpt-4o-mini] Answer: I'd like leave ..."}
>> manager_approval: approved
[manager_approval] {"decision": "approved"}
(e-mail not sent) to bo@example.com: Your leave request: approved
...
Final state: {...}
```

- **Model.** Node LLM mặc định dùng mock offline: không cần API key, không tốn
  tiền, lần nào cũng ra cùng câu trả lời. Để gọi model thật, cài LangChain và
  gói của nhà cung cấp rồi đặt tên nhà cung cấp:

    ```bash
    pip install langchain langchain-openai
    export LLM_PROVIDER=openai OPENAI_API_KEY=sk-...
    ```

    `LLM_PROVIDER` là bất kỳ nhà cung cấp nào `init_chat_model` hỗ trợ
    (`openai`, `anthropic`, `ollama`, …); tên model của node được dùng nguyên
    như trên canvas.
- **Node Human và bước duyệt.** `EXAMPLE_ANSWERS` chứa các câu trả lời của
  test case đầu tiên, kể cả cho bước duyệt công cụ của node Agent. Khi một node
  hết câu trả lời, file hỏi trên terminal.
- **Node Code** chạy nguyên như đã viết, trong tiến trình Python của bạn, không
  có sandbox của studio. Hãy đọc chúng trước khi chạy file người khác chia sẻ.

## Từ canvas sang code

| Canvas | Code |
| --- | --- |
| Các trường state | `class State(TypedDict, total=False)`; trường có reducer là `Annotated[kiểu, reducer]` |
| Start và End | `START` và `END` trong các cạnh |
| LLM | `render(PROMPT, state)`, rồi `call_llm(prompt, model)` |
| Condition | một node không đổi gì, và `add_conditional_edges` với hàm router và bảng nhãn → node |
| Human | `interrupt(...)` dừng run; `Command(resume=answer)` chạy tiếp |
| Agent | một hàm vào, một hàm model và một hàm công cụ với hai router, và một hàm kết thúc; `interrupt(...)` trước công cụ cần duyệt |
| Join | một node, và `add_edge([nhánh, nhánh], join)`: chạy một lần khi mọi nhánh xong |
| For each | một trường vị trí vòng lặp và một router trả về `each` hoặc `done` |
| Decision | `decide(text, question)` cho từng câu hỏi |
| Subgraph | workflow con thành graph riêng `build_<child>()`, được thêm như một node |
| Tool: function | code của hàm, được chép vào |
| Tool: HTTP | một request `httpx` |
| Tool: Code | code của node, nằm trong hàm của node |
| Retriever, MCP, Send email | hàm stub có `TODO`: chúng cần dịch vụ của studio (kể cả công cụ kho tri thức và MCP của node Agent) |
| Note | một comment |
| Retry, cache, trường input | `RetryPolicy`, `CachePolicy`, `input_schema` trong `add_node` |
| Timeout | một comment: LangGraph không dừng được node đang chặn |

Hàm của node được đặt theo nhãn (`Read the request` → `read_the_request`). Tên
trùng với một trường state hay một tên của Python được thêm `_node`, ví dụ
`decision_node`.

### State và reducer

Từ mẫu Tổng hợp phản hồi khách hàng:

```python
class State(TypedDict, total=False):
    feedback: list
    item: str
    labelled: Annotated[list, append_items]
    report: str
    sent: dict
    loop_each_piece_of_feedback: int  # loop position of a For each node
```

Một node chỉ trả về các trường nó đổi, và LangGraph gộp chúng vào state. Trường
không có reducer bị thay thế; `labelled` gom một nhãn cho mỗi phản hồi.

### Một Condition

Từ mẫu Định tuyến:

```python
def route_route(state: State) -> str:
    """The branch to take after "Route": the edge label that state["intent"] names."""
    value = state.get("intent")
    ...
    label = pick_branch(value, ["billing", "technical", "other"])
    return "other" if label is None else label


builder.add_conditional_edges("route", route_route, {"billing": "billing_answer", "technical": "technical_answer", "other": "general_answer"})
```

### Một node Human

Từ mẫu Đơn nghỉ phép:

```python
def manager_approval(state: State) -> dict:
    answer = interrupt({"node": "manager_approval", "question": render(MANAGER_APPROVAL_PROMPT, state)})
    return {"decision": answer}
```

`interrupt()` dừng run và trao câu hỏi cho bên gọi. Graph được compile với một
checkpointer (`MemorySaver`), nên `main()` chạy tiếp được bằng
`graph.stream(Command(resume="approved"), config)`. Khi đó node chạy lại từ
đầu, và `interrupt()` trả về câu trả lời.

### Một node Agent

Lấy từ mẫu Agent hỗ trợ khách hàng. Node Agent được viết đúng như studio chạy
nó: mỗi bước một hàm, và cuộc hội thoại nằm trong một trường state
(`agent_support_agent`) mà hàm kết thúc sẽ xoá.

```python
builder.add_edge("support_agent", "support_agent_model")
builder.add_conditional_edges("support_agent_model", route_support_agent_model, {"tool": "support_agent_tool", "done": "support_agent_end"})
builder.add_conditional_edges("support_agent_tool", route_support_agent_tool, {"tool": "support_agent_tool", "model": "support_agent_model"})
```

- `support_agent_model` gọi `call_agent(messages, tools, model)`: bản mock, hoặc
  khi đặt `LLM_PROVIDER` thì một chat model của LangChain với `bind_tools`.
- `support_agent_tool` chạy một lần gọi công cụ. Công cụ trong
  `SUPPORT_AGENT_NEEDS_APPROVAL` hỏi trước bằng `interrupt()`; "approved" thì
  chạy, mọi câu trả lời khác được báo cho model làm lý do.
- `SUPPORT_AGENT_TOOLS` chứa tên, mô tả và JSON Schema của từng công cụ, còn
  `SUPPORT_AGENT_MAX_ROUNDS` là giới hạn số vòng.

File không dùng `create_react_agent`: hàm đó không hỏi trước riêng một công cụ
được, và không ghi các vòng và các bước như studio.

Một [công cụ workflow](agent.md#workflow-lam-cong-cu) (từ mẫu Đội hỗ trợ) gọi
graph riêng của workflow kia, được viết một lần trong cùng file:

```python
def call_supervisor_tool(name: str, args: dict, state: State) -> Any:
    if name == "order_desk":
        final = build_order_desk().invoke({k: args[k] for k in ["message"] if k in args})
        return {k: final.get(k) for k in ["answer"]}
```

Trong studio, lần gọi là một run được gọi; trong file, graph con chạy ngay trong
bước công cụ, và một `interrupt()` bên trong nó làm cả graph dừng chờ.

### Một Subgraph

```python
def build_review_step():
    builder = StateGraph(ReviewStepState)
    ...
    return builder.compile()


builder.add_node("review", build_review_step())  # a compiled graph is a node of another graph
```

Subgraph có class state riêng và dùng chung trường với graph cha theo tên.

## TypeScript (LangGraph.js)

Chọn **TypeScript** trong menu ngôn ngữ của tab Code để có cùng graph dưới dạng
một file [LangGraph.js](https://langchain-ai.github.io/langgraphjs/). Menu nhớ
lựa chọn của bạn; **Tải .ts** lưu file.

```bash
deno run --allow-env --allow-read leave_request.ts
```

Các package là import `npm:` (`npm:@langchain/langgraph@^1.5`), nên Deno tự tải
ở lần chạy đầu và `deno check` kiểm tra kiểu của file. Với Node, bỏ tiền tố
`npm:` và phiên bản, chạy `npm i @langchain/langgraph @langchain/core`, rồi
`npx tsx leave_request.ts`.

| Canvas | TypeScript |
| --- | --- |
| Trường state | `Annotation.Root({...})`; reducer là `Annotation({ reducer, default })` |
| LLM | `render(PROMPT, state)`, rồi `callLlm(prompt, model)`: mock, hoặc `initChatModel` khi đặt `LLM_PROVIDER` |
| Condition, For each | `addConditionalEdges` với một hàm router |
| Human | `interrupt(...)`; `new Command({ resume })` chạy tiếp |
| Join | `addEdge([nhánh, nhánh], join)` |
| Decision | `decide(text, question)` cho từng câu hỏi |
| Subgraph | `build_<child>()`, một graph đã compile được thêm làm node |
| Tool: Code bằng TypeScript | code của node giữ nguyên; các import được chuyển lên đầu file |
| Tool: Code bằng Python | stub ném lỗi `not implemented in TS export`: hãy chuyển sang TypeScript |
| Tool: function | stub ném lỗi: hàm là Python trên server |
| Tool: HTTP | `fetch`, không đi theo chuyển hướng |
| Retriever, MCP, Send email | stub có `TODO`, như file Python |
| Agent | các bước vào, model, công cụ và kết thúc, như file Python; `callAgent` là mock, hoặc `initChatModel` với `bindTools` khi đặt `LLM_PROVIDER`. Công cụ có sẵn là stub ném lỗi |
| Retry, cache, trường đầu vào, timeout | `retryPolicy`, `cachePolicy`, `input`, `timeout` trong `addNode` |

API key và các thiết lập khác được đọc từ biến môi trường (`LLM_PROVIDER`,
`OPENAI_API_KEY`, …), không bao giờ ghi vào file. Node không nối tới Start bị bỏ
ra, kèm một chú thích: LangGraph.js không nhận node không tới được. File Python
cũng có stub tương tự cho Code node TypeScript (`NotImplementedError`).

## Dự án cho langgraph dev và LangSmith Studio

**Dự án .zip** (cạnh nút **Tải**) lưu bản xuất thành một dự án LangGraph nhỏ
mà [LangGraph CLI](https://docs.langchain.com/langsmith/cli) chạy bằng
`langgraph dev`, nhờ đó graph mở được trong
[LangSmith Studio](https://docs.langchain.com/langsmith/studio). File zip có
một thư mục:

| File | Nội dung |
| --- | --- |
| `agent.py` / `agent.ts` | File xuất, thêm `graph = build_graph()` ở cuối: graph mà server nạp |
| `langgraph.json` | Cấu hình CLI: `graphs` ánh xạ tên workflow tới `./agent.py:graph`, `env` là `.env` |
| `requirements.txt`, `pyproject.toml` | Python: `langgraph` và các thư viện bên ngoài mà Code node import |
| `package.json`, `tsconfig.json` | TypeScript: `@langchain/langgraph`, `@langchain/core`, `langchain` và `@langchain/langgraph-cli` với `npm run dev` |
| `.env.example` | Các biến môi trường graph đọc, key của model và tracing LangSmith |
| `README.md` | Cách chạy |

Python:

```bash
unzip leave-request-python.zip && cd leave-request
pip install -U "langgraph-cli[inmem]" -r requirements.txt
cp .env.example .env
langgraph dev
```

TypeScript (Node 20 trở lên):

```bash
unzip leave-request-typescript.zip && cd leave-request
npm install
cp .env.example .env
npm run dev
```

Server nghe ở `http://localhost:2024` và in ra đường dẫn Studio
(`https://smith.langchain.com/studio/?baseUrl=http://localhost:2024`). Server
cục bộ và API của nó chạy không cần tài khoản; riêng Studio cần đăng nhập
LangSmith. Mọi client LangGraph đều gọi được server, ví dụ Python SDK:

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:2024")
assistant = (await client.assistants.search())[0]
thread = await client.threads.create()
print(await client.runs.wait(thread["thread_id"], assistant["assistant_id"], input={"message": "Xin chào"}))
```

Dự án khác file đơn ở ba điểm nhỏ: graph được compile không kèm checkpointer
(server tự thêm, nên `interrupt()` của node Human dừng thread và Studio tiếp tục
nó), import TypeScript là tên package thường thay vì `npm:` của Deno, và ví dụ
TypeScript chỉ chạy bằng `npm run example`, không chạy khi server import file.
`scripts/langgraph_dev_smoke.py python|typescript` xuất workflow mẫu, chạy
`langgraph dev` trên nó và gọi bằng SDK.

## Những gì không có trong file

- Credential, API key, cấu hình SMTP, kho tri thức, máy chủ MCP, kênh duyệt,
  người duyệt và địa chỉ chuyển cấp.
- Các tính năng của studio quanh một run: trace, lịch sử run, khôi phục sau
  khi khởi động lại, kênh duyệt và hạn chót, theo dõi chi phí, timeout của node.
- Lời gọi Retriever, MCP và Send email thật: stub trả về kết quả rỗng, không
  gì cả, hoặc thư lẽ ra sẽ gửi.

Hai kết quả có thể khác studio: node Decision với model thật hỏi LLM thay vì
TypeSafe Jev, và một trường có reducer mà subgraph cũng ghi sẽ được gộp thêm một
lần khi subgraph trả về.

## API

`GET /api/workflows/{wid}/python` trả về code, tên file, version và các dòng
của từng node; `GET /api/workflows/{wid}/export/python` tải file và `GET /api/workflows/{wid}/export/{language}/project` tải zip dự án.
Cả ba nhận
`?version=n` và `?language=python|typescript` (`GET /api/workflows/{wid}/code`
và `/export/typescript` cũng vậy, với tên trung lập). Xem [HTTP API](../reference/api.md).
