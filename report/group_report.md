# Báo cáo nhóm Mono — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

- Nhóm: Mono (1 thành viên).
- Thành viên: Bùi Tùng Dương — MSSV 2A202602775 — phụ trách toàn bộ 4 mảng trong `docs/TEAM.md`.
- Repository hiện tại: https://github.com/bobui147/K4-L3A-Day10-Data-Pipeline-Data-Observability
- Môi trường: `uv sync`; `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4.1-mini`; embedding `sentence-transformers/all-MiniLM-L6-v2`. Khóa API nằm trong `.env` và không được đưa vào Git.
- Lưu ý nộp bài: tên repository hiện tại chưa theo mẫu `K4-L3-DAY10-Mono-DataPipeline` trong `docs/SUBMISSION.md`.

## 2. Luồng dữ liệu và cách chạy

Crossref snapshot → raw response và records → làm sạch và chuẩn hóa → embedding và ChromaDB → bộ câu hỏi benchmark → baseline metrics và quality/freshness gate → tiêm lỗi → đo lại → phục hồi từ raw records → đối chiếu ba trạng thái.

```powershell
uv sync
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Lần chạy tạo các artifacts được nộp dùng snapshot Crossref đã lưu, chưa gọi Crossref Live API. Bộ dữ liệu sạch có 24 bài, bộ benchmark có 10 câu hỏi với DOI ground truth; `top_k=4`. Ba trạng thái dùng cùng `data/eval/test_set.json`. ChromaDB chứa ba collection `papers-baseline`, `papers-corrupted` và `papers-repaired`. Hai pipeline đã chạy thành công để tạo các artifacts trong `data/`.

## 3. Data contract và kiểm tra chất lượng

`src/ingestion/crossref.py` đọc snapshot hoặc gọi Crossref với retry/fallback, giữ raw response; `src/ingestion/cleaning.py` chuẩn hóa title, summary, ngày, DOI, loại bản ghi không hợp lệ hoặc trùng DOI, rồi tạo `age_days` và `text_for_embedding`. DOI được dùng làm `paper_id` để đối chiếu tài liệu gốc.

Quality gate trong `src/observability/quality.py` dùng Great Expectations 1.x để kiểm tra số dòng, null, DOI duy nhất và độ dài các trường quan trọng. Freshness SLA đánh dấu stale khi `age_days > 180`; dataset fail nếu tỷ lệ stale vượt 25%. Baseline có 1/24 bài stale (4,2%) và pass cả quality lẫn freshness.

## 4. Kết quả ba trạng thái

| Chỉ số | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số bài | 24 | 21 | 24 |
| Retrieval Hit Rate@4 | 1,000 | 0,700 | 1,000 |
| Mean Token F1 | 0,974 | 0,600 | 0,974 |
| Judge Accuracy | 0,900 | 0,600 | 0,900 |
| Mean Judge Score / 5 | 4,800 | 3,700 | 4,800 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Tỷ lệ stale | 4,2% | 28,6% | 4,2% |

Nguồn: `data/results/*_metrics.json`, `data/quality/`, `data/reports/corruption_report.md`. LLM judge dùng GPT-4.1 mini; cả ba lượt đánh giá có `judge_fallback_count=0`. Ragas là tùy chọn và chưa chạy.

## 5. Corruption, repair và kết luận

`data/results/corruption_log.json` ghi sáu thao tác: xóa 5 bài mới nhất, làm rỗng 3 summary, thêm noise vào 3 bài, cắt ngắn 3 title, làm cũ ngày của 6 bài và chèn 2 dòng trùng DOI. Một số thao tác cùng tác động lên một bài nên dataset sau lỗi có 21 dòng.

Ở trạng thái corrupted, DOI trùng và title/summary ngắn làm GX fail; 6/21 bài stale (28,6%) làm freshness fail. Trên cùng benchmark, Hit Rate@4 giảm từ 1,0 xuống 0,7 và Token F1 từ 0,974 xuống 0,6. Repair tái tạo dữ liệu sạch từ `data/raw/crossref_records.json`, không chỉnh vá bộ corrupted. Nội dung repaired khớp baseline, cả hai gate pass và các chỉ số RAG trở lại mức baseline. Chạy lại bước repair cho cùng nội dung JSON và 24 DOI duy nhất trong collection.

## 6. Giới hạn

- Snapshot offline giúp tái hiện kết quả; đường gọi Crossref Live API chưa được kiểm chứng với request thật.
- Quality gate phát hiện bộ lỗi kết hợp, nhưng chưa bảo đảm phát hiện độc lập lỗi mất bài mới nhất hoặc noise.
- Tên repository GitHub hiện tại chưa theo quy ước nộp bài. Việc đổi tên và nộp link trên LMS là bước riêng sau commit.
