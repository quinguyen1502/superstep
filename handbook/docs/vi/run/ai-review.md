# AI duyệt yêu cầu phê duyệt

Một mô hình có thể xem yêu cầu phê duyệt trước người. Tính năng này dùng được
trên node **Human** và trên phần duyệt công cụ của node **Agent**. Người vẫn
quyết định: mô hình không bao giờ tự từ chối, và mọi trường hợp nó chưa chắc
đều chuyển cho người như bình thường.

## Chế độ

Chọn chế độ trong mục **AI duyệt** của node, dưới phần cài đặt phê duyệt.

| Chế độ | Điều gì xảy ra |
| --- | --- |
| Tắt | Mọi yêu cầu do người trả lời (mặc định). |
| Gợi ý | Mô hình nêu ý kiến (duyệt, từ chối hoặc chưa chắc, kèm độ tin cậy và lý do). Người vẫn trả lời. Ý kiến hiện trên trang **Duyệt** và trong tin nhắn gửi qua kênh. |
| Tự trả lời | Mô hình duyệt các yêu cầu mà nó chắc chắn. Mọi trường hợp khác chuyển cho người. |

Ai sửa được workflow đều chọn được **Gợi ý**. Chỉ chủ workflow hoặc quản trị
viên mới chọn được **Tự trả lời**, hoặc lưu thay đổi cho node đang dùng chế độ
này. Người khác nhận lỗi `AUTO_APPROVAL_FORBIDDEN`.

Hãy bắt đầu với **Gợi ý**. Mục này cho biết người đồng ý với mô hình bao nhiêu
phần trăm trong 30 ngày qua. Chỉ bật tự trả lời khi tỉ lệ này cao.

## Cài đặt

| Cài đặt | Ý nghĩa |
| --- | --- |
| Credential của mô hình duyệt | Bất kỳ credential chat nào. Việc duyệt là một lần gọi mô hình riêng. |
| Mô hình | Mô hình của credential đó. |
| Hướng dẫn | Điều mô hình duyệt cần biết, ví dụ "Hoàn tiền đến 50 USD cho khách hàng cũ là được." |
| Độ tin cậy tối thiểu | Từ 0 đến 1, mặc định 0,8. Thấp hơn thì yêu cầu chuyển cho người. |
| Số lần tự trả lời mỗi ngày | Theo từng workflow, mặc định 50, tối đa 10000. Ngày tính theo UTC. Quá giới hạn, yêu cầu chuyển cho người. |
| Báo | Báo cho người sở hữu run khi yêu cầu được tự trả lời. Chỉ người sở hữu run được báo. |
| Quy tắc | Được kiểm tra trước mô hình, xem bên dưới. |

## Quy tắc

Quy tắc xem một trường của yêu cầu; khi khớp, nó chuyển yêu cầu cho người hoặc
từ chối. Quy tắc không bao giờ duyệt.

- Trường: `tool` và `args.<tên>` (lệnh gọi công cụ của Agent), `prompt` và
  `state.<trường>` (node Human).
- Phép so sánh: bằng, khác, chứa, không chứa, khớp (biểu thức chính quy), lớn
  hơn, nhỏ hơn, trống.
- Khi nhiều quy tắc cùng khớp, từ chối thắng hỏi người.
- Tối đa 20 quy tắc mỗi node.

Ví dụ: `args.amount` lớn hơn `100`, thì **Hỏi người**.

Ở chế độ gợi ý, từ chối của quy tắc chỉ là gợi ý.

## Khi nào vẫn hỏi người

Yêu cầu chuyển cho người, như khi AI duyệt tắt, nếu:

- AI duyệt đang tạm dừng (xem bên dưới) hoặc bị tắt trên máy chủ;
- đã đạt giới hạn mỗi ngày;
- thiếu credential của mô hình duyệt, hoặc studio đang ở chế độ demo;
- lệnh gọi mô hình lỗi, quá 30 giây, hoặc trả về câu trả lời không hợp lệ;
- mô hình nghi yêu cầu đang cố ra lệnh cho nó (prompt injection);
- mô hình muốn từ chối, chưa chắc, hoặc độ tin cậy thấp hơn mức tối thiểu.

## Tạm dừng

- Trên trang **Duyệt**, khung **AI duyệt** liệt kê các workflow của bạn có
  dùng AI duyệt, kèm số liệu 30 ngày qua và tỉ lệ đồng ý. Chủ workflow hoặc
  quản trị viên có thể tạm dừng từng workflow tại đây.
- Quản trị viên có thể tạm dừng AI duyệt cho mọi workflow trong cùng khung.
- Người vận hành có thể tắt tự trả lời bằng `STUDIO_AUTO_APPROVAL=off`.

Tạm dừng không thay đổi workflow và không tạo phiên bản mới.

## Nhật ký

Mỗi lần duyệt được ghi trong nhật ký phê duyệt: kết quả, độ tin cậy, mô hình,
lý do, các quy tắc đã khớp và mã băm của chính sách. Khi người trả lời sau đó,
nhật ký ghi lại họ có đồng ý với mô hình hay không.

## Rủi ro

- **Quá tự tin.** Mô hình có thể chắc chắn mà vẫn sai. Hãy giữ độ tin cậy tối
  thiểu cao, dùng quy tắc cho những gì luôn phải đến tay người, và theo dõi tỉ
  lệ đồng ý.
- **Prompt injection.** Yêu cầu có thể chứa chữ do người khác viết. Mô hình
  duyệt chỉ coi yêu cầu là dữ liệu, và khi nghi có injection thì chuyển cho
  người. Quy tắc chạy trước mô hình nên không thể bị thuyết phục.
- **Chi phí.** Mỗi lần duyệt là một lần gọi mô hình trên credential đó.

## Xuất code

Bản xuất Python, TypeScript và dự án LangGraph chỉ giữ đồ thị: ở đó người trả
lời mọi yêu cầu, và có ghi chú trong code. Xuất workflow và template giữ cài
đặt AI duyệt nhưng bỏ credential của mô hình duyệt.

Xem thêm [Duyệt bởi người](human-approval.md) và [node Agent](../guide/agent.md).
