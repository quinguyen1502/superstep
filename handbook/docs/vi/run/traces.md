# Run và trace

## Timeline Logs

![Trace của run](../images/run-trace.png)

Logs trong tab **Chạy** có mỗi bước của node là một dòng: trạng thái, tên, loại, thời
gian, thanh thác nước, và số token khi model trả về. Vòng lặp hiện `#2`, `#3`,
… Dòng tóm tắt cho biết trạng thái run, thời gian, số bước, token input và
output, chi phí và số lỗi.

Bấm vào một dòng, hoặc vào node trên canvas, để mở chi tiết:

| Tab | Hiện |
| --- | --- |
| Input | State mà node nhận vào |
| Output | Kết quả node trả về (token đang stream nếu là node LLM đang chạy) |
| State diff | Các trường mà bước này thêm, đổi hoặc xoá |
| Raw | Sự kiện gốc của bước |

![State diff](../images/trace-detail.png)

[Node Agent](../guide/agent.md#trace-va-muc-dung) hiện các bước của nó ngay bên
dưới: dòng `Agent › model` có vòng và các công cụ đã gọi hoặc câu trả lời, dòng
`Agent › tool` có công cụ, kết quả đã rút gọn, và **đã duyệt** hoặc **người
duyệt từ chối** khi có người trả lời.

**Raw events** chuyển cả timeline sang luồng sự kiện gốc. Chọn một run trước
đó ở menu run cạnh các tab (10 run gần nhất), hoặc trong **Xem tất cả**, để
phát lại trên cùng timeline, kèm nhãn phiên bản.

## Chạy từng bước

| Nút | Tác dụng |
| --- | --- |
| **Một bước** | Chạy một superstep rồi dừng chính run đó (trạng thái `paused`). |
| **Chạy tiếp** | Chạy phần còn lại. |
| **Chạy tới đây** | Chọn một node trước. Chạy tới khi node đó xong rồi dừng. Nếu đường đi không bao giờ tới node đó, run chạy hết và báo lại. |

Dừng kiểu này không phải là duyệt bởi người. Superstep chỉ có Start không tính
là một bước.

## Du hành thời gian: fork từ một checkpoint

Mở một run đã xong (hoặc chọn trong **Xem tất cả run**) rồi bấm **Du hành thời
gian** phía trên timeline. Hộp thoại liệt kê các checkpoint của run: mỗi bước
một checkpoint, đặt tên theo các node chạy tiếp theo ("Trước Approved?"), kèm
state mà chúng bắt đầu, và cuối cùng là state cuối.

1. Chọn một checkpoint để xem state của nó.
2. Có thể sửa state (phải vẫn là một object JSON). **Đặt lại** đưa state đã ghi
   về như cũ.
3. Bấm **Fork từ đây**. Một run mới bắt đầu tại các node đó với state đó; các
   node trước đó không chạy lại. Timeline của nó hiện **Fork từ** run gốc và
   checkpoint. Run gốc không bị thay đổi.

Bản fork chạy phiên bản workflow mà run gốc đã chạy nếu phiên bản đó còn được
lưu, nếu không thì chạy workflow đã lưu. Số lần lặp (giới hạn vòng lặp) được
giữ nguyên. Không thể fork checkpoint có state quá lớn để ghi lại, state cuối,
run của graph LangGraph được import, và run đang chờ hoặc đang chạy. Chỉ chủ
run (hoặc chủ workflow và admin) mới xem được các checkpoint của nó.

```text
GET  /api/runs/{run_id}/checkpoints
WS   /ws/run   {"fork": {"run_id": "...", "checkpoint": 1, "state": {...}}}   (state không bắt buộc)
```

## Huỷ

**Huỷ** (++ctrl+period++) gửi `{"type": "cancel"}`. Đóng tab cũng huỷ run. Huỷ
mang tính hợp tác: run dừng giữa các bước, nên lời gọi LLM hay HTTP đang chạy
có thể vẫn chạy xong. Container của node Code bị kill.

## Trạng thái

| Trạng thái | Nghĩa |
| --- | --- |
| `ok` | Đã tới End. |
| `error` | Một node lỗi sau khi đã retry, hoặc graph không qua kiểm tra. |
| `cancelled` | Bị người huỷ hoặc tab bị đóng. |
| `timeout` | Chạy quá `STUDIO_RUN_TIMEOUT`. |
| `paused` | Dừng bởi Một bước hoặc Chạy tới đây. |
| `waiting` | Đang ở node Human. |
| `expired` | Chờ lâu hơn `STUDIO_WAIT_TTL`. |

Lỗi gói trong một dòng, `sk-…`, `Bearer …` và `api_key=…` được che đi.

## Giới hạn

| Biến | Mặc định | Nghĩa |
| --- | --- | --- |
| `STUDIO_RECURSION_LIMIT` | 25 | Số bước tối đa mỗi run. Vòng lặp không bao giờ đi qua Condition sẽ dừng với lỗi. Bước của For each không tính. |
| `STUDIO_RUN_TIMEOUT` | 120 giây | Thời gian tối đa của run, quá thì `timeout`. Thời gian chờ ở node Human không tính, phần chuẩn bị trước node đầu tiên (như lưu checkpoint tiến độ đầu tiên) cũng không tính. |
| `STUDIO_EVENT_MAX_BYTES` | 262144 | Kích thước tối đa của một sự kiện. Trường quá lớn thành `{"_truncated": true, …}`. |
| `STUDIO_RUN_MAX_BYTES` | 2097152 | Dung lượng sự kiện tối đa lưu cho một run. Phần giữa được thay bằng `{"type": "truncated", "dropped": n}`. |
| `STUDIO_INPUT_MAX_BYTES` | 262144 | Input tối đa của run. |
| `STUDIO_WORKFLOW_MAX_BYTES` | 1048576 | JSON workflow tối đa. Lưu lớn hơn trả về HTTP 413. |

Timeline còn cắt `input` và `delta` ở 16 000 ký tự JSON để trang nhẹ.

## Token và chi phí

Chi phí tính từ số token và bảng giá trong `backend/app/engine/usage.py`. Bản
mock ước lượng token và tính `$0`. Model không có trong bảng hiện `—`. Ghi đè
giá (USD cho mỗi triệu token) bằng `STUDIO_PRICES='{"my-model": [1.0, 2.0]}'`
(input, output) hoặc `STUDIO_PRICES_FILE`; tiền tố khớp dài nhất thắng.

## Xuất ra hệ thống trace

Mỗi run cũng có thể thành một trace OpenTelemetry trong Jaeger, Tempo hoặc
LangSmith, có link **Mở trace** trong timeline. Xem
[Quan sát hệ thống](../operate/observability.md).
