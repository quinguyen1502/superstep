# Tương thích Public Chat API

Chính sách này áp dụng cho HTTP và giao thức socket của Chat API công khai,
có hiệu lực cùng handbook Chat API giai đoạn 1. Endpoint workflow trigger
và API nội bộ studio có hợp đồng riêng.

## Phiên bản và thay đổi bổ sung

Client mới cố định `/api/public/v1/chat/{slug}` và
`/ws/public/v1/chat/{slug}`. `v1` trong URL là phiên bản major API. Phiên
bản tài liệu OpenAPI/AsyncAPI mô tả tài liệu của chúng; không chọn endpoint
khác và không thay thế major API.

Trong v1 chỉ thay đổi bổ sung: có thể thêm trường response tùy chọn và kiểu
event server mới. Client phải bỏ qua trường response và kiểu event chưa
biết, đồng thời tiếp tục hỗ trợ các trường/event đã biết. Chỉ gửi trường
frame client được tài liệu quy định. Xóa, đổi tên hợp đồng bắt buộc hiện có
hoặc đổi nghĩa không tương thích yêu cầu major API mới (`v2`).

Major SDK đi theo major API công khai khi chat SDK được phát hành. Các
helper chạy workflow của SDK đang phát hành không có nghĩa helper chat
hay toolkit React/native trong kế hoạch đã sẵn sàng.

## Đường dẫn cũ

| Đường dẫn | Hành vi hiện tại |
| --- | --- |
| `/api/public/chat/{slug}/...` | HTTP alias cũ của handler v1; tích hợp mới dùng URL có phiên bản |
| `/ws/public/chat/{slug}` | Socket cũ cùng origin, dùng `{chat_session_id,message}` / `{chat_session_id,response}` không có kiểu; phát `node_token`, `run_summary` |
| `/ws/public/v1/chat/{slug}` | `message`/`answer` có kiểu, `auth` đầu tùy chọn; phát `token`, `done`, `v`, `seq` riêng mỗi kết nối |

Đường dẫn cũ không được khuyến khích cho tích hợp mới nhưng vẫn hoạt động
khi trang/widget có sẵn còn dùng chúng. Socket cũ **không** là alias của
giao thức v1 có kiểu: cần đổi cả cách phân tích frame lẫn URL. Xác thực
user bên thứ ba khác origin dùng socket v1. Xem [Chat API](../run/chat-api.md).

## Ngừng khuyến khích và ngừng hỗ trợ

Phiên bản kế tiếp có thay đổi phá vỡ tương thích được phát hành trên đường
dẫn major mới. v1 được hỗ trợ **ít nhất 12 tháng sau khi v2 phát hành**.
Khi chính thức deprecate một phiên bản, response của nó sẽ có header
`Deprecation` và `Sunset`, cùng thông báo chuyển đổi và ngày ngừng hỗ trợ
đảm bảo thời gian tối thiểu đó. Chưa công bố v2 hay ngày sunset v1, và các
header này chưa được bật. Đây là cam kết chính sách, không phải thông báo
đã có lịch ngừng hỗ trợ.

## Checklist nâng cấp

1. Đọc [changelog](https://github.com/quinguyen1502/superstep/blob/develop/CHANGELOG.md)
   và thông báo chuyển đổi của phiên bản đích.
2. So sánh [OpenAPI JSON](openapi.public.json),
   [AsyncAPI](https://github.com/quinguyen1502/superstep/blob/develop/docs/asyncapi/chat-v1.yaml)
   và [schema frame](https://github.com/quinguyen1502/superstep/tree/develop/backend/app/api/schemas/chat_ws_v1).
3. Kiểm tra xác thực/làm mới, stream hoàn tất và bị ngắt, trả lời Human,
   tệp, đánh giá và khôi phục từ lượt đã lưu.
4. Cố định đường dẫn API và phiên bản SDK tương thích, xử lý field/event
   tùy chọn chưa biết. Test major mới trước khi chuyển lưu lượng.
