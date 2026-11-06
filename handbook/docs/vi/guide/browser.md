# Công cụ trình duyệt (bản giao đầu)

Studio có thể mở **trình duyệt cách ly** cho bước Agent và recipe: navigate,
snapshot, extract, screenshot và các thao tác thay đổi tuỳ chọn (click, fill,
upload, download, evaluate). Kết nối nằm ở **Cài đặt → Máy chủ MCP**. Không gắn
URL khởi đầu trên kết nối — URL đến từ chat, state workflow hoặc công cụ tìm kiếm
đã cấu hình khi chạy.

Bản giao Studio đầu tiên ưu tiên hướng dẫn tiếng Anh (Guide → Browser tools;
ảnh minh hoạ chỉ tiếng Anh). Trang này tóm tắt cùng các bước bằng tiếng Việt. Xuất Python/TypeScript vẫn để sau
(TASK-0251/0252).

## Trước khi bắt đầu

1. Bật hai cổng trên API/worker Studio (mặc định **tắt**):

   ```bash
   STUDIO_ENABLE_BROWSER=1
   STUDIO_ENABLE_BROWSER_RUNTIME=1
   ```

2. Provider **cục bộ**: build image worker và gateway một lần trên máy chủ.
3. Provider **từ xa** (self-hosted Superstep `browser_controller`, nhãn
   **Browserless** trong Cài đặt): chạy controller HTTPS và khai báo
   `STUDIO_BROWSER_CONTROLLERS`. Không hỗ trợ CDP/WSS tuỳ ý.

## 1. Tạo kết nối trình duyệt

1. **Cài đặt → Máy chủ MCP → Thêm máy chủ**.
2. Vận chuyển: **Kết nối được quản lý** · Adapter: **Trình duyệt cách ly**.
3. **Địa chỉ gốc được phép** (bắt buộc): mỗi dòng một origin `http(s)` chính xác.
   Danh sách trống bị từ chối.
4. Proxy HTTP tuỳ chọn (không SOCKS; lỗi proxy không chuyển sang direct).
5. Công tắc an toàn: phê duyệt thao tác thay đổi mặc định **tắt**; evaluate/
   upload/download mặc định **tắt**.
6. Lưu rồi **Khám phá công cụ**.

![Cài đặt kết nối trình duyệt](../images/browser-connection-settings.png)

## 2. Gán công cụ trên Agent

1. Chọn node **Agent** → **Cài đặt**: thêm công cụ MCP từ kết nối trình duyệt.
2. **Dữ liệu**: chọn **nguồn URL** (Agent điền / URL cố định / state workflow).
3. **Thực thi**: xem hạn mức kế thừa (số thao tác, idle, lifetime). Phiên giữ
   qua các lượt chat đến khi hết hạn hoặc hiệu ứng không chắc chắn.

![Gán nguồn URL trên Agent](../images/browser-agent-url-binding.png)

## 3. Chạy một lượt chat

Mở chat của workflow, yêu cầu một trang trong whitelist. Agent gọi `navigate`
rồi công cụ chỉ-đọc. URL ngoài whitelist bị từ chối riêng. Trace chủ sở hữu có
thể tải ảnh chụp riêng; chat công khai chỉ thấy sự kiện được phép.

## 4. Recipe (tuỳ chọn)

Trên **Bắt đầu → Cài đặt**, bật recipe trình duyệt dùng lại, chọn cùng kết nối,
khai báo input/result ở **Dữ liệu**. Ví dụ:
[lookup_shipment.json](https://github.com/quinguyen1502/superstep/blob/develop/examples/browser/lookup_shipment.json).
