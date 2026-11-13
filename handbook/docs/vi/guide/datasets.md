# Tập dữ liệu

Tập dữ liệu là một bảng có kiểu, thuộc về bạn hoặc một nhóm. Workflow có thể tra
cứu và ghi dòng. Dự án xuất ra có thể dùng cùng các dòng đó qua API Superstep
hoặc qua cơ sở SQLite hay PostgreSQL riêng.

## Soạn thảo

Mở **Tập dữ liệu** từ điều hướng của studio.

![Lưới Phiếu hỗ trợ](../images/datasets-grid.png)

Trên màn hình hẹp, danh mục xếp dưới tiêu đề và lưới cuộn ngang.

![Tập dữ liệu trên màn hình hẹp](../images/datasets-narrow.png)

- **Tạo** hỏi tên, mô tả không bắt buộc, và phạm vi cá nhân hoặc nhóm. Hãy thêm
  cột trước lần nhập đầu nếu bạn đã biết các trường.
- Mỗi cột có nhãn, khoá ổn định, và kiểu: văn bản, số, boolean, ngày, ngày giờ,
  email, hoặc chọn. Cột có thể bắt buộc hoặc duy nhất. Khoá không đổi khi bạn
  đổi nhãn, nên ánh xạ trong workflow vẫn đúng.
- Bắt buộc được chọn khi thêm cột. Duy nhất có thể bật sau trong **Sửa cột**,
  ví dụ sau khi nhập CSV chưa có khoá. Studio kiểm tra các dòng hiện có trước.
  Nếu có dòng trùng giá trị, Studio cho biết số dòng và dẫn tới các dòng đó để
  bạn sửa. Không thể tắt Duy nhất khi còn workflow dùng trường này để tìm dòng
  cho Upsert hoặc Xoá dòng.
- Lưới sửa dòng. Lần lưu gửi revision của dòng. Nếu người khác đã lưu trước,
  Studio bảo bạn tải lại thay vì ghi đè sửa đổi đó.
- Xoá tập dữ liệu, cột, hoặc quyền yêu cầu bạn gõ đúng tên mục đó. Khi xoá một
  dòng, Studio gọi tên dòng theo trường duy nhất đầu tiên, hoặc theo ID dòng
  nếu dòng không có giá trị duy nhất.
- Xoá cột sẽ xoá giá trị của cột đó trong mọi dòng. Khoá của cột vẫn được giữ
  nên không dùng lại được, và cột đã xoá không tính vào giới hạn 100 cột.
- Cột bắt buộc thêm vào tập dữ liệu đã có dòng cần giá trị mặc định. Mọi dòng
  hiện có nhận giá trị mặc định, miễn là không dòng nào vượt giới hạn 64 KiB.

Bạn cần `resources.manage` để tạo tập dữ liệu hoặc đổi lược đồ và dòng. Ai nhìn
thấy tập dữ liệu thì đọc được dòng. Khi thiếu quyền đó, các nút tạo, sửa, nhập,
và xoá vẫn hiện nhưng bị tắt, kèm ghi chú giải thích lý do. Liên kết tới tập dữ
liệu đã bị xoá, hoặc bạn không mở được, hiện "Không tìm thấy tập dữ liệu" kèm
đường quay lại danh mục.

## Quyền truy cập

Menu **Truy cập** cấp cho một workflow đã lưu quyền đọc hoặc ghi. Workflow không
có quyền đó không chạy được node Tập dữ liệu hoặc công cụ Tập dữ liệu trên bảng
này. Phát hành token Tập dữ liệu cho dự án xuất ra gọi API Superstep. Token chỉ
hiện một lần. Thu hồi token thì các lần gọi sau dừng. Người không nhìn thấy tập
dữ liệu nhận kết quả không tìm thấy, kể cả khi tải CSV.

