<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/brand/superstep-mark-dark.svg">
    <img src="frontend/public/brand/superstep-mark.svg" alt="Superstep logo" width="140" height="140">
  </picture>

  <h3><b>Superstep</b></h3>
  <p>Studio LangGraph trực quan, mã nguồn mở<br>Kéo thả đồ thị • Theo dõi run trực tiếp • Duyệt bởi con người • Node code Python &amp; TypeScript</p>

  <p>
    <a href="https://github.com/quinguyen1502/superstep/stargazers"><img src="https://img.shields.io/github/stars/quinguyen1502/superstep?style=social" alt="GitHub stars"></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/quinguyen1502/superstep" alt="License"></a>
    <a href="https://github.com/quinguyen1502/superstep/actions/workflows/ci.yml"><img src="https://github.com/quinguyen1502/superstep/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://quinguyen1502.github.io/superstep/vi/"><img src="https://github.com/quinguyen1502/superstep/actions/workflows/handbook.yml/badge.svg" alt="Handbook"></a>
  </p>

  <a href="README.md">English</a> · <b>Tiếng Việt</b>
</div>

<p align="center"><b>Dựng workflow LangGraph trên trình duyệt và chạy chúng như một dịch vụ.</b></p>

<p align="center"><a href="https://quinguyen1502.github.io/superstep/vi/">Tài liệu</a> • <a href="https://quinguyen1502.github.io/superstep/vi/#video">Video bắt đầu nhanh</a> • <a href="https://quinguyen1502.github.io/superstep/vi/reference/api/">HTTP API</a> • <a href="https://quinguyen1502.github.io/superstep/vi/run/public-api/">API công khai và SDK</a> • <a href="https://quinguyen1502.github.io/superstep/vi/reference/architecture/">Kiến trúc</a></p>

<img src="handbook/docs/vi/images/overview.png" alt="Trình soạn thảo Superstep: workflow rẽ nhánh, cài đặt node, run đang chờ người duyệt và khung Chat" width="100%">

<table>
  <tr>
    <td width="33%" align="center"><img src="handbook/docs/vi/images/chat-tab.png" alt="Chat với workflow" width="100%"><p>Chat với workflow</p></td>
    <td width="33%" align="center"><img src="handbook/docs/vi/images/run-trace.png" alt="Trace run trực tiếp" width="100%"><p>Trace run trực tiếp</p></td>
    <td width="33%" align="center"><img src="handbook/docs/vi/images/code-tab.png" alt="Xuất mã LangGraph" width="100%"><p>Xuất mã LangGraph</p></td>
  </tr>
</table>

## Vì sao chọn Superstep?

<table>
  <tr>
    <td width="50%" valign="top"><b>Đồ thị trực quan</b><br>Kéo node, nối cạnh; lưu dạng JSON, biên dịch thành <code>StateGraph</code> của LangGraph</td>
    <td width="50%" valign="top"><b>Run trực tiếp</b><br>Trace và thay đổi state của từng node khi đang chạy; debug từng bước</td>
  </tr>
  <tr>
    <td width="50%" valign="top"><b>Con người duyệt</b><br>Dừng chờ duyệt trong studio, Slack, Telegram, email hoặc Teams</td>
    <td width="50%" valign="top"><b>Trigger</b><br>HTTP API có token, webhook có chữ ký, lịch cron, lệnh chat</td>
  </tr>
  <tr>
    <td width="50%" valign="top"><b>Code Python & TypeScript</b><br>Node code trong sandbox Docker khoá chặt; mọi model, MCP và pgvector</td>
    <td width="50%" valign="top"><b>Học LangGraph</b><br>Xuất workflow thành một file Python dễ đọc, chạy độc lập</td>
  </tr>
</table>

## Bắt đầu nhanh

```bash
git clone https://github.com/quinguyen1502/superstep.git
cd superstep && ./dev.sh
```

