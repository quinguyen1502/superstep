# Quan sát hệ thống

## Trace

OpenTelemetry tạo một trace cho mỗi run và một span cho mỗi node, kèm các
thuộc tính `gen_ai.usage.*` và chi phí. Khi chưa cấu hình exporter, trace
không làm gì. Span được gửi đi khi từng node xong; run đang chờ người duyệt
được trace khi nó kết thúc.

| Đích | Biến |
| --- | --- |
| OTLP (Jaeger, Tempo, một collector) | `OTEL_EXPORTER_OTLP_ENDPOINT` và các biến `OTEL_*` chuẩn (`OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`) |
| LangSmith | `LANGSMITH_API_KEY` và `LANGSMITH_TRACING=true`, thêm `LANGSMITH_PROJECT` và `LANGSMITH_ENDPOINT` nếu cần |
| Link **Mở trace** trong UI | `STUDIO_TRACE_URL`, ví dụ `http://localhost:16686/trace/{trace_id}` |

Khi run được trace sang LangSmith và chưa đặt `STUDIO_TRACE_URL`, **Mở trace**
mở run đó trong LangSmith. Kết quả test cũng có thể gửi sang LangSmith: xem
[Kiểm thử workflow](../run/tests.md).

Khi exporter LangSmith của Studio bật, tracer LangSmith riêng của LangChain bị
tắt, để mỗi lời gọi LLM chỉ được xuất một lần.

## Jaeger với Compose

```bash
# trong .env
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
STUDIO_TRACE_URL=http://localhost:16686/trace/{trace_id}
```

```bash
docker compose --profile tracing up --build   # Jaeger UI: http://localhost:16686
```

Không dùng Compose:

```bash
docker run -p 16686:16686 -p 4318:4318 jaegertracing/all-in-one
```

rồi trỏ backend tới `http://localhost:4318`.

## Metric

`STUDIO_OTEL_METRICS=1` cùng một endpoint OTLP sẽ xuất thêm:

| Metric | Loại | Nghĩa |
| --- | --- | --- |
| `studio.runs` | counter | Số run đã kết thúc |
| `studio.run.duration` | histogram, ms | Thời gian run thực sự chạy |
| `studio.tokens` | counter | Token LLM |
| `studio.cost` | counter, USD | Chi phí LLM ước tính |
| `studio.errors` | counter | Số sự kiện lỗi |

## Health

`GET /api/health` cho biết `llm_mode`, `database`, `run_bus` và bus có phản
hồi không (`run_bus_ok`), `tracing` và `import_enabled`. Container `web` trả lời
`/healthz`.

## Log

API ghi log ra stdout. Lỗi trong sự kiện gói trong một dòng, `sk-…`,
`Bearer …` và `api_key=…` được che, và `?token=` hiện thành `token=***` trong
access log của uvicorn.
