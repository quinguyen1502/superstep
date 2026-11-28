---
hide:
  - navigation
  - toc
---

# Tham chiếu API công khai

API khởi chạy workflow dùng workflow token. Chat API v1 công khai hỗ trợ
danh tính ẩn danh, người dùng Studio hoặc người dùng ứng dụng. Dataset
Connected v1 dùng Dataset API token. Phần tham chiếu bên dưới được dựng từ spec OpenAPI công khai,
[`openapi.public.json`](openapi.public.json) (cùng nội dung
với `docs/api/openapi.public.json` trong repository). Máy chủ đang chạy cũng
trả spec này tại `/openapi.public.json`, kèm giao diện Swagger tại
`/docs/public`.

Hướng dẫn từng bước với ví dụ curl, Python và TypeScript nằm ở
[API công khai và SDK](../run/public-api.md).
Về phiên chat và stream, xem [Chat API](../run/chat-api.md) và
[Xác thực bên thứ ba](../run/chat-third-party-auth.md). Frame socket được đặc
tả bằng AsyncAPI có link trong hướng dẫn chat; không phải thao tác HTTP bên dưới.

Để thao tác với các dòng trong Dataset, tạo token ở **Datasets → Access →
Dataset API tokens** và gửi qua `Authorization: Bearer dsat_…`. Phần Dataset
bên dưới có ví dụ request cho từng thao tác Find, Aggregate, Get, Insert,
Upsert và Delete. Dùng token đúng Dataset. Khi thử lại một yêu cầu ghi hoặc
xóa, gửi lại cùng `operation_id` và nội dung request.

<div id="api-reference" class="api-reference" data-spec="../openapi.public.json"></div>
<script src="../javascripts/vendor/redoc.standalone.js"></script>
<script src="../javascripts/api-reference.js"></script>
