# API công khai và SDK

Dịch vụ khác khởi chạy workflow qua HTTP bằng **token của workflow**, rồi hỏi
lại (poll) để lấy kết quả. Trang này mô tả hai endpoint công khai, SDK chính
thức cho Python và TypeScript, và các lỗi cần xử lý. Callback, chữ ký và lịch
sử gửi webhook nằm ở [API trigger và webhook](api-triggers.md). Mọi trường đều
có trong [Tham chiếu API công khai](../reference/public-api.md).

## Khái niệm

| Thuật ngữ | Nghĩa |
| --- | --- |
| Token của workflow | Secret `wft_...` chỉ khởi chạy được run của **một** workflow. Gửi dưới dạng `X-Workflow-Token: wft_...` hoặc `Authorization: Bearer wft_...`. Ngoài các endpoint này, token chỉ dùng được với [API tương thích LangGraph](agent-server-api.md) và [MCP server](mcp-server.md) của cùng workflow. |
| Run | Một lần thực thi phiên bản đã lưu mới nhất của workflow. `input` là state ban đầu. |
| Trạng thái | `queued` và `running` khi đang chạy; sau đó là `ok`, `error`, `cancelled`, `timeout`, `waiting` (dừng ở node Human) hoặc `expired`. |
| Envelope | Mọi phản hồi đều có dạng `{"success", "data", "error"}`. Khi lỗi, `error.code` là mã ổn định; `error.message` là tiếng Anh, dùng cho log. |

| Phương thức và đường dẫn | Operation | Mục đích |
| --- | --- | --- |
| `POST /api/hooks/workflows/{wid}/runs` | `startRun` | Khởi chạy run. Trả `202` kèm `poll_url` và header `Location`, hoặc `200` kèm kết quả ở chế độ `sync`. |
| `GET /api/hooks/workflows/{wid}/runs/{run_id}` | `getRun` | Trạng thái, và khi đã xong thì có `final_state`, `error`, `metrics`. |

## Tạo token

1. Mở workflow trong trình soạn thảo và lưu lại.
2. Mở **⋯ → API**, nhập tên rồi chọn **Tạo token**.
3. Sao chép token (`wft_...`) và secret ký (`whsec_...`). Mỗi thứ chỉ hiện một
   lần; hãy cất vào nơi quản lý secret của bạn.

![Hộp thoại API](../images/api-trigger.png)

Chỉ chủ workflow hoặc admin mới tạo được token. Thu hồi token ngay trong hộp
thoại này; sau đó mọi request dùng token đó bị từ chối với
`401 TRIGGER_TOKEN_INVALID`. Mã workflow (`wid`) là phần cuối của URL trình
soạn thảo.

## Khởi chạy run

=== "curl"

    ```bash
    curl -i -X POST "$SUPERSTEP_BASE_URL/api/hooks/workflows/$WID/runs" \
      -H "X-Workflow-Token: $SUPERSTEP_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"input": {"message": "where is my order A100"}}'
    ```

=== "Python"

    ```python
    from superstep import Client

    client = Client(workflow_id="example", token="wft_...", base_url="https://superstep.example.com")
    started = client.run({"message": "where is my order A100"})
    print(started.run_id, started.status)  # ... queued
    ```

=== "TypeScript"

    ```ts
    import { Superstep } from '@superstep/sdk'

    const client = new Superstep({ workflowId: 'example', token: 'wft_...', baseUrl: 'https://superstep.example.com' })
    const started = await client.run({ message: 'where is my order A100' })
    console.log(started.run_id, started.status) // ... queued
    ```

Phản hồi là `202 Accepted`:

```json
{
  "success": true,
  "data": {"run_id": "3f9c2a1b7d", "status": "queued",
           "poll_url": "https://superstep.example.com/api/hooks/workflows/example/runs/3f9c2a1b7d"},
  "error": null
}
```

