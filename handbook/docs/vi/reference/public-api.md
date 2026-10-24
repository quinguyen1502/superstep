---
hide:
  - navigation
  - toc
---

# Tham chiếu API công khai

API khởi chạy workflow mà các dịch vụ khác gọi bằng token của workflow. Phần
tham chiếu bên dưới được dựng từ spec OpenAPI công khai,
[`openapi.public.json`](openapi.public.json) (cùng nội dung
với `docs/api/openapi.public.json` trong repository). Máy chủ đang chạy cũng
trả spec này tại `/openapi.public.json`, kèm giao diện Swagger tại
`/docs/public`.

Hướng dẫn từng bước với ví dụ curl, Python và TypeScript nằm ở
[API công khai và SDK](../run/public-api.md).

<div id="api-reference" class="api-reference" data-spec="../openapi.public.json"></div>
<script src="../javascripts/vendor/redoc.standalone.js"></script>
<script src="../javascripts/api-reference.js"></script>
