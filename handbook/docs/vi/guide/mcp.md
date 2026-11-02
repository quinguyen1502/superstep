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
| HTTP API tổng quát | URL gốc cố định, JSON định nghĩa công cụ và JSON header xác thực được mã hoá | Các công cụ đã khai báo; GET gửi query dạng đơn, phương thức khác gửi object JSON |

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

### HTTP API tổng quát

![Cài đặt HTTP API tổng quát với cấu hình mẫu](../images/managed-http-api.png)

Chọn **HTTP API tổng quát** trong kết nối được quản lý. Nhập URL gốc HTTPS,
ví dụ `https://api.example.com/v1`. Đường dẫn công cụ là đường dẫn tương đối
cố định, không dùng template. Tham số lúc chạy không được chọn URL, phương
thức hay header. Địa chỉ nội bộ và HTTP thường cần máy chủ bật rõ
`STUDIO_MCP_ALLOW_PRIVATE=1`. Mỗi yêu cầu kiểm tra địa chỉ và kết nối tới IP
đã xác minh; không đi theo redirect.

Dán mảng JSON vào **Định nghĩa công cụ**, ví dụ:

```json
[
  {
    "name": "create_record",
    "description": "Create a record in the configured API",
    "method": "POST",
    "path": "/records",
    "input_schema": {
      "type": "object",
      "additionalProperties": false,
      "required": ["text"],
      "properties": {"text": {"type": "string", "maxLength": 4000}}
    },
    "success_statuses": [200, 201],
    "response_schema": {
      "type": "object",
      "required": ["ok"],
      "properties": {"ok": {"const": true}}
    }
  }
]
```

Hỗ trợ GET, POST, PUT, PATCH và DELETE. Schema input phải là object với
`additionalProperties: false`. Thuộc tính GET có kiểu vô hướng; phương thức
khác gửi toàn bộ object tham số làm JSON. Schema không được chứa tham chiếu.
Chưa có biến đường dẫn động, form data hay tải tệp. Khai báo công cụ cố định
riêng khi cần đích khác nhau, bấm **Khám phá công cụ** rồi chọn trong MCP node
hoặc slot Agent. Khám phá lại sau khi sửa cấu hình.

**Header xác thực** là object JSON được mã hoá, có thể để trống, ví dụ
`{"Authorization":"Bearer YOUR_API_TOKEN"}` hoặc `{"X-API-Key":"YOUR_API_KEY"}`.
Không đặt credential trong URL gốc hay định nghĩa công cụ công khai. Studio
quản lý header host, truyền tải, cookie và ID thao tác; header xác thực không
được ghi đè chúng. Giá trị đã lưu không trả lại. Chuỗi credential đã cấu hình
được che trong dữ liệu phản hồi; không trả lại header hay URL phản hồi. Xem
dữ liệu API nhận được là nội dung không tin cậy.

Giới hạn: 20 công cụ, JSON định nghĩa 32 KiB, JSON header 4 KiB, JSON sâu tối
đa 16 cấp, tham số 128 KiB và phản hồi 256 KiB. Thời gian chờ yêu cầu quản lý
là 20 giây. Chỉ hỗ trợ phản hồi JSON hoặc body rỗng. Mã thành công mặc định
là 200, 201, 204; dùng `success_statuses` cho mã 2xx đã hoàn tất khác. HTTP
202 luôn chưa rõ kết quả vì xử lý chưa xong. Phản hồi thành công nhưng JSON
sai, quá lớn hoặc sai schema cũng chưa rõ kết quả. Xem
[ngữ nghĩa HTTP](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted).

HTTP thành công chỉ xác nhận hợp đồng phản hồi đã cấu hình, không tự xác
nhận mọi kết quả nghiệp vụ hay giao tin. Thêm `response_schema` nếu API có
thể báo lỗi bằng HTTP 200; điều kiện `ok: true` trong ví dụ phải khớp API của
bạn. Mỗi yêu cầu gửi `Idempotency-Key` cố định; việc chống trùng bên ngoài
phụ thuộc hợp đồng của API. Adapter tổng quát chưa có cách tra cứu kết quả
bên ngoài tự động: thao tác timeout/chưa rõ luôn bị chặn, không gửi lại, kể
cả khi bấm **Kiểm tra kết quả bên ngoài**. Kiểm tra API trước khi tạo run mới.

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
