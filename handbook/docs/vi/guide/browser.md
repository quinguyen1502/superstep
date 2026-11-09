# Công cụ trình duyệt (bản giao đầu)

Studio có thể mở **trình duyệt cách ly** cho bước Agent và recipe: navigate,
snapshot, extract, screenshot và các thao tác thay đổi tuỳ chọn (click, fill,
upload, download, evaluate). Kết nối nằm ở **Cài đặt → Máy chủ MCP**. Không gắn
URL khởi đầu trên kết nối — URL đến từ chat, state workflow hoặc công cụ tìm kiếm
đã cấu hình khi chạy.

Trang này là hướng dẫn thiết lập bản giao đầu bằng tiếng Việt. Xuất Python/TypeScript
có thể chạy các bước trình duyệt; xem mục xuất bên dưới.

## Trước khi bắt đầu

1. Discovery trình duyệt **bật mặc định**. Đặt `STUDIO_ENABLE_BROWSER=0` để ẩn
   adapter được quản lý `browser` / `web`. Các run tin cậy vẫn cần cổng runtime riêng
   (mặc định **tắt**) trước khi mở trình duyệt:

   ```bash
   # Tuỳ chọn: đây đã là mặc định
   STUDIO_ENABLE_BROWSER=1
   # Bắt buộc trước khi một run mở Chromium / controller từ xa
   STUDIO_ENABLE_BROWSER_RUNTIME=1
   ```

   Chỉ khám phá công cụ thì không khởi động Chromium.

2. Với provider **cục bộ**, build image worker và gateway (một lần trên mỗi máy chủ):

   ```bash
   docker build -t superstep-browser-worker:1 docker/browser-worker
   docker build -f docker/browser-gateway/Dockerfile -t superstep-browser-gateway:1 .
   ```

3. Với provider **từ xa** (self-hosted Superstep `browser_controller`, vẫn mang nhãn
   **Browserless** trong Cài đặt), chạy một controller mà máy chủ Studio gọi được
   qua HTTPS, rồi phê duyệt nó:

   ```bash
   # Trên máy chủ controller (ví dụ)
   export STUDIO_BROWSER_CONTROL_TOKEN='…32+ ký tự ASCII in được…'
   export STUDIO_BROWSER_CONTROL_ID='controller-1'
   python -m app.browser_controller

   # Trên Studio
   export STUDIO_BROWSER_CONTROLLERS='[{"endpoint":"https://browser.example.org","address":"203.0.113.10"}]'
   ```

   Token chỉ ghi trong Cài đặt. Không hỗ trợ endpoint CDP/WSS tuỳ ý.
   Xem [browser-remote.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-remote.md) về biên tin cậy.

## 1. Tạo kết nối trình duyệt

1. Mở **Cài đặt → Máy chủ MCP → Thêm máy chủ**.
2. Vận chuyển: **Kết nối được quản lý**.
3. Adapter: **Trình duyệt cách ly**.
4. Phạm vi: cá nhân (**Người dùng**), trừ khi admin cấu hình kết nối tổ chức.
5. Provider:
   - **Trình duyệt cách ly cục bộ (Docker)** — Studio khởi động worker trên máy này.
   - **Browserless (controller)** — dán token controller; endpoint phải đã có trong
     `STUDIO_BROWSER_CONTROLLERS`.
6. **Địa chỉ gốc được phép** (bắt buộc): mỗi dòng một origin `http(s)` chính xác,
   ví dụ `https://example.org`. Danh sách trống bị từ chối. Địa chỉ nội bộ vẫn bị
   chặn bởi chính sách mạng ngay cả khi liệt kê sai.
7. **Mạng / Proxy** tuỳ chọn: direct, mặc định của operator, hoặc proxy HTTP tuỳ chỉnh
   (Basic auth dùng username/password mã hoá riêng). Không hỗ trợ SOCKS.
   Lỗi proxy không bao giờ chuyển sang direct.
8. **Hồ sơ đăng nhập cá nhân** tuỳ chọn (chỉ phạm vi người dùng): tên, origin HTTPS
   của hồ sơ, và seed JSON storage-state Playwright có giới hạn kích thước.
9. **Công tắc an toàn** (mặc định):
   - Yêu cầu duyệt thao tác thay đổi — **tắt** (navigate / snapshot /
     extract / screenshot không bao giờ chờ).
   - Cho phép evaluate / upload / download — **tắt** cho đến khi bạn cần.
10. Lưu rồi **Khám phá công cụ**. Với công tắc an toàn để mặc định, dùng được
    sáu công cụ: navigate, snapshot, click, fill, extract và screenshot. Thẻ
    cũng liệt kê upload, download và evaluate, mỗi công cụ ghi rõ đang tắt trên
    kết nối này cho đến khi bật công tắc tương ứng.

![Cài đặt kết nối trình duyệt](../images/browser-connection-settings.png)

## 2. Gán công cụ trên Agent

1. Mở workflow, chọn node **Agent**.
2. **Cài đặt**: thêm công cụ MCP từ kết nối trình duyệt (`navigate`,
   `snapshot`, …). Công cụ thay đổi vẫn chịu công tắc của kết nối và,
   khi bật duyệt, phải qua Human review.
3. **Dữ liệu**: với mỗi công cụ trình duyệt cần URL, chọn **nguồn URL**:
   - **Agent điền** — từ chat / model (hỏi khi thiếu; không đoán site).
   - **URL cố định** — literal `https://…` mà model không ghi đè được.
   - **State workflow** — tham chiếu `{{state.…}}` được giải một lần lúc chạy.