Mở <http://localhost:5173> và tạo tài khoản bằng **Đăng ký** (ngoài production
còn có sẵn tài khoản demo `admin@example.com` / `admin123`). Tài liệu API ở
<http://localhost:8000/docs>. Node LLM trả lời bằng bản mock offline cố định
cho tới khi bạn thêm credential của model. Phần
[Bắt đầu nhanh](https://quinguyen1502.github.io/superstep/vi/start/quickstart/)
hướng dẫn dựng, chạy, duyệt và gọi workflow đầu tiên trong khoảng mười phút.

Chạy đủ stack (Postgres có pgvector, Redis, API, worker, nginx):

```bash
cp .env.example .env        # đặt JWT_SECRET và POSTGRES_PASSWORD
docker compose up --build   # http://localhost:8080
```

## Tính năng

1. **Trình soạn thảo trực quan:** 14 loại node (LLM, Agent, Tool, Condition,
   For each, Join, Subgraph, MCP, Retriever, Decision, Send email, Human,
   Start, End) cùng node Code chỉ đọc từ repo đã import, state có kiểu và reducer,
   tham chiếu `{{state.field}}` được kiểm tra trước khi chạy, và thư viện mẫu
   để bắt đầu nhanh.
2. **Trace của run:** thời gian, token và chi phí từng node, input, output và
   state diff của mỗi bước, debug từng bước và chạy tới node đã chọn. Test
   case kiểm tra kết quả của workflow, và có thể so sánh các run test.
3. **Node Agent:** model tự chọn và gọi các công cụ bạn cho phép (công cụ
   của máy chủ MCP, yêu cầu HTTP, hàm có sẵn, tìm trong kho tri thức) tới khi
   trả lời được, có giới hạn số vòng và bước duyệt trước các công cụ bạn đánh
   dấu.
4. **Duyệt giữa chừng (human-in-the-loop):** node Human dừng run tại
   checkpoint; duyệt trong hộp Duyệt của studio, hoặc qua Slack, Telegram,
   WhatsApp, email hay Teams; hạn chờ gửi nhắc, chuyển người duyệt hoặc cho run
   hết hạn.
5. **Trigger:** token API cho từng workflow, run đồng bộ và bất đồng bộ,
   webhook kết quả có chữ ký và retry, lịch cron theo múi giờ, và chạy từ
   chat: một lệnh gửi Slack app hoặc bot Telegram chạy workflow, bot trả lời.
6. **Độ tin cậy:** checkpoint trong database, job của worker có lease, side
   effect thực hiện gần như đúng một lần (effectively-once) nhờ idempotency
   key và sổ ghi kết quả.
7. **Model và công cụ:** OpenAI, Anthropic, OpenRouter, Ollama, LM Studio và
   server tương thích OpenAI; kho tri thức pgvector; máy chủ MCP; code Python
   chạy trong container Docker bị giới hạn chặt.
8. **Vận hành:** phiên bản bất biến có diff và khôi phục, vai trò admin,
   editor và viewer, chia sẻ và nhóm, nhật ký audit, trace OpenTelemetry gửi
   tới OTLP hoặc LangSmith.
9. **Học LangGraph:** tab Code hiện mọi workflow dưới dạng một file Python
   LangGraph dễ đọc, chạy được độc lập (offline với model mock), tô sáng code
   của node đang chọn, và xuất ra để dùng trong dự án của bạn.

## Cách hoạt động

```mermaid
flowchart LR
  UI[Trình soạn thảo<br/>React Flow] -- REST + WebSocket --> API[FastAPI]
  SVC[Dịch vụ khác] -- "POST /api/hooks/…/runs" --> API
  API --> DB[(SQLite hoặc<br/>Postgres + pgvector)]
  API -- job --> Q[(Bộ nhớ hoặc Redis)] --> W[Worker]
  API & W --> G[LangGraph StateGraph]
  G --> M[Nhà cung cấp LLM] & T[HTTP · MCP · SMTP] & S[Sandbox Docker]
```

Run khởi chạy từ trình soạn thảo được thực thi ngay trong process API và gửi sự kiện qua
WebSocket. Run gọi qua API, run theo lịch và run được khôi phục đi qua hàng
đợi tới worker. Chi tiết:
[Kiến trúc](https://quinguyen1502.github.io/superstep/vi/reference/architecture/).

## Triển khai

**Demo trực tuyến:** [superstep-demo.onrender.com](https://superstep-demo.onrender.com) (bấm "Dùng thử demo"). Bản demo chạy trên gói miễn phí của Render: lần tải đầu có thể mất khoảng 30 giây trong lúc máy chủ khởi động lại, dữ liệu được đặt lại mỗi khi máy chủ nghỉ, và thay đổi không được lưu. Node Code, HTTP và Send email đang tắt, model trả lời bằng mock; xem [docs/deploy/demo.vi.md](docs/deploy/demo.vi.md).

Triển khai image all-in-one (giao diện, API và WebSocket trên một cổng; SQLite trên volume hoặc Postgres):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/quinguyen1502/superstep)
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/quinguyen1502/superstep)
[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/quinguyen1502/superstep/tree/main)
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=docker&image=ghcr.io/quinguyen1502/superstep:latest&name=superstep&ports=8000;http;/&env%5BSTUDIO_ADMIN_EMAILS%5D=&env%5BJWT_SECRET%5D=&env%5BSTUDIO_SECRET_KEY%5D=&env%5BDATABASE_URL%5D=)

