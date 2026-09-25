# Báo Cáo Pha 1: Baseline Pipeline & Data Observability

**Thời gian khởi tạo:** `2026-09-25 08:57:29 UTC`  
**Trạng thái kiểm định:** `CHẤP THUẬN (PASS)`  
**Môi trường:** Python venv | Great Expectations 1.x (ephemeral) | ChromaDB  

---

## 1. Tóm Tắt Tổng Quan (Executive Summary)

Pha 1 của hệ thống RAG Agent đã hoàn thành toàn bộ chu trình xử lý dữ liệu sạch (Baseline Data Pipeline) với các kết quả chính:
- **Dữ liệu thô:** Thu thập và lưu trữ an toàn 24 bản ghi metadata nghiên cứu khoa học từ Crossref API.
- **Làm sạch & Chuẩn hóa:** Dữ liệu được loại bỏ thẻ XML/JATS, chuẩn hóa khoảng trắng, tính toán chỉ số tuổi thọ `age_days`, và tạo ngữ cảnh chuẩn `text_for_embedding`.
- **Kiểm soát chất lượng (Quality Gate):** Vượt qua 100% các tiêu chí kiểm định Great Expectations 1.x và đạt tiêu chuẩn tươi mới Freshness SLA.
- **Vector Database:** Đã lập chỉ mục 24 tài liệu vào ChromaDB collection `papers-baseline` bằng mô hình embedding `all-MiniLM-L6-v2`.
- **Hiệu năng Baseline:** Đạt **Retrieval Hit Rate = 100.00%**, **Token F1 = 0.4125**, và **LLM Judge Score = 2.60/5.0**.

---

## 2. Thu Thập Dữ Liệu & Data Lineage (Raw Preservation)

Để đảm bảo khả năng tái lập và phục hồi dữ liệu (Idempotency & Lineage), hai tầng lưu trữ thô đã được thiết lập:
- **Nguồn dữ liệu:** Crossref REST API
- **Truy vấn chủ đề:** `agentic retrieval augmented generation large language model`
- **Bộ lọc nguồn:** `from-pub-date:2026-03-29,has-abstract:true`
- **Artifacts lưu trữ bản gốc:**
  - `data/raw/crossref_response.json`: Toàn bộ JSON phản hồi nguyên gốc từ API.
  - `data/raw/crossref_records.json`: Danh sách đối tượng `PaperRecord` đã bóc tách chuẩn.

---

## 3. Làm Sạch & Chuẩn Hóa Dữ Liệu (Data Cleaning)

- **Số dòng dữ liệu sạch:** 24 bản ghi.
- **Khử trùng lặp:** Dựa trên khóa định danh chuẩn hóa `paper_id` (DOI).
- **Cấu trúc trường `text_for_embedding`:**
  ```text
  Title: <Tiêu đề bài báo>
  Authors: <Danh sách tác giả>
  Published: <Ngày xuất bản>
  Categories: <Lĩnh vực chuyên môn>
  Summary: <Tóm tắt nội dung sạch>
  ```
- **File xuất ra:**
  - `data/clean/papers_clean.csv` (Định dạng bảng phân tích)
  - `data/clean/papers_clean.json` (Định dạng bản ghi có cấu trúc)

---

## 4. Trạm Kiểm Soát Dữ Liệu Great Expectations 1.x (Quality Gate)

Hệ thống sử dụng Great Expectations 1.x ephemeral mode để thẩm định dữ liệu trước khi nạp vào Vector Database:

| Tên kỳ vọng (Expectation) | Kết quả kiểm định |
| :--- | :---: |
| `expect_table_row_count_to_be_between` | PASSED |
| `expect_column_values_to_not_be_null` | PASSED |
| `expect_column_values_to_be_unique` | PASSED |
| `expect_column_values_to_not_be_null` | PASSED |
| `expect_column_values_to_not_be_null` | PASSED |
| `expect_column_value_lengths_to_be_between` | PASSED |

**Đánh giá GX 1.x:** `THÀNH CÔNG (PASSED)`

---

## 5. Giám Sát Độ Tươi Mới (Freshness SLA Monitoring)

- **Ngưỡng quy định SLA:** `180` ngày.
- **Bài báo mới nhất:** `2026-07-22`
- **Bài báo cũ nhất:** `2026-03-28`
- **Số bản ghi quá hạn (> 180 ngày):** `1` bản ghi.
- **Tỉ lệ quá hạn (Stale Ratio):** `4.17%` (Ngưỡng cảnh báo: > 25.00%).
- **Trạng thái Freshness:** `ĐẠT TIÊU CHUẨN TƯƠI MỚI (FRESH)`

---

## 6. Hiệu Năng Đánh Giá Baseline (Evaluation Metrics)

Bộ câu hỏi benchmark được đánh giá trên tập test set chuẩn (`data/eval/test_set.json`):

| Chỉ số đánh giá | Điểm số Baseline | Diễn giải |
| :--- | :---: | :--- |
| **Số lượng câu hỏi mẫu** | `5` | Phủ đều 4 nhóm: summary, authors, date, categories |
| **Retrieval Hit Rate** | **`100.00%`** | Tỷ lệ trích xuất đúng tài liệu chứa ground truth |
| **Mean Token F1** | **`0.4125`** | Độ tương đồng từ vựng giữa câu trả lời và ground truth |
| **LLM Judge Accuracy** | **`40.00%`** | Tỷ lệ câu trả lời được LLM Judge thẩm định chính xác |
| **LLM Judge Score** | **`2.60 / 5.00`** | Điểm số chất lượng trung bình theo thang điểm 5 |

---

## 7. Bảng Kiểm Tra Artifacts Được Sinh Ra (Artifact Checklist)

| STT | Tên Artifact | Đường dẫn tệp tin | Trạng thái |
| :---: | :--- | :--- | :---: |
| 1 | Bảng dữ liệu sạch hoàn chỉnh | `data/clean/papers_clean.csv` | **PASSED** |
| 2 | Vector Database ChromaDB | `data/chroma/` | **PASSED** |
| 3 | Bộ câu hỏi benchmark cố định | `data/eval/test_set.json` | **PASSED** |
| 4 | Bảng chỉ số Baseline | `data/results/baseline_metrics.json` | **PASSED** |
| 5 | Báo cáo chi tiết định dạng Markdown | `data/reports/phase1_report.md` | **PASSED** |

---
*Báo cáo được khởi tạo tự động bởi hệ thống Day 10 Data Pipeline & Data Observability.*