4. **Thực thi**: hiện hạn mức kế thừa từ kết nối (số thao tác, idle, lifetime).
   Phiên giữ qua các lượt chat đến khi hết idle/lifetime tối đa hoặc hiệu ứng không chắc chắn.

Lưu workflow.

![Gán nguồn URL trên Agent](../images/browser-agent-url-binding.png)

## 3. Chạy một lượt chat

1. Mở chat của workflow (hoặc chat công khai dùng workflow đó).
2. Yêu cầu một trang trong whitelist, ví dụ “Mở https://example.org và
   tóm tắt tiêu đề.”
3. Agent nên gọi `navigate` rồi các công cụ chỉ-đọc. Lời gọi thay đổi hoặc
   chạy ngay (mặc định) hoặc chờ Human duyệt khi công tắc bật.
4. Trace Studio của chủ sở hữu có thể tải ảnh chụp riêng; chat công khai chỉ hiện
   các sự kiện trạng thái / thao tác / duyệt được phép — không có envelope thô của worker.

Nếu URL ngoài whitelist, run thất bại với mã từ chối riêng (không phải lỗi mạng
chung). Phiên mất hoặc hết hạn dừng mà không lặng lẽ chạy lại click.

## 4. Recipe dùng lại (tuỳ chọn)

Trên **Bắt đầu → Cài đặt**, bật **Recipe trình duyệt dùng lại**, chọn cùng
kết nối trình duyệt, rồi khai báo input/result kiểu dưới **Dữ liệu**. Các bước MCP
trình duyệt tuyến tính trên kết nối đó trở thành hợp đồng đóng mà Agent khác có thể
gọi như một công cụ workflow thông thường. Lỗi layout/selector dừng lại; chúng không
chuyển thành duyệt tự trị. Workflow ví dụ:
[`examples/browser/lookup_shipment.json`](https://github.com/quinguyen1502/superstep/blob/develop/examples/browser/lookup_shipment.json).

## 5. Xuất project Python

Tải file Python hoặc project LangGraph sau khi lưu workflow.
Bước trình duyệt thành `browser_call` trong file đó. File không import
Superstep và không chứa token controller, mật khẩu proxy hay trạng thái profile.

- Driver mặc định là `memory`: HTTP thư viện chuẩn trong whitelist origin, để
  fixture cục bộ chạy offline. `SUPERSTEP_BROWSER_DRIVER=playwright` dùng
  Chromium cục bộ. `browserless` đọc `SUPERSTEP_BROWSER_ENDPOINT_*` và
  `SUPERSTEP_BROWSER_TOKEN_*` từ môi trường. `.env.example` liệt kê các tên đó
  với giá trị trống. Playwright và Browserless giữ một trang đến khi hết
  idle, hết lifetime, hoặc tiến trình thoát. Click, fill và evaluate chạy trên
  trang đó. Mỗi bước redirect phải còn trong whitelist và không phải địa chỉ riêng.
  Driver memory không theo redirect.
- Sáu công cụ mặc định là navigate, snapshot, click, fill, extract và
  screenshot. Evaluate chỉ chạy khi kết nối cho phép. Upload và
  download bị từ chối ngoài Studio dù kết nối bật,
  vì runtime mang đi không có kho tệp đính kèm.
- Lệnh trên một phiên chạy lần lượt. Khi bật duyệt thao tác ghi, helper
  dừng bằng `interrupt()` trước hiệu ứng. Từ chối thì trang không đổi.
  Hiệu ứng mất hoặc không chắc chắn không bị chạy lại.
  `SUPERSTEP_BROWSER_FAULT` là móc thử một lần; hãy để trống.
- Bản xuất TypeScript dùng cùng helper `browserCall`. Playwright và
  Browserless giữ một trang đến khi hết idle, hết lifetime, hoặc tiến trình
  thoát. Click, fill và evaluate chạy trên trang đó. Mỗi bước redirect phải còn
  trong whitelist và không phải địa chỉ riêng. Driver memory không theo
  redirect. Chạy bằng Node (`npx tsx`) hoặc Deno. Playwright là tuỳ chọn
  `npm install playwright`.

## Rủi ro và quy tắc luôn bật

| Khu vực | Hành vi |
| --- | --- |
| Mạng | Whitelist origin chính xác bắt buộc; lỗi proxy không chuyển sang direct. |
| Bí mật | Token controller, mật khẩu proxy và trạng thái profile chỉ ghi. |
| Công cụ thay đổi | Mặc định tắt evaluate/upload/download; duyệt mặc định tắt nhưng không bỏ qua Human khi bật. |
| Nội dung trang | Không đáng tin; hiện đã escape trong trace chủ sở hữu; Studio không thực thi. |
| Controller từ xa | JSON tương thích không phải chứng nhận — chỉ endpoint operator phê duyệt mới chạy. |
| Stealth / CAPTCHA | Không hỗ trợ; không giải challenge tự động. |

## Ghi chú kỹ thuật liên quan

- Chi tiết UI kết nối: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-settings.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-settings.md)
- Worker cục bộ: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-runtime.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-runtime.md)
- Controller từ xa: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-remote.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-remote.md)
- Phiên: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-sessions.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-sessions.md)
- Duyệt: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-approvals.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-approvals.md)
- Editor / recipe / trace đã lọc: [https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-editor.md](https://github.com/quinguyen1502/superstep/blob/develop/docs/browser-editor.md)