Fly.io, Railway, Zeabur, Northflank, Coolify và Dokploy (cách đầy đủ tính năng với sandbox Docker), các biến thể Postgres và worker, tài khoản admin đầu tiên và các biến môi trường:
[`docs/deploy/`](docs/deploy/README.vi.md). Trên các nền tảng được quản lý, node Code chạy trực tiếp trên server (không có sandbox Docker); hãy đọc hướng dẫn trước.

## Tài liệu

| Chủ đề | Phần trong handbook |
| --- | --- |
| Cài đặt, bắt đầu nhanh, khái niệm | [Bắt đầu](https://quinguyen1502.github.io/superstep/vi/start/) |
| Trình soạn thảo, node, state, chế độ Code, kho tri thức, MCP | [Xây dựng](https://quinguyen1502.github.io/superstep/vi/guide/) |
| Trace, test, duyệt giữa chừng, API trigger, lịch chạy, chạy từ chat | [Chạy](https://quinguyen1502.github.io/superstep/vi/run/) |
| Triển khai, tài khoản, vai trò, nhà cung cấp, kênh duyệt | [Vận hành](https://quinguyen1502.github.io/superstep/vi/operate/) |
| Cấu hình, HTTP API, mã lỗi, kiến trúc | [Tham chiếu](https://quinguyen1502.github.io/superstep/vi/reference/) |
| Khởi chạy workflow từ dịch vụ khác: SDK Python và TypeScript, tham chiếu API công khai | [API công khai và SDK](https://quinguyen1502.github.io/superstep/vi/run/public-api/), [tham chiếu](https://quinguyen1502.github.io/superstep/vi/reference/public-api/) |

Mã nguồn handbook nằm ở [`handbook/`](handbook/README.md). Mọi biến môi trường
có trong [`.env.example`](.env.example) và mọi mã lỗi trong
[`docs/api-errors.md`](docs/api-errors.md).

## Phát triển

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run lint && npm test
cd frontend && npm run e2e
```

| Đường dẫn | Nội dung |
| --- | --- |
| `backend/app/` | App FastAPI: router → service → repository và engine LangGraph ([các lớp](docs/backend-architecture.md)) |
| `frontend/` | React, TypeScript, Vite, React Flow, Tailwind v4, shadcn/ui ([quy tắc UI](docs/ui-conventions.md)) |
| `handbook/` | Site tài liệu (Zensical) |
| `sdk/` | Client Python (`superstep`) và TypeScript (`@superstep/sdk`) cho API công khai ([SDK](sdk/README.md)); spec ở `docs/api/openapi.public.json` |
| `scripts/promo/` | Công cụ render video bắt đầu nhanh |
| `.factory-state/` | Requirement, decision, task, review và QA |

## Đóng góp

Thay đổi đi theo quy trình trong [`AGENTS.md`](AGENTS.md): một requirement và
một task trong `.factory-state/`, branch `factory/task-<id>-<name>`, kiểm tra,
review, và merge sau khi có người duyệt. Xem
[Phát triển](https://quinguyen1502.github.io/superstep/vi/reference/development/)
để biết cách cài môi trường test và quy ước của từng lớp.

## Giấy phép

[MIT](LICENSE)
