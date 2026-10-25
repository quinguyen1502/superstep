# Chat

Khung **Chat** ở bên phải editor cho bạn trò chuyện với một workflow như
người chat sẽ làm. Mỗi tin nhắn chạy một run của workflow **đã lưu**; các bước
và câu trả lời hiện dần trong lúc run chạy, và cuộc trò chuyện được lưu lại để
workflow có thể nhớ.

![Khung Chat cạnh canvas](../images/chat-tab.png)

## Mở khung chat

- Nút **Chat** trên thanh trên, hoặc ++shift+c++ trên canvas, mở và đóng khung.
  Khung vẫn mở, đúng độ rộng bạn đã kéo (340–760 px), ở lần mở editor sau trên
  trình duyệt này.
- **Cấu hình** vẫn ở cạnh, nên bạn sửa một node rồi thử lại được ngay.
- **Toàn màn hình** (nút mũi tên) hiện chat trên cả cửa sổ, với danh sách các
  cuộc trò chuyện ở bên trái. ++esc++ để quay lại; cuộc trò chuyện và nội dung
  đang gõ vẫn còn.
- Trong khung hẹp, chọn cuộc trò chuyện cũ ở menu chọn cuộc trò chuyện cạnh **Xem dưới góc
  nhìn**, hoặc bắt đầu cuộc mới bằng nút **Chat mới** (biểu tượng bút).

![Chat toàn màn hình](../images/chat-fullscreen.png)

!!! note "Giai đoạn 1"
    Chat hiện dùng trong studio, cho những người được chạy workflow. Link chat
    công khai, người chat đã đăng nhập, tệp đính kèm và widget nhúng sẽ có sau;
    phần cài đặt đã chừa chỗ cho chúng.

## Bật chat

1. Mở workflow và chọn **⋯ → Cài đặt Chat**, hoặc nút bánh răng trong khung Chat.
   Bạn cần quyền chủ sở hữu để đổi cài đặt (chủ workflow hoặc admin).
2. Bật **Chat** và kiểm tra các trường:
    - **Trường tin nhắn**: trường state nhận mỗi tin nhắn (`string` hoặc `list`).
    - **Trường trả lời**: trường state hiện làm câu trả lời.
    - **Trường cuộc trò chuyện**: một trường `list` nhận các tin nhắn trước đó
      (xem [Bộ nhớ](#bo-nho)). Chọn **Không** cho chat không nhớ.
3. Lưu. Khi lưu, các trường được kiểm tra có trong state của workflow.

![Cài đặt Chat](../images/chat-settings.png)

| Cài đặt | Tác dụng | Mặc định |
|---|---|---|
| Ai được chat | Hiện chỉ **Người dùng studio**. *Ai có link* và *Người đã đăng nhập* có trong danh sách nhưng chưa dùng được. | Người dùng studio |
| Số lượt nhớ | Số lượt hỏi–đáp trước đó (một tin nhắn và câu trả lời của nó) gửi vào trường cuộc trò chuyện. | 10 |
| Bước hiện cho người chat | **Không**, **Tên bước** hoặc **Đầy đủ** (kèm input và output của từng bước). | Tên bước |
| Thời gian lưu (ngày) | Cuộc trò chuyện không có tin nhắn mới quá thời gian này sẽ bị xoá. | 30 |

## Trò chuyện

Nhập tin nhắn rồi nhấn ++enter++ (++shift+enter++ để xuống dòng). Câu trả lời
là Markdown: danh sách, bảng, link và khối code được định dạng; HTML thô và ảnh
từ trang khác không hiện, link mở ở tab mới.

- **Cuộc trò chuyện mới** bắt đầu một cuộc trò chuyện chưa có gì để nhớ. Các
  cuộc trò chuyện cũ vẫn ở danh sách, mới nhất trên cùng, đặt tên theo tin nhắn
  đầu tiên.
- **Xem dưới góc nhìn** ở trên cùng đổi cách xem. *Người dựng workflow* thấy đầy
  đủ mọi bước, kèm input và output (bấm vào một bước để mở); *Khách chat* xem
  trước đúng như khách thấy trên trang chat công khai: những gì **Bước hiện cho
  người chat** cho phép. Khi khung Chat hẹp, nút đổi cách xem hiện nhãn ngắn
  **Người dựng** hoặc **Khách** và chứa luôn **Cài đặt Chat**; khi đang xem như
  khách, một dải phía trên cuộc trò chuyện báo điều đó, kèm **Về góc nhìn người dựng**.

![Xem trước như khách chat](../images/chat-visitor.png)
- Mỗi tin nhắn là một run trong lịch sử run (**Chạy → Xem tất cả**) với nhãn
  *Chat*, nên bạn mở được trace đầy đủ ở đó.
- Chat dùng workflow đã lưu: hãy lưu thay đổi trước khi thử.

## Bộ nhớ

Khi có trường cuộc trò chuyện, mỗi run nhận *n* lượt hỏi–đáp gần nhất cùng tin
nhắn mới trong trường đó, dạng list các mục `{"role": "user" | "assistant",
"content": "…"}`. Dùng nó trong prompt, ví dụ:

```text
Cuộc trò chuyện đến giờ:
{{state.messages}}

Trả lời tin nhắn cuối của người dùng.
```

## Node Human trong chat

Tuỳ chọn **Người trả lời** của node Human quyết định ai trả lời khi workflow
chạy từ chat:

- **Người chat** (mặc định): câu hỏi hiện trong chat với **Duyệt** và **Từ chối**;
  hoặc nhập câu trả lời vào ô tin nhắn. Câu trả lời vào trường output của node và run chạy tiếp.
- **Người duyệt**: chat báo đang chờ duyệt, còn câu hỏi đến trang
  [Duyệt](human-approval.md) (và các kênh của nó) như thường lệ. Chat hiện câu
  trả lời khi run chạy tiếp.

Bước duyệt công cụ của [node Agent](../guide/agent.md#duyet-truoc-khi-goi-cong-cu)
luôn do người duyệt trả lời: người chat không duyệt hành động của chính agent.

Không gửi được tin nhắn mới khi chat đang chờ trả lời. [Hạn chờ](human-approval.md#han-cho)
của node áp dụng cho cả hai cách; khi quá hạn, hành động khi hết hạn quyết định
điều gì xảy ra.

## Lỗi

| Mã | Ý nghĩa |
|---|---|
| `CHAT_NOT_ENABLED` | Chat đang tắt cho workflow này. |
| `CHAT_SETTINGS_INVALID` | Một cài đặt bị sai; `field` cho biết cài đặt nào. |
| `CHAT_ACCESS_NOT_AVAILABLE` | Lựa chọn *Ai được chat* đó chưa dùng được. |
| `CHAT_SESSION_NOT_FOUND` | Cuộc trò chuyện không tồn tại, hoặc không phải của bạn. |
| `CHAT_MESSAGE_EMPTY` / `CHAT_MESSAGE_TOO_LONG` | Tin nhắn trống, hoặc dài quá 4000 ký tự. |
| `CHAT_RUN_WAITING` | Chat đang chờ câu trả lời cho một node Human. |
| `CHAT_ANSWER_BY_REVIEWER` | Bước này do người duyệt trả lời, ở trang Duyệt. |

Xem thêm [Chạy từ chat](chat-triggers.md) cho Slack và Telegram.
