# Máy chủ MCP

## Kết nối được quản lý

Trong **Cài đặt → MCP**, thêm **Kết nối được quản lý**, chọn adapter dịch vụ,
rồi bấm khám phá công cụ. Chọn kết nối này trong node **MCP tool** hoặc slot
công cụ MCP của Agent như với máy chủ MCP từ xa. Logic riêng của dịch vụ nằm
trong adapter, không tạo loại node riêng trên canvas.

| Adapter | Cấu hình kết nối | Tham số công cụ |
| --- | --- | --- |
| Thao tác Telegram | Kết nối Telegram đã có; ID cuộc chat nhận tin cố định | `send_message`: `text` thuần, `reply_to_message_id` dạng số nguyên nếu cần |
| Thao tác Google Sheets | ID spreadsheet và tên tab cố định; số cột dữ liệu (1–25); khoá JSON service account được mã hoá | `append_row`: `values` với đúng số phần tử vô hướng đã cấu hình |

Tạo [service account Google](https://developers.google.com/identity/protocols/oauth2/service-account),
bật Sheets API, chia sẻ spreadsheet cho email đó với quyền chỉnh sửa rồi dán
khoá JSON vào Cài đặt. Sheet được chia sẻ trực tiếp không cần OAuth người dùng
hay uỷ quyền toàn miền. Secret được mã hoá, không trả lại trong metadata công cụ
hoặc workflow JSON. Telegram dùng lại secret của kết nối kênh; không thể chọn
kênh cá nhân của người khác để cấp quyền qua kết nối MCP tổ chức. Quyền sử dụng
và chính sách tổ chức được kiểm tra lại khi gọi.

Với sáu cột dữ liệu, đặt tiêu đề tại A–F và dành cột G cho ID thao tác. Giữ
nguyên cột này. [API append của Sheets](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/append)
nhận giá trị `RAW`: chuỗi vẫn là văn bản, kể cả nội dung giống công thức; số
vẫn là số. ID bổ sung cho phép tìm kết quả khi mất phản hồi. Đối soát đọc tối
đa 100.000 dòng; chuyển sang tab mới trước giới hạn đó. Không để công cụ khác
sửa hoặc xoá ID thao tác trong cùng tab.

### Kết quả ghi và khôi phục

Mỗi thao tác ghi cần ID cố định từ workflow. Studio lưu ý định trước khi gọi
dịch vụ. Kết quả đã xác nhận được dùng lại cho cùng run/node/lần lặp; đổi tham
số hoặc nơi ghi sẽ bị từ chối. MCP node cũng dùng sổ kết quả và cơ chế chặn
worker đã mất quyền xử lý hiện có.

**Thao tác gần đây** hiển thị chờ xác nhận, đã xác nhận, bị từ chối hoặc chưa
rõ kết quả cùng ID thao tác bên ngoài. **Kiểm tra kết quả bên ngoài** chỉ đọc:
Sheets có thể xác nhận ID đã ghi, nhưng không tìm thấy dòng không có nghĩa là
được append lại. Máy chủ dừng trước khi gửi cũng có thể để lại ý định chưa rõ.
Telegram không tìm được tin đã gửi theo ID này, nên thao tác gửi chưa rõ kết
quả vẫn bị chặn. Không tạo run mới chỉ để vượt qua trạng thái chưa rõ; kiểm
tra dịch vụ bên ngoài trước. Khôi phục nơi ghi gốc trước khi đối soát thao tác
cũ; có thể thay khoá xác thực mà giữ nguyên nơi ghi.

Chỉ báo thành công sau thao tác **đã xác nhận**. Bị từ chối hoặc chưa rõ kết
quả sẽ dừng MCP node thường. Agent nhận lỗi công cụ bình thường; hướng dẫn
Agent phải yêu cầu xác nhận trước khi báo thành công. Run kiểm thử và run dùng
model giả lập không gửi tin, ghi sheet, đổi token hay lưu ý định. MCP HTTP/stdio
giữ nguyên hành vi. Xuất Python/TypeScript từ chối kết nối quản lý một cách rõ
ràng vì hiện cần theo dõi thao tác trong Studio. Template để trống tham chiếu
tài nguyên; chọn kết nối sau khi tạo workflow từ mẫu.

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

Để client MCP gọi workflow **của bạn** như công cụ, xem [Workflow làm công cụ MCP](../run/mcp-server.md).

## Node MCP hay node Agent

Node MCP tool gọi một công cụ với các tham số bạn điền sẵn, ở một chỗ cố định
trong graph. Muốn model tự quyết định có gọi công cụ không, gọi lúc nào và với
tham số gì, hãy thêm công cụ đó vào một [node Agent](agent.md): chọn máy chủ và
công cụ, model sẽ đọc mô tả và schema input của công cụ từ máy chủ. Model chỉ
được dùng các công cụ bạn thêm, không bao giờ là cả danh sách của máy chủ.