| Trường trong body | Nghĩa |
| --- | --- |
| `input` | State ban đầu, một JSON object (mặc định `{}`). |
| `mode` | `async` (mặc định) trả lời ngay. `sync` chờ tối đa `STUDIO_SYNC_WAIT_MAX` giây (mặc định 30) rồi trả `200` kèm kết quả; nếu run vẫn đang chạy thì trả `202` kèm kết quả hiện tại và `poll_url`. |
| `callback_url` | Tuỳ chọn. URL công khai nhận kết quả khi run kết thúc. Xem [Xác minh callback](api-triggers.md#kiem-tra-callback). |

## Lấy kết quả

=== "curl"

    ```bash
    curl "$SUPERSTEP_BASE_URL/api/hooks/workflows/$WID/runs/3f9c2a1b7d" \
      -H "Authorization: Bearer $SUPERSTEP_TOKEN"
    ```

=== "Python"

    ```python
    run = client.get_run(started.run_id)
    if run.done:
        print(run.status, run.final_state)
    ```

=== "TypeScript"

    ```ts
    import { isDone } from '@superstep/sdk'

    const run = await client.getRun(started.run_id)
    if (isDone(run)) console.log(run.status, run.final_state)
    ```

```json
{
  "success": true,
  "data": {
    "run_id": "3f9c2a1b7d", "workflow_id": "example", "status": "ok", "source": "api",
    "final_state": {"intent": "order_status"}, "error": null, "waiting": null,
    "metrics": {"duration_ms": 412.0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "error_count": 0},
    "trace_url": null, "started": 1761292800.0, "ended": 1761292800.4
  },
  "error": null
}
```

Hỏi lại mỗi một hoặc hai giây và giãn dần với run dài; việc poll không bị
giới hạn tần suất. Run kết thúc ở `error` có lỗi của node hỏng trong `error`;
run ở `waiting` ghi tên node Human và prompt của nó trong `waiting`.

## Chạy và chờ

`run_and_wait` (Python) và `runAndWait` (TypeScript) khởi chạy run rồi poll
đến khi xong. Khoảng chờ bắt đầu từ 1 giây, mỗi lần tăng 1,5 lần, tối đa 10
giây. Hàm trả về run bất kể trạng thái cuối, nên hãy kiểm tra `status`; quá
`timeout` thì báo `WaitTimeoutError` kèm trạng thái cuối cùng đã thấy.

=== "Python"

    ```python
    from superstep import Client, WaitTimeoutError

    client = Client()  # SUPERSTEP_WORKFLOW_ID, SUPERSTEP_TOKEN, SUPERSTEP_BASE_URL
    try:
        run = client.run_and_wait({"message": "hi"}, timeout=120, poll_interval=0.5)
    except WaitTimeoutError as err:
        print("still", err.run.status)
    else:
        print(run.status, run.final_state)
    ```

    `AsyncClient` có cùng các phương thức, dạng coroutine:

    ```python
    from superstep import AsyncClient

    async with AsyncClient() as client:
        run = await client.run_and_wait({"message": "hi"})
    ```

=== "TypeScript"

    ```ts
    import { Superstep } from '@superstep/sdk'

    const client = new Superstep() // SUPERSTEP_WORKFLOW_ID, SUPERSTEP_TOKEN, SUPERSTEP_BASE_URL
    const run = await client.runAndWait(
      { message: 'hi' },
      { timeoutMs: 120_000, pollIntervalMs: 500, signal: AbortSignal.timeout(130_000) },
    )
    console.log(run.status, run.final_state)
    ```

=== "curl"

    ```bash
    # Để máy chủ chờ (tối đa STUDIO_SYNC_WAIT_MAX giây).
    curl -X POST "$SUPERSTEP_BASE_URL/api/hooks/workflows/$WID/runs" \
      -H "X-Workflow-Token: $SUPERSTEP_TOKEN" -H "Content-Type: application/json" \
      -d '{"input": {"message": "hi"}, "mode": "sync"}'
    ```

## Cài SDK

| Ngôn ngữ | Cài đặt | Mã nguồn |
| --- | --- | --- |
| Python 3.9+ | `pip install superstep` | [`sdk/python`](https://github.com/quinguyen1502/superstep/tree/develop/sdk/python) |
| TypeScript, Node 18+ | `npm install @superstep/sdk` | [`sdk/typescript`](https://github.com/quinguyen1502/superstep/tree/develop/sdk/typescript) |

Cả hai đọc `SUPERSTEP_BASE_URL`, `SUPERSTEP_TOKEN` và `SUPERSTEP_WORKFLOW_ID`
khi bạn không truyền tuỳ chọn tương ứng. Trước bản phát hành đầu tiên, cài từ
mã nguồn: `pip install ./sdk/python` hoặc `npm install ./sdk/typescript`.

## Lỗi

Lỗi dùng envelope và một `code` ổn định:

```json
{"success": false, "data": null,
 "error": {"code": "TRIGGER_TOKEN_INVALID", "message": "Missing, invalid or revoked workflow token", "details": null}}
```

| HTTP | Mã | Nguyên nhân | Lỗi trong Python / TypeScript |
| --- | --- | --- | --- |
| 401 | `TRIGGER_TOKEN_INVALID` | Thiếu token, sai, đã thu hồi, hoặc token của workflow khác | `AuthenticationError` |
| 404 | `RUN_NOT_FOUND` | Run không tồn tại, hoặc thuộc workflow khác | `NotFoundError` |
| 400 | `RUN_INPUT_INVALID` | `input` không phải JSON object | `InvalidRequestError` |
| 400 | `CALLBACK_URL_INVALID` | `callback_url` không phải URL http(s) công khai | `InvalidRequestError` |
| 422 | `VALIDATION_ERROR` | Body sai dạng; `details` liệt kê `{field, message}` | `InvalidRequestError` |
| 413 | `RUN_INPUT_TOO_LARGE` | `input` vượt `STUDIO_INPUT_MAX_BYTES` (mặc định 256 KB) | `PayloadTooLargeError` |
| 429 | `RATE_LIMITED` | Token này khởi chạy quá nhiều run | `RateLimitError` (`retry_after` / `retryAfter`) |
| 500 | `INTERNAL_ERROR` | Lỗi máy chủ | `ServerError` |

SDK còn có `APIConnectionError` (lỗi mạng, hoặc phản hồi không phải
envelope), `WaitTimeoutError` và `ConfigError`. Toàn bộ mã lỗi nằm ở
[Mã lỗi](../reference/errors.md).

## Giới hạn tần suất

Mỗi token được khởi chạy `STUDIO_TRIGGER_RATE_LIMIT` run trong mỗi
`STUDIO_TRIGGER_RATE_WINDOW` giây (mặc định 60 run mỗi 60 giây). Vượt giới hạn
thì nhận `429 RATE_LIMITED` kèm header `Retry-After` tính bằng giây. Việc poll
không bị giới hạn. Có Redis thì mọi process API dùng chung bộ đếm; không có
Redis thì mỗi process đếm riêng.

=== "Python"

    ```python
    import time
    from superstep import RateLimitError

    try:
        client.run({"message": "hi"})
    except RateLimitError as err:
        time.sleep(err.retry_after or 1)
    ```

=== "TypeScript"

    ```ts
    import { RateLimitError } from '@superstep/sdk'

    try {
      await client.run({ message: 'hi' })
    } catch (err) {
      if (!(err instanceof RateLimitError)) throw err
      await new Promise((r) => setTimeout(r, (err.retryAfter ?? 1) * 1000))
    }
    ```

## OpenAPI

Các endpoint công khai có spec riêng, không kèm API nội bộ của studio:

| Ở đâu | Nội dung |
| --- | --- |
| `/openapi.public.json` trên máy chủ đang chạy | Spec công khai |
| `/docs/public` trên máy chủ đang chạy | Swagger UI cho spec công khai |
| `docs/api/openapi.public.json` trong repository | Bản đã commit, nguồn để sinh SDK |
| [Tham chiếu API công khai](../reference/public-api.md) | Spec hiển thị ngay trong handbook |

Bạn có thể sinh client cho ngôn ngữ khác từ file đó bằng bất kỳ công cụ sinh
OpenAPI nào.
