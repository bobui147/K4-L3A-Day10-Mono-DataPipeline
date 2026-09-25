# Báo cáo cá nhân — Bùi Tùng Dương

- **MSSV:** 2A202602775
- **Nhóm:** Mono (làm cá nhân)
- **Repository:** https://github.com/bobui147/K4-L3A-Day10-Data-Pipeline-Data-Observability
- **Vai trò:** Phụ trách cả 4 mảng: Pipeline Integration, Data Foundation & Recovery, RAG & Vector Index, Observability & Evaluation.

## Phần việc và đầu ra

1. **Data Foundation & Recovery:** `src/ingestion/crossref.py` đọc dữ liệu Crossref và giữ raw snapshot; `src/ingestion/cleaning.py` chuẩn hóa bản ghi, tạo `age_days` và `text_for_embedding`; `src/ingestion/corruption.py` tạo sáu dạng lỗi. Đầu ra nằm ở `data/raw/`, `data/clean/` và `data/results/corruption_log.json`.
2. **RAG & Vector Index:** dữ liệu sạch, lỗi và phục hồi được embedding và nạp vào ba collection ChromaDB riêng. `src/retrieval/qa.py` trả lời từ kết quả truy hồi. Đầu ra gồm `data/chroma/`, `data/embeddings/` và các file answers trong `data/results/`.
3. **Observability & Evaluation:** `src/evaluation/testset.py` tạo 10 câu hỏi có ground truth DOI; `src/observability/quality.py` chạy Great Expectations 1.x và Freshness SLA; `src/observability/reporting.py` tạo báo cáo. Đầu ra nằm ở `data/eval/`, `data/quality/` và `data/reports/`.
4. **Pipeline Integration:** `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py` nối các khối, dùng cùng test set cho ba trạng thái và phục hồi từ raw records. Đầu ra là ba bộ metrics trong `data/results/`.

## Cách triển khai và xác minh

Pipeline giữ dữ liệu gốc để có thể tái tạo trạng thái sạch. `paper_id` lấy từ DOI, nên benchmark đối chiếu được bài đúng qua các lần lập chỉ mục. Quality gate kiểm tra số dòng, trường bắt buộc, DOI duy nhất và độ dài title/summary/text. Freshness đo riêng tỷ lệ bài quá 180 ngày. Corruption được chọn theo thứ tự xác định để kết quả có thể lặp lại; repair đọc lại raw snapshot thay vì sửa trực tiếp dữ liệu đã hỏng.

```powershell
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Hai luồng đã chạy thành công và tạo ra các báo cáo, dữ liệu và metrics trong `data/`. Lần chạy dùng Crossref snapshot offline; đường gọi Live API chưa được thử bằng request thật. LLM judge dùng OpenAI `gpt-4.1-mini`, không có heuristic fallback trong ba bộ metrics. Ragas tùy chọn chưa chạy.

## Kết quả và bài học

- Baseline: 24 bài, Hit Rate@4 = 1,0; Token F1 = 0,974; Judge Accuracy = 0,9; quality và freshness đều PASS.
- Corrupted: 21 bài, Hit Rate@4 = 0,7; Token F1 = 0,6; Judge Accuracy = 0,6; quality và freshness đều FAIL. Sáu thao tác lỗi được ghi trong `data/results/corruption_log.json`.
- Repaired: 24 bài, cả hai gate PASS; các chỉ số RAG trở lại mức baseline. Nội dung phục hồi khớp baseline và bộ DOI vẫn duy nhất khi chạy lại repair.

Bộ dữ liệu vẫn có thể tạo câu trả lời khi một phần record sai, vì vậy chỉ kiểm tra pipeline chạy hết là chưa đủ. Cần đo chất lượng dữ liệu và chất lượng truy hồi trên cùng benchmark. Các tín hiệu hiện tại bắt được lỗi trùng DOI, thiếu summary, title ngắn và dữ liệu cũ; lỗi mất bài mới nhất hoặc noise riêng lẻ cần thêm kiểm tra chuyên biệt.

## Vấn đề tích hợp đã xử lý

Lúc đầu QA có lối tắt chèn tài liệu theo exact title vào kết quả, làm chỉ số retrieval có thể không phản ánh truy hồi vector thực tế. Sau khi bỏ lối tắt trong `src/retrieval/qa.py`, phép đo dùng kết quả từ index; baseline vẫn đạt Hit Rate@4 = 1,0 nhưng top 1 chỉ đúng 6/10 câu, cho thấy top-k có ý nghĩa.

## Giới hạn và hướng cải thiện

- Thử đường Crossref Live API với request thật và lưu provenance riêng cho lần làm mới.
- Thêm kiểm tra đối chiếu số DOI mới nhất với raw/source và nhận diện noise để từng lỗi có tín hiệu độc lập.
- Tên repository hiện tại chưa theo mẫu quy định trong `docs/SUBMISSION.md`; cần xử lý trước khi nộp link LMS.
