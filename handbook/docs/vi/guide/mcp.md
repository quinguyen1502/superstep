# Máy chủ MCP

Máy chủ [Model Context Protocol](https://modelcontextprotocol.io) cung cấp
công cụ. Đăng ký máy chủ một lần, rồi gọi công cụ của nó từ các node
[MCP tool](nodes.md#mcp-tool).

![Máy chủ MCP](../images/settings-mcp.png)

## Trước khi bắt đầu

- Vai trò `admin` hoặc `editor` cho server cá nhân. Server của tổ chức và lệnh
  stdio cần admin.
- Server hỗ trợ Streamable HTTP, hoặc với stdio, `STUDIO_MCP_STDIO=1` trên máy
  chạy API.

## Đăng ký máy chủ

Mở **Cài đặt → Máy chủ MCP**, chọn **Thêm máy chủ MCP**.

=== "Streamable HTTP"

    Một URL và header bí mật (tuỳ chọn). URL phải là địa chỉ công khai; kết nối
    được ghim vào IP đã kiểm tra. Địa chỉ private và loopback (ví dụ một
    container sidecar) cần `STUDIO_MCP_ALLOW_PRIVATE=1`.

=== "stdio"

    Một lệnh, các tham số (mỗi dòng một tham số) và biến môi trường bí mật, chạy như process con của API. Stdio tắt cho tới khi
    `STUDIO_MCP_STDIO=1`, và chỉ admin mới đăng ký được lệnh. Process nhận môi
    trường sạch, thư mục home tạm rỗng và `STUDIO_MCP_TIMEOUT` giây (mặc định
    30), sau đó cả nhóm process bị kill.

    !!! warning
        Đây không phải sandbox. Máy chủ MCP không tin cậy nên chạy thành
        container HTTP riêng.

**Lấy danh sách công cụ** liệt kê những gì máy chủ cung cấp. Phạm vi là cá nhân hoặc toàn
tổ chức; admin chọn vai trò nào được dùng máy chủ của tổ chức. Secret được mã
hoá, API chỉ trả về tên và giá trị đã che.

## Gọi công cụ

Trong node MCP tool, chọn máy chủ và công cụ; mô tả của công cụ hiện trong cấu
hình. Chuỗi trong arguments là [template](state.md#tham-chieu).
Argument đúng bằng một tham chiếu thì giữ nguyên kiểu. Kết quả ghi vào
`output_field`.

Workflow được chia sẻ chạy bằng máy chủ MCP của **chủ** workflow.

## Node MCP hay node Agent

Node MCP tool gọi một công cụ với các tham số bạn điền sẵn, ở một chỗ cố định
trong graph. Muốn model tự quyết định có gọi công cụ không, gọi lúc nào và với
tham số gì, hãy thêm công cụ đó vào một [node Agent](agent.md): chọn máy chủ và
công cụ, model sẽ đọc mô tả và schema input của công cụ từ máy chủ. Model chỉ
được dùng các công cụ bạn thêm, không bao giờ là cả danh sách của máy chủ.