Quyền ghi mà không có quyền đọc được chèn và upsert dòng nhưng không bao giờ
nhận giá trị ô. Kết quả chỉ có mã dòng, revision và cho biết dòng có được thêm
mới hay không, dù là run thật, run kiểm thử hay gỡ lỗi, hoặc lần ghi được
thử lại. Node Tập dữ liệu có quyền chỉ ghi không chọn được trường trả về; node
đã lưu mà vẫn yêu cầu trường sẽ lỗi `DATASET_GRANT_DENIED` trước khi ghi. Công
cụ của Agent không có **Tìm dòng** chỉ đưa cho mô hình các mã định danh đó, kể
cả khi có quyền đọc và ghi. Upsert vẫn cho biết đã có dòng mang khoá đó hay
chưa. Nếu điều này cần được giữ kín, hãy dùng **Thêm dòng**. Upsert không đổi giá
trị nào thì giữ nguyên revision và thời điểm cập nhật của dòng.

## CSV

**Nhập CSV** xem trước tệp trước khi ghi.

![Xem trước và ánh xạ cột khi nhập CSV](../images/datasets-csv.png)

- Tệp là UTF-8, tối đa 1 MiB và 1.000 bản ghi. Bắt buộc có dòng tiêu đề.
- Bản xem trước gợi ý khoá trường và kiểu cho mỗi cột. Bạn có thể đổi ánh xạ,
  bỏ qua một cột, và sửa lược đồ trước khi nhập.
- Việc nhập là nguyên tử. Nếu có dòng không hợp lệ, hoặc trùng giá trị duy nhất,
  thì không ghi gì. Bản xem trước liệt kê tối đa 100 lỗi theo thứ tự dòng, kèm
  số lỗi của mỗi loại. Mỗi lỗi nêu nhãn cột và giá trị bị từ chối, rút gọn khi
  quá dài.
- **Xuất CSV** cần quyền đọc. Tệp gồm mọi dòng. Giá trị mà bảng tính coi là công
  thức được thêm dấu nháy đơn ở đầu. Bản tải về tối đa 16 MiB.

## Workflow và xuất dự án

Node Tập dữ liệu có thể tìm dòng, lấy một dòng, chèn dòng, hoặc upsert dòng.
Công cụ của Agent chỉ được đọc. Nhiều node dùng cùng một tập dữ liệu thì chung
một binding khi xuất.

Ở tab **Mã**, **Dự án .zip** liệt kê từng binding. Chọn API Superstep, SQLite,
hoặc PostgreSQL. Đồ thị sinh ra đọc lựa chọn đó từ biến môi trường, nên lúc
triển khai có thể đổi backend mà không cần xuất lại. Đặt:

- `DATASET_N_BACKEND` là `superstep`, `sqlite`, hoặc `postgresql`
- `DATASET_N_ID` là id đích, hoặc một tên ổn định trong cơ sở dữ liệu của bạn
- `DATASET_N_API_URL` và `DATASET_N_API_TOKEN` cho API Superstep
- `DATASET_N_SQLITE_PATH` hoặc `DATASET_N_POSTGRES_DSN` cho cơ sở độc lập

Chạy `python agent.py --setup-datasets` hoặc lệnh TypeScript tương ứng trước
lần chạy đầu. Setup lặp lại vẫn an toàn. Lệnh tạo các bảng của dự án và giữ
những dòng đã có. Ảnh chụp tắt trừ khi bạn chọn **Kèm các dòng hiện tại** cho
binding độc lập. Khi đó gói chứa tối đa 1.000 dòng trong
`dataset-snapshots.json`. Setup chỉ nhập dòng ảnh chụp khi id đó chưa được lưu,
và từ chối ảnh chụp có lược đồ không khớp binding.

## Sao lưu, nâng cấp, và giới hạn

Sao lưu tệp SQLite độc lập bằng cách chép tệp khi không có tiến trình ghi, hoặc
sao lưu PostgreSQL bằng `pg_dump`. Cơ sở Superstep giữ dòng của Studio trong
các bảng `dataset_rows`. Hãy giữ các bảng đó khi bạn lùi một phiên bản ứng
dụng. Thay đổi lược đồ chỉ thêm. Đừng xoá bảng để hoàn tác một lần nâng cấp.

Giới hạn được hỗ trợ:

| Giới hạn | Giá trị |
| --- | --- |
| Số cột | 100 cột đang dùng, 200 khi tính cả cột đã xoá |
| Số dòng trong một tập dữ liệu | 25.000 |
| Một dòng | 64 KiB |
| Nhập CSV | 1 MiB và 1.000 bản ghi |
| Xuất CSV | 16 MiB |
| Ảnh chụp trong một dự án | 1.000 dòng |
