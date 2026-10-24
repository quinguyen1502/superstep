# API tương thích LangGraph

Superstep trả lời một phần của
[LangGraph Agent Server API](https://docs.langchain.com/langsmith/server-api-ref)
tại `/api/lg`. Code viết cho LangGraph, dùng client `langgraph-sdk` chính thức
hoặc `RemoteGraph`, chạy được workflow Superstep mà không cần sửa: chỉ cần trỏ
tới studio của bạn thay vì một Agent Server.

| LangGraph | Superstep |
| --- | --- |
| Assistant / graph | Một workflow. `assistant_id` và `graph_id` là id của workflow (trong URL của editor). |
| Thread | Một chuỗi run của một workflow. State của thread là state của run gần nhất. |
| Run | Một run API của phiên bản đã lưu mới nhất. Run hiện trong lịch sử của workflow. |
| Interrupt | Một node Human đang chờ câu trả lời. |

## Kết nối

Dùng token của workflow (chỉ workflow đó) hoặc token đăng nhập của bạn (mọi
workflow bạn được chạy). SDK gửi `api_key` qua header `x-api-key`;
`X-Workflow-Token` và `Authorization: Bearer` cũng dùng được.

```python
from langgraph_sdk import get_client

client = get_client(url="https://superstep.example.com/api/lg", api_key="wft_...")

assistants = await client.assistants.search()
thread = await client.threads.create(metadata={"customer": "c-42"})
result = await client.runs.wait(thread["thread_id"], "example", input={"message": "Đơn A100 đang ở đâu?"})
print(result["answer"])
```

Stream run theo từng node:

```python
async for part in client.runs.stream(thread["thread_id"], "example",
                                     input={"message": "xin chào"}, stream_mode=["updates", "values"]):
    print(part.event, part.data)
```

Hoặc dùng workflow như một node trong graph LangGraph của bạn:

```python
from langgraph.pregel.remote import RemoteGraph

support = RemoteGraph("example", url="https://superstep.example.com/api/lg", api_key="wft_...")
print(support.invoke({"message": "xin chào"}))
```

## Node Human

Khi run tới một node Human, thread chuyển sang `interrupted` và `runs.wait`
trả về state kèm `__interrupt__`:

```python
out = await client.runs.wait(thread["thread_id"], wid, input={"message": "hoàn tiền đơn A100"})
print(out["__interrupt__"][0]["value"])  # {"node": "ask", "question": "Duyệt hoàn tiền ...?"}

done = await client.runs.wait(thread["thread_id"], wid, command={"resume": "approved"})
```

Câu trả lời là văn bản, hoặc `true` / `false` cho duyệt / từ chối, như trong
hộp thư [Duyệt bởi người](human-approval.md). Run đang chờ cũng hiện trong hộp
thư và các kênh duyệt, nên một người có thể trả lời ở đó.

## Những gì được hỗ trợ

| Endpoint | Ghi chú |
| --- | --- |
| `POST /assistants/search`, `GET /assistants/{id}` | Các workflow bạn được chạy |
| `GET /assistants/{id}/graph`, `GET /assistants/{id}/schemas` | Canvas dưới dạng graph LangGraph; schema từ các trường state |
| `POST /threads`, `GET /threads/{id}`, `POST /threads/search`, `DELETE /threads/{id}` | |
| `GET /threads/{id}/state`, `POST /threads/{id}/history` | History có một mục: state hiện tại |
| `POST /threads/{id}/runs`, `/runs/wait`, `/runs/stream` | Không cần thread: `POST /runs`, `/runs/wait`, `/runs/stream` |
| `GET /threads/{id}/runs`, `GET /threads/{id}/runs/{run_id}`, `.../join`, `.../cancel` | |

Cần biết:

- Run mới trên một thread bắt đầu từ state của thread, với input mới đè lên.
  Mỗi thread chạy một workflow và mỗi lúc một run (`409 THREAD_BUSY`).
- `stream_mode` hỗ trợ `values` (mặc định) và `updates`. Các chế độ khác không
  gửi gì.
- Chưa hỗ trợ: tạo hoặc sửa assistant, cron, store, sửa state của thread,
  checkpoint theo id, `interrupt_before` / `interrupt_after`.
- Lỗi dùng [envelope lỗi](../reference/errors.md) và mã HTTP như thường lệ.

## LangSmith Studio và Agent Chat UI

Chưa kiểm chứng. Cả hai chạy trên trình duyệt ở origin khác, nên studio phải
cho phép origin đó trong `STUDIO_CORS_ORIGINS`, và chúng gọi những endpoint mà
phần API này chưa có (lịch sử checkpoint, phiên bản assistant). Agent Chat UI
còn cần một danh sách `messages` trong state. Để làm việc với workflow trong
Studio, hãy xuất nó thành [dự án LangGraph](../guide/python-export.md) và chạy
`langgraph dev`.
