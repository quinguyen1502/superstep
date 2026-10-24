# Chế độ demo công khai

`STUDIO_DEMO_MODE=true` biến một máy chủ thành bản demo công khai, dùng xong bỏ. Bản demo
trực tuyến ở https://superstep-demo.onrender.com (gói miễn phí của Render, Singapore). Không
bao giờ bật chế độ này cho công việc thật.

## Thiết kế: mỗi khách một tài khoản riêng, chỉ cho xem

Trang đăng nhập có nút **Dùng thử demo**. Nút này đăng nhập bằng `demo@superstep.dev` với
mật khẩu công khai. Tài khoản đó được tạo lại mỗi lần khởi động với vai trò **viewer**; mỗi lần
đăng nhập bằng nó tạo một tài khoản khách ẩn danh mới của riêng người đó (cũng là viewer, được
chia sẻ các workflow mẫu chỉ cho xem), nên lịch sử run, cuộc trò chuyện, run đang chờ và thông
báo của mỗi khách là riêng. Các
quy tắc vai trò sẵn có đã chặn nó khỏi credential, kho tri thức, API token, máy chủ MCP, kết
nối duyệt, việc tạo workflow và mọi trang quản trị. Chế độ demo thêm:

| Phần | Ở chế độ demo |
| --- | --- |
| Ghi dữ liệu | API từ chối mọi thao tác ghi của tài khoản khách, trừ đăng nhập, đăng xuất, huỷ run, trả lời node Human, đánh dấu thông báo đã đọc và bắt đầu hoặc xoá cuộc trò chuyện trong khung Chat (`403 DEMO_READ_ONLY`). Khách không lưu, chia sẻ, đổi tên hay xoá workflow, và không đổi được tài khoản (mật khẩu, tuỳ chọn, tài khoản liên kết). |
| Đăng ký, đặt lại mật khẩu | Đóng với mọi người (`DEMO_READ_ONLY`), để không ai tạo được tài khoản có nhiều quyền hơn. |
| Chạy | Khách có thể chạy các chỉnh sửa **chưa lưu** trong trình soạn thảo. Không thay đổi nào được lưu. |
| Node Code | Tắt, máy chủ bắt buộc (`DEMO_CODE_DISABLED`); trình soạn thảo ghi rõ lý do. |
| Node HTTP Tool và Send email | Bị từ chối khi chạy (`DEMO_NODE_DISABLED`), nên run không gọi ra ngoài. |
| Node LLM và Decision | Luôn dùng model mock ngoại tuyến, kể cả khi có `OPENAI_API_KEY`. Không gọi nhà cung cấp nào. Câu trả lời mock (và tool mẫu `lookup_order`) theo ngôn ngữ giao diện của khách, tiếng Anh hoặc tiếng Việt. |
| Dữ liệu của khách | Tài khoản khách cũ hơn `STUDIO_DEMO_VISITOR_TTL` giây (mặc định 86400, một ngày) bị xoá cùng các run và cuộc trò chuyện, mỗi lần khởi động và mỗi lần đăng nhập demo. |
| Giới hạn tần suất | `STUDIO_DEMO_RUN_RATE_LIMIT` run mỗi IP mỗi phút (mặc định 20; `RATE_LIMITED`). |
| Workflow mẫu | Example, Chatbot (kiểu chat: `message` vào, `answer` ra, bật chat web cho khung Chat), Router và Approval flow được tạo và chia sẻ cho khách mỗi lần khởi động, vì gói miễn phí xoá file SQLite khi dịch vụ nghỉ. |
| Thông báo | Mọi trang có một thông báo nhỏ: đây là bản demo, dữ liệu được đặt lại, lần tải đầu có thể mất khoảng 30 giây. |

Admin (`STUDIO_ADMIN_EMAILS` cùng `STUDIO_ADMIN_PASSWORD` cố định) là tài khoản bình thường,
không bị giới hạn; hãy giữ kín mật khẩu đó.

Giới hạn, nói thẳng: lịch sử của khách chỉ tồn tại trong phiên của họ (đăng nhập lại là một
khách mới), và admin thấy các tài khoản khách trong danh sách người dùng. Node MCP và Retriever không có gì để dùng (không có máy chủ MCP hay kho
tri thức). Thời gian chạy tối đa và giới hạn kích thước input giữ như bình thường.

## Tự chạy một bản demo

```bash
STUDIO_DEMO_MODE=true
STUDIO_SECRET_KEY=<ngẫu nhiên>  JWT_SECRET=<ngẫu nhiên>
STUDIO_ADMIN_EMAILS=you@example.com  STUDIO_ADMIN_PASSWORD=<ngẫu nhiên, từ 8 ký tự, có chữ và số>
```

Trên Render: một web service Docker miễn phí từ repo này, với các biến ở trên. Không cần
disk: bản demo vốn để đặt lại.
