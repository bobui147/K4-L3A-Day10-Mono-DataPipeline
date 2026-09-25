# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Mono`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Repository hiện tại:** `K4-L3A-Day10-Data-Pipeline-Data-Observability` (cần đổi tên theo quy định trước khi nộp)

---

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Bùi Tùng Dương | 2A202602775 | duongbui147205@gmail.com | Làm cá nhân, phụ trách cả 4 phần: Pipeline Integration; Data Foundation & Recovery; RAG & Vector Index; Observability & Evaluation | `report/2A202602775_BuiTungDuong.md` |

---

## Cá nhân

### Bùi Tùng Dương — 2A202602775

- **Vai trò:** Thành viên duy nhất của nhóm Mono, thực hiện cả 4 phần công việc.
- **Pipeline Integration:** Thiết lập cấu hình trong `src/core/config.py`, kết nối luồng chạy baseline và corruption flow, kiểm tra các artifacts đầu ra.
- **Data Foundation & Recovery:** Thu thập dữ liệu Crossref với bản dự phòng offline, bảo toàn raw snapshot, làm sạch dữ liệu, tạo các lỗi dữ liệu có kiểm soát và phục hồi từ dữ liệu gốc.
- **RAG & Vector Index:** Tạo embedding, quản lý các collection ChromaDB cho baseline, corrupted và repaired; chạy truy vấn hỏi đáp trên từng trạng thái.
- **Observability & Evaluation:** Xây dựng Quality Gate bằng Great Expectations 1.x, kiểm tra Freshness SLA, tạo benchmark test set, đo các chỉ số và lập báo cáo đối chiếu 3 trạng thái.
- **Điều học được / Đóng góp chính:** Thiết kế pipeline có thể chạy lại, truy vết từ dữ liệu gốc đến kết quả đánh giá, và dùng kiểm tra chất lượng để phát hiện suy giảm dữ liệu trước khi phục vụ truy vấn.
