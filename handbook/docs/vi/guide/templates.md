# Mẫu workflow

**Workflow mới** mở thư viện mẫu.

![Thư viện mẫu](../images/templates.png)

| Nhóm | Nội dung |
| --- | --- |
| Workflow trống | Chỉ có Start và End. |
| Có sẵn | Mười ba mẫu ở dưới. |
| Chỉ mình tôi | Các mẫu bạn đã lưu. |
| Toàn tổ chức | Các mẫu chia sẻ cho mọi người. |

Mỗi thẻ có bản xem trước của graph. Tạo từ mẫu sẽ chép nó thành một workflow
mới do bạn sở hữu. Tên và mô tả của
mẫu có sẵn hiện theo ngôn ngữ giao diện.

## Mẫu có sẵn

| Mẫu | Làm gì |
| --- | --- |
| **Chatbot** | Một LLM trả lời tin nhắn của người dùng. |
| **Hỏi đáp RAG** | Tìm các đoạn liên quan trong kho tri thức rồi trả lời dựa trên đó. |
| **Quy trình duyệt** | Soạn câu trả lời, nhờ người duyệt trong studio, rồi chỉnh lại hoặc dừng. |
| **Định tuyến** | Phân loại yêu cầu rồi chuyển tới nhánh chuyên trách. |
| **Duyệt hoàn tiền** | Tài chính duyệt hoàn tiền trên Slack. Khách nhận email xác nhận, hoặc thư từ chối lịch sự do LLM soạn. |
| **Đơn nghỉ phép** | Quản lý duyệt đơn nghỉ trên Microsoft Teams. Nhân viên nhận kết quả qua email, HR được cc. |
| **Duyệt bài đăng mạng xã hội** | Biên tập viên duyệt bài trên Telegram, hoặc trả lời kèm góp ý để bài được viết lại và gửi duyệt lại. |
| **Kiểm tra đơn hàng lớn** | Node Decision đánh giá từng đơn. Đơn có rủi ro chờ quản lý bán hàng xác nhận trên WhatsApp; đơn khác đi thẳng. |
| **Duyệt chi phí công tác** | LLM đối chiếu khoản chi với chính sách công tác, người duyệt trả lời qua link email, rồi nhân viên được báo kết quả. |
| **Đề nghị mua sắm** | Trưởng nhóm duyệt trên Slack, sau đó tài chính duyệt qua email. Người đề nghị luôn nhận kết quả. |
| **Hỗ trợ có chuyển cấp** | Trả lời từ kho tri thức; node Decision chuyển câu trả lời chưa chắc chắn cho nhân viên hỗ trợ trong studio. |
| **Tổng hợp phản hồi khách hàng** | Vòng For each gắn nhãn từng phản hồi, rồi LLM viết báo cáo và gửi email cho team. |
| **Agent hỗ trợ khách hàng** | Một [node Agent](agent.md) tra cứu đơn hàng và chính sách hoàn tiền; mỗi yêu cầu hoàn tiền của agent đều cần người duyệt. |
| **Đội hỗ trợ** | Một agent điều phối giao mỗi câu hỏi cho một [công cụ workflow](agent.md#workflow-lam-cong-cu) chuyên trách: Order desk hoặc Refund desk. Dùng mẫu sẽ tạo cả ba workflow. |
| **Bàn hỗ trợ** | Triage trả lời câu hỏi về đơn hàng và [chuyển giao](handoffs.md) câu hỏi thanh toán cho Billing, sự cố kỹ thuật cho Kỹ thuật. Trong chat, tin nhắn tiếp theo ở lại với agent vừa trả lời. |

Mẫu có kênh duyệt chỉ ghi loại kênh. Sau khi tạo, chọn kết nối, người nhận và
người duyệt trên node Human (xem [Kênh duyệt](../operate/channels.md)). Trước
đó, run sẽ dừng chờ ở node Human và có thể duyệt ngay trong studio. **Hỏi đáp
RAG**, **Hỗ trợ có chuyển cấp** và **Agent hỗ trợ khách hàng** cần một kho tri
thức trước khi chạy: workflow mới mở ra đã báo điều này ở panel Chạy, và ô chọn
kho tri thức của node được đánh dấu cho tới khi bạn chọn một kho.

Mỗi mẫu có sẵn đi kèm một đến ba test case cho thấy mẫu dùng để làm gì, ví dụ
"Approved leave" và "Rejected leave". Workflow tạo từ mẫu có các test case này
trong tab **Test**, và chúng đạt với model mock offline (xem
[Kiểm thử workflow](../run/tests.md)). Mẫu bạn tự lưu không kèm test case.

Mỗi node Human có kênh duyệt còn có [hạn chờ](../run/human-approval.md#han-cho)
phù hợp với quy trình, ví dụ đơn nghỉ phép chờ 2 ngày, nhắc mỗi ngày, rồi từ chối.
Duyệt bài đăng mạng xã hội sẽ tự duyệt nếu biên tập viên không trả lời trong một
ngày. Bạn có thể đổi hoặc tắt hạn chờ trên node.

## Lưu thành mẫu

**⋯ → Lưu thành mẫu** chép **phiên bản đã lưu gần nhất** của workflow (muốn có
các sửa đổi chưa lưu thì lưu trước). Chọn tên, mô tả và ai được thấy. Phạm vi
tổ chức cần quyền `org.manage`.

Mẫu không bao giờ mang theo credential, kho tri thức, máy chủ MCP, kết nối kênh
duyệt, người nhận hay người duyệt, liên kết subgraph, header hay API key, kể cả
trong các công cụ của node Agent. Các trường đó được để trống, sau khi tạo bạn tự chọn lại. Node Human chỉ giữ loại kênh
mà nó dùng, và hạn chờ của nó (không kèm địa chỉ chuyển tiếp).

## Xuất và nhập

**Xuất** trên một thẻ ghi ra file `*.template.json`:

```json
{"format": "superstep/template", "version": 1,
 "name": "…", "description": "…", "workflow": {"state": [], "nodes": [], "edges": []}}
```

**Nhập mẫu** trong thư viện đọc lại file đó. Mẫu có node Code cần quyền
`code.write` để nhập hoặc dùng.

Xoá mẫu cần gõ đúng tên mẫu. Các workflow đã tạo từ mẫu không bị ảnh hưởng.
