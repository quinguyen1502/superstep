# Phát triển

## Cấu trúc repo

| Đường dẫn | Nội dung |
| --- | --- |
| `backend/app/` | App FastAPI, chia lớp `core / models / schemas / repositories / services / api / engine` |
| `backend/tests/` | Bộ test pytest, gồm cả kiểm tra lớp, envelope và danh mục lỗi |
| `frontend/` | React, TypeScript, Vite, React Flow, Tailwind v4, shadcn/ui |
| `frontend/e2e/` | Các spec Playwright |
| `docker/studio-code/` | Image sandbox cho chế độ Code |
| `handbook/` | Trang này (Zensical, cấu hình dạng MkDocs) |
| `scripts/` | Smoke test cho Compose, công cụ render video bắt đầu nhanh |
| `docs/` | Danh mục lỗi, kiến trúc backend và quy ước UI |
| `.env.example` | Mọi biến cho Compose và lúc chạy |
| `.factory/`, `.factory-state/` | Quy trình giao việc: requirement, decision, task, review và QA |

## Test

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run lint && npm test
```

Cài backend bằng `pip install -e "backend[dev]"`. Chạy với Postgres và Redis ở
máy:

```bash
cd backend
DATABASE_URL=postgresql://… TEST_DATABASE_URL=postgresql://… \
  REDIS_URL=redis://localhost:6379/0 .venv/bin/python -m pytest -q
```

Test Postgres cần một role có quyền `CREATEDB`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) chạy pytest trên Python 3.12 (cả
trên Postgres 17 và Redis 7), lint và build frontend trên Node 20 và 22, và một smoke
test cho Compose. `handbook.yml` build handbook này ở chế độ strict và xuất bản
từ `main`. `factory-verify.yml` kiểm tra metadata của factory. Test end-to-end
không chạy trên CI.

## Test end-to-end

Playwright tự khởi động API riêng ở cổng 8100 (database tạm), Vite ở 5190, một
API chat giả và một SMTP sink.

```bash
cd frontend && npx playwright install chromium
npm run e2e
```

| Biến | Tác dụng |
| --- | --- |
| `PW_CHROME` | Dùng Chrome đã cài thay cho Chromium của Playwright |
| `E2E_UVICORN`, `E2E_PYTHON` | Ghi đè đường dẫn binary của backend |
| `E2E_API_PORT`, `E2E_UI_PORT` | Chạy song song hai bản checkout |
| `E2E_CODE_RUNTIME=subprocess` | Chạy các spec chế độ Code khi không có Docker |

CI chạy toàn bộ bộ test (tiếng Anh và tiếng Việt) trên mọi pull request trong job
`E2E (Playwright)`, chia thành ba phần bằng `--shard`, có cache Chromium và
`E2E_CODE_RUNTIME=subprocess`. Test không được chạy lại: test chập chờn được sửa tận
gốc. Khi một phần lỗi, trace và ảnh chụp màn hình được tải lên thành artifact
`e2e-shard-N` (giữ 7 ngày); mở trace bằng `npx playwright show-trace`.

## Ảnh chụp cho handbook

```bash
cd frontend && HANDBOOK_SHOTS=1 npm run e2e -- handbook quickstart
```

`e2e/handbook.spec.ts` tạo các workflow mẫu, chạy chúng và ghi
`handbook/docs/<en|vi>/images/*.png` ở 1440 × 900. Ảnh chế độ Code cần Docker
và image `studio-code:1`. `e2e/quickstart.spec.ts` làm theo
[Bắt đầu nhanh](../start/quickstart.md) trên giao diện, ghi ảnh chụp và lưu các
khung hình dùng cho video.

## Handbook

```bash
cd handbook
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/zensical serve -a 127.0.0.1:8001
```

Site được build bằng [Zensical](https://zensical.org) từ cấu hình dạng MkDocs.
Tiếng Anh (`docs/en/`, `mkdocs.yml`) ở `/`, tiếng Việt (`docs/vi/`,
`mkdocs.vi.yml`) ở `/vi/`; hai bản dùng chung `mkdocs.base.yml` và cùng một cây
trang. `strict: true` làm build lỗi khi có link hoặc anchor hỏng. Trang
[Mã lỗi](errors.md) lấy nội dung từ `docs/api-errors.md`. Lệnh build xem
`handbook/README.md`.

## Video bắt đầu nhanh

`scripts/promo/` render video ở trang chủ từ các khung hình do
`e2e/quickstart.spec.ts` ghi lại: một timeline HTML đưa con trỏ tới đúng vị
trí đã ghi của từng control, Chrome render từng khung hình, và ffmpeg ghép lại
cùng một đoạn nhạc tự tổng hợp. Xem `scripts/promo/README.md`.

## Quy trình đóng góp

Công việc theo AI Software Factory trong `.factory/` (xem `AGENTS.md`):
requirement, decision và task nằm trong `.factory-state/`, mỗi task có một
branch `factory/task-<id>-<name>`, và merge cần người duyệt. Thay đổi backend
giữ đúng các lớp; thay đổi schema đi qua Alembic; mã lỗi mới thêm vào danh mục,
`docs/api-errors.md` và cả hai file ngôn ngữ; chuỗi giao diện thêm vào cả hai
file ngôn ngữ.

Code frontend theo `docs/ui-conventions.md`. Quy tắc căn chỉnh trong đó (dùng
size variant của shadcn thay vì tự đặt chiều cao, padding hay line height;
thanh công cụ là một hàng `flex items-center`) được kiểm tra ở hai chỗ:
`npm run lint` chạy `scripts/check-ui-classes.mjs`, và `e2e/alignment.spec.ts`
đo các thanh công cụ chính bằng `e2e/helpers/alignment.ts`. Ngoại lệ có lý do
chính đáng thì ghi chú thích `ui-class-ok: <lý do>` ngay trên phần tử.
