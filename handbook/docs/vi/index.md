---
title: Tài liệu Superstep
hide:
  - navigation
  - toc
---

<div class="home" markdown>

# Tài liệu Superstep

Superstep là nền tảng tự host để xây workflow LangGraph trên trình duyệt
và chạy chúng như một dịch vụ. Mỗi workflow là một tài liệu JSON: backend
FastAPI kiểm tra, biên dịch nó thành `StateGraph` của LangGraph, rồi chạy kèm
sự kiện của từng node. Cùng một workflow có thể được khởi chạy qua HTTP, theo
lịch cron, hoặc dừng lại chờ người quyết định.

<video id="video" class="home-video" controls playsinline preload="none" poster="assets/video/studio-intro-vi.jpg" aria-label="Video bắt đầu nhanh: dựng, chạy, duyệt và gọi một workflow, rồi node Agent, du hành thời gian, tool MCP và giao diện điện thoại">
  <source src="assets/video/studio-intro-vi.mp4" type="video/mp4">
</video>

## Bắt đầu nhanh

```bash
git clone https://github.com/quinguyen1502/superstep.git
cd superstep && ./dev.sh
```

Mở <http://localhost:5173> và tạo tài khoản bằng **Đăng ký**. Node LLM trả lời bằng bản mock offline cho tới khi bạn thêm
credential của model, nên không cần gì thêm để làm theo phần
[bắt đầu nhanh](start/quickstart.md): dựng một workflow, chạy, duyệt và gọi
nó qua HTTP trong khoảng mười phút.

## Các phần tài liệu

<div class="grid cards" markdown>

-   :material-rocket-launch-outline:{ .lg .middle } **Bắt đầu**

    ---

    [Tổng quan](start/index.md) · [Bắt đầu nhanh](start/quickstart.md) ·
    [Cài đặt](start/install.md) · [Khái niệm](start/concepts.md)

-   :material-vector-polyline:{ .lg .middle } **Xây dựng**

    ---

    [Trình soạn thảo](guide/editor.md) · [Các loại node](guide/nodes.md) ·
    [State và tham chiếu](guide/state.md) · [Chế độ Code](guide/code-mode.md) ·
    [Kho tri thức](guide/knowledge.md) · [Máy chủ MCP](guide/mcp.md) ·
    [Mẫu workflow](guide/templates.md) · [Phiên bản](guide/versions.md)

-   :material-play-circle-outline:{ .lg .middle } **Chạy**

    ---

    [Run và trace](run/traces.md) · [Duyệt bởi người](run/human-approval.md) ·
    [API trigger và webhook](run/api-triggers.md) · [Lịch chạy](run/schedules.md)

-   :material-server-outline:{ .lg .middle } **Vận hành**

    ---

    [Triển khai bằng Compose](operate/deploy.md) · [Tài khoản](operate/accounts.md) ·
    [Vai trò và chia sẻ](operate/access.md) · [Nhà cung cấp LLM](operate/providers.md) ·
    [Kênh duyệt](operate/channels.md) · [Môi trường chạy Code](operate/code-runtime.md) ·
    [Quan sát hệ thống](operate/observability.md) · [Import repo](operate/import.md)

-   :material-book-open-variant:{ .lg .middle } **Tham chiếu**

    ---

    [Cấu hình](reference/configuration.md) · [HTTP API](reference/api.md) ·
    [Mã lỗi](reference/errors.md) · [Kiến trúc](reference/architecture.md) ·
    [Phím tắt](reference/shortcuts.md) · [Phát triển](reference/development.md) ·
    [Câu hỏi thường gặp](reference/faq.md)

</div>

## Thành phần

| Phần | Xây trên | Vai trò |
| --- | --- | --- |
| Editor | React, React Flow, shadcn/ui | Vẽ graph và ghi JSON của workflow; nhận sự kiện của run qua WebSocket |
| API | FastAPI, SQLAlchemy, Alembic | Lưu workflow và phiên bản, kiểm tra và biên dịch, phục vụ REST và WebSocket |
| Engine | `StateGraph` của LangGraph | Chạy graph theo superstep và lưu checkpoint state sau mỗi superstep |
| Worker | Hàng đợi trong bộ nhớ hoặc Redis | Chạy run gọi qua API, run theo lịch, run được khôi phục, và gửi webhook |
| Lưu trữ | SQLite, hoặc Postgres có pgvector | Workflow, run, checkpoint, credential và vector của kho tri thức |
| Sandbox | Docker | Python trong node Tool và các repo LangGraph được import |
| Telemetry | OpenTelemetry | Mỗi run một trace, mỗi node một span, gửi tới OTLP hoặc LangSmith |

Xem [Kiến trúc](reference/architecture.md) để biết đường đi của request và các
đảm bảo khi retry và khôi phục.

</div>
