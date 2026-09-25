# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung |
| ----------------- | ------------------------------------------------------ |
| Khóa/Lớp          | K4 — DAY10 |
| Tên nhóm          | Group 16 (`T016` / `K4A-DAY10-Group16-T016`) |
| Repository        | https://github.com/quanchu14104/K4A-DAY10-Group16-T016 |
| Ngày hoàn thành   | 2026-09-25 |

### Thành viên và phân công (Nhóm 2 thành viên — Tỷ lệ 50% / 50%)

| STT | Họ và tên | MSSV | Vai trò chính | Module / deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | **Chu Minh Quân** | 2A202602709 | Trưởng nhóm / Observability & Pipeline Integrator | `core/config.py`, `src/observability/quality.py` (GX 1.x & Freshness), `src/pipelines/phase1.py`, `src/observability/reporting.py` |
| 2 | **Nguyễn Văn Ước** | 2A202602445 | Data Foundation, Vector Retrieval & Corruption Specialist | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/retrieval/index.py`, `src/evaluation/testset.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành trọn vẹn toàn bộ chu trình thực chiến từ Checkpoint 0 đến Checkpoint 5 theo đúng quy chuẩn kỹ thuật:
1. **Pha 1 (Baseline Pipeline):** Thu thập thành công 24 bản ghi metadata bài báo khoa học từ Crossref API với cơ chế bảo tồn dữ liệu thô (Raw Preservation) và Offline Fallback. Dữ liệu được làm sạch, tính toán tuổi đời `age_days`, ghép ngữ cảnh 5 thành phần `text_for_embedding` và lập chỉ mục vào ChromaDB (`papers-baseline`). Hệ thống thiết lập chốt kiểm dịch **Great Expectations 1.x** (ephemeral context) vượt qua 100% các tiêu chí kiểm định và đạt tiêu chuẩn tươi mới Freshness SLA. Đánh giá Baseline đạt **Retrieval Hit Rate = 100.00%**, **Mean Token F1 = 0.4125**, và **LLM Judge Score = 2.60/5.0**.
2. **Pha 2 (Corruption & Degradation):** Thực thi 6 kịch bản tiêm độc tố dữ liệu giả lập sự cố sản xuất (mất bài mới, rỗng tóm tắt, chèn chuỗi rác, cắt cụt tiêu đề, mốc dữ liệu 5 năm trước, nhân bản dữ liệu). Kết quả ghi nhận hiện tượng **Silent Failure**: Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống **0.00%**, Token F1 rơi về **0.0000**, và LLM Judge Score giảm xuống **1.00/5.0**. Cả hai trạm kiểm soát GX 1.x và Freshness SLA đều lập tức báo động đỏ (`GX Success: False`, `Fresh: False`).
3. **Pha 3 (Idempotent Repair & Đối chiếu):** Kích hoạt cơ chế tự phục hồi an toàn từ bản sao lưu thô ban đầu, tái lập lại dataset sạch và index vector mới (`papers-repaired`). Hiệu năng của RAG Agent được khôi phục 100% về mức Baseline ban đầu (Hit Rate: 100%, F1: 0.4125, Judge: 2.60), chứng minh tính khả thi của nguyên lý Data Lineage và kiến trúc tự chữa lành.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref API (hoặc Snapshot data/raw/crossref_response.json)
    │
    ├──> Ingestion & Raw Preservation -> data/raw/crossref_records.json
    │
    ├──> Cleaning & Data Modeling -> data/clean/papers_clean.csv (24 dòng sạch)
    │
    ├──> Embedding (all-MiniLM-L6-v2) + ChromaDB Index (papers-baseline)
    │
    ├──> Evaluation Baseline (test_set.json) -> baseline_metrics.json (Hit Rate: 100%)
    │
    ├──> Data Observability (GX 1.x Ephemeral + Freshness SLA 180 ngày) -> phase1_report.md
    │
    ├──> Data Corruption Suite (6 kịch bản lỗi) -> data/results/corruption_log.json
    │       │
    │       ├──> Đánh giá sụt giảm (papers-corrupted) -> corrupted_metrics.json (Hit Rate: 0%)
    │       └──> Quality Gate báo động: GX FAILED, Freshness STALE
    │
    └──> Idempotent Repair (Tái nạp từ raw snapshot) -> papers-repaired
            │
            ├──> Đánh giá phục hồi -> repaired_metrics.json (Hit Rate: 100%)
            └──> Báo cáo đối chiếu 3 trạng thái -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output / artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Parse DOI, title, summary, authors, fallback offline | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Nguyễn Văn Ước |
| **Cleaning** | Raw `PaperRecord` objects | Lọc rác XML, tính `age_days`, tạo `text_for_embedding` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Nguyễn Văn Ước |
| **Embedding & Index** | Cleaned DataFrame | MiniLM-L6-v2 embedding, ChromaDB PersistentClient | `data/chroma/`<br>`data/embeddings/papers_embeddings.json` | Nguyễn Văn Ước |
| **Evaluation** | Cleaned DataFrame, ChromaDB index | Sinh benchmark testset 5 câu hỏi, tính Hit Rate, F1, Judge | `data/eval/test_set.json`<br>`data/results/baseline_metrics.json` | Nguyễn Văn Ước |
| **Observability** | Cleaned DataFrame | Cấu hình GX 1.x ephemeral mode, 4 expectations, đo Freshness | `data/quality/baseline_quality_report.json`<br>`data/quality/freshness_report.json` | Chu Minh Quân |
| **Corruption & Repair** | Cleaned DataFrame & Raw snapshot | Tiêm 6 kịch bản lỗi, log hành động, re-fetch & repair từ raw | `data/results/corruption_log.json`<br>`data/results/corrupted_metrics.json`<br>`data/results/repaired_metrics.json` | Nguyễn Văn Ước |
| **Orchestration & Report**| Pipeline modules | Ghép nối luồng end-to-end, tạo Markdown reports | `src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Chu Minh Quân |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến / cấu hình | Giá trị sử dụng | Ghi chú |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `9router` | Router LLM local kết nối backend custom |
| `LLM_MODEL` | `parrotgo` | Mô hình ngôn ngữ phục vụ tác vụ QA & Judge |
| `Embedding model` | `sentence-transformers/all-MiniLM-L6-v2` | Kích thước vector 384 chiều, khoảng cách cosine |
| `Số lượng Crossref records` | `24` | Thu thập qua từ khóa AI / RAG |
| `Retrieval top_k` | `4` | Số lượng context trích xuất cho mỗi truy vấn |
| `Freshness threshold` | `180` ngày | Ngưỡng đánh giá bài báo quá hạn (> 6 tháng) |
| `Chroma collection names` | `papers-baseline`, `papers-corrupted`, `papers-repaired` | Phân lập 3 không gian vector riêng biệt |

### Lệnh cài đặt

```bash
# Kích hoạt môi trường ảo Python 3.11+
.\.venv\Scripts\activate

# Cài đặt toàn bộ dependencies của project
python -m pip install -e .
```

### Lệnh chạy kiểm chứng

**1. Chạy toàn bộ luồng Phase 1 Baseline Pipeline:**
```bash
python script/run_phase1.py
```

**2. Chạy toàn bộ luồng Phase 2 Corruption & Self-Healing Repair:**
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :--- | :--- | :--- |
| `python script/run_phase1.py` | Thành công | 2026-09-25 15:57:29 | Exit code 0, sinh đủ 5 artifacts, console in: `PHASE 1 BASELINE PIPELINE HOAN THANH XUAT SAC!` |
| `python script/run_corruption_flow.py` | Thành công | 2026-09-25 16:01:56 | Exit code 0, bảng đối chiếu 3 trạng thái in ra console, sinh `corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| Source | Crossref REST API công khai (`https://api.crossref.org/works`) |
| Query / filter | `query=agentic retrieval augmented generation large language model`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 (Snapshot dự phòng: `data/raw/crossref_response.json`) |
| Số record nhận được | 24 bài báo khoa học |
| Cơ chế retry / fallback | Khi API trả về lỗi `429 Too Many Requests` hoặc phòng lab mất mạng, hệ thống tự động fallback đọc snapshot có sẵn tại `data/raw/crossref_response.json` không gây dừng luồng. |

### Schema raw và clean

| Tên trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa nghiệp vụ | Cách xử lý khi thiếu / sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` (DOI) | Có | Mã định danh duy nhất của công trình | Chuẩn hóa lowercase/strip, loại bỏ record rỗng |
| `title` | `str` | Có | Tiêu đề bài báo | Chuẩn hóa khoảng trắng thừa, bỏ record nếu rỗng |
| `summary` | `str` | Có | Tóm tắt bài báo | Loại bỏ regex `<[^>]+>` (JATS XML), strip khoảng trắng |
| `authors` | `list[str]` | Có | Danh sách tác giả | Ghép `given` + `family`, nếu thiếu gán `["Unknown Author"]` |
| `categories` | `list[str]` | Có | Chuyên ngành / lĩnh vực | Chuẩn hóa danh sách, nếu thiếu gán `["Artificial Intelligence"]` |
| `published` | `str` (YYYY-MM-DD) | Có | Ngày công bố chính thức | Trích xuất date-parts ISO 8601, nếu lỗi gán `2026-01-01` |
| `age_days` | `int` | Có | Tuổi thọ dữ liệu tính theo ngày | `max(0, (run_date - pub_date).days)` |
| `text_for_embedding` | `str` | Có | Ngữ cảnh toàn diện phục vụ vector search | Ghép 5 trường chuẩn có tiền tố rõ ràng |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record tác động | Cách xác minh |
| :--- | :--- | :---: | :--- |
| Loại bỏ thẻ HTML/JATS XML rác trong tóm tắt | Validity / Cleanliness | 24 | `re.sub(r"<[^>]+>", " ", abstract_raw)` |
| Khử trùng lặp theo khóa duy nhất `paper_id` | Uniqueness | 24 bản ghi duy nhất | GX `ExpectColumnValuesToBeUnique` = PASSED |
| Bắt buộc không để null `paper_id`, `title`, `text_for_embedding` | Completeness | 24 | GX `ExpectColumnValuesToNotBeNull` = PASSED |
| Độ dài tối thiểu phần tóm tắt >= 30 ký tự | Accuracy / Sufficiency | 24 | GX `ExpectColumnValueLengthsToBeBetween` = PASSED |
| Tính toán tuổi thọ dữ liệu và phân loại quá hạn | Freshness | 24 | `freshness_report.json` ghi nhận 1 bài stale (4.17%) |

**Cấu trúc trường `text_for_embedding`:**
```text
Title: <Tiêu đề bài báo>
Authors: <Danh sách tác giả ngăn cách bởi dấu phẩy>
Published: <Ngày xuất bản định dạng YYYY-MM-DD>
Categories: <Lĩnh vực chuyên môn>
Summary: <Đoạn tóm tắt nội dung đã loại bỏ toàn bộ thẻ rác XML>
```

---

## 6. Cấu hình đánh giá (Evaluation Setup)

| Thành phần | Cấu hình thực tế | Ghi chú |
| :--- | :--- | :--- |
| Số câu hỏi benchmark | **5** câu hỏi mẫu | Phủ trọn 5 dạng câu hỏi nghiên cứu |
| Các `question_type` | `summary`, `authors`, `date`, `category`, `multi_hop` | Đánh giá cả đơn tài liệu và tổng hợp đa tài liệu |
| Ground-truth document ID | DOI bài báo tương ứng | So khớp chính xác với `retrieved_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | Đo khoảng cách Cosine trên không gian vector |
| Vector store / collections | ChromaDB local (`data/chroma`) | `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | `4` | Lấy 4 tài liệu liên quan nhất cho mỗi query |
| LLM provider / model | `9router` (`parrotgo`) | Đánh giá trích xuất câu trả lời và chấm điểm Judge |
| Benchmark Test Set | `data/eval/test_set.json` | **Dùng chung cố định** cho cả 3 trạng thái để đảm bảo tính khách quan |

**Lý do giữ nguyên test set cho cả 3 trạng thái:**  
Để đo lường chuẩn xác tác động tiêu cực của dữ liệu bẩn và hiệu quả khôi phục của cơ chế repair, tập đề thi (ground truth benchmark) phải được giữ làm biến độc lập cố định. Nếu thay đổi câu hỏi kiểm thử giữa các trạng thái, sự thay đổi điểm số sẽ bị nhiễu và không phản ánh đúng chất lượng của tầng dữ liệu (Data Foundation).

---

## 7. Kết quả Baseline (Pha 1)

### Bảng kiểm tra Artifacts (Checklist)

| STT | Artifact yêu cầu | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :---: | :--- | :--- | :---: | :--- |
| 1 | Raw response & records | `data/raw/crossref_records.json` | **CÓ** | Đủ 24 records bóc tách chuẩn |
| 2 | Cleaned dataset | `data/clean/papers_clean.csv` | **CÓ** | Đầy đủ 24 dòng sạch hoàn chỉnh |
| 3 | Embedding manifest/index | `data/embeddings/papers_embeddings.json` | **CÓ** | Collection `papers-baseline` |
| 4 | Benchmark Test set | `data/eval/test_set.json` | **CÓ** | 5 câu hỏi phủ đủ 5 dạng nghiệp vụ |
| 5 | Baseline metrics | `data/results/baseline_metrics.json` | **CÓ** | Lưu trữ chỉ số Hit Rate, F1, Judge |
| 6 | Quality & Freshness report | `data/quality/baseline_quality_report.json` | **CÓ** | GX 1.x passed, Freshness passed |
| 7 | Baseline Markdown Report | `data/reports/phase1_report.md` | **CÓ** | Báo cáo chi tiết định dạng Markdown |

### Chỉ số hiệu năng Baseline

| Metric | Giá trị thực tế | Diễn giải kết quả của nhóm |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **100.00%** | Toàn bộ 5/5 câu hỏi đều trích xuất đúng tài liệu chứa ground truth vào top 4 context |
| `mean_token_f1` | **0.4125** | Độ trùng khớp từ vựng cao giữa câu trả lời trích xuất và ground truth |
| `judge_accuracy` | **40.00%** | Tỷ lệ câu trả lời được LLM Judge thẩm định chính xác tuyệt đối |
| `mean_judge_score` | **2.60 / 5.0** | Điểm số chất lượng trung bình của câu trả lời trích xuất trên nền dữ liệu sạch |

---

## 8. Data Quality & Freshness Monitoring

### Kết quả kiểm định Great Expectations 1.x (Data Quality Gate)

| Tên Expectation | Chiều chất lượng | Ngưỡng / Kỳ vọng | Kết quả Baseline | Bằng chứng kiểm tra |
| :--- | :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] dòng | **PASSED** (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (paper_id) | Completeness | Không được null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (paper_id) | Uniqueness | Không có trùng lặp | **PASSED** (100% unique) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (title) | Completeness | Không được null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (text_for_embedding) | Completeness | Không được null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (summary) | Validity / Length | Độ dài >= 30 ký tự | **PASSED** (min > 30) | `baseline_quality_report.json` |

### Giám sát độ tươi mới (Freshness SLA)

| Thuộc tính | Giá trị thực tế |
| :--- | :--- |
| Vị trí đo lường | `data/clean/papers_clean.csv` |
| Ngày công bố mới nhất | `2026-07-22` |
| Ngày công bố cũ nhất | `2026-03-28` |
| Ngưỡng Freshness SLA quy định | `180` ngày |
| Số bản ghi quá hạn (> 180 ngày) | `1` bản ghi |
| Tỷ lệ quá hạn (Stale Ratio) | **4.17%** (Ngưỡng cảnh báo: > 25.00%) |
| Trạng thái Freshness Baseline | **FRESH (Đạt chuẩn tươi mới)** |

---

## 9. Kịch bản làm bẩn dữ liệu (Data Corruption) và cơ chế tự phục hồi (Repair)

| STT | Kịch bản lỗi | Cách tạo lỗi | Record bị ảnh hưởng | Tín hiệu Quality kỳ vọng | Tác động thực tế lên RAG | Cách Repair |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- |
| **1** | **Drop latest records** | Bỏ rơi 2 bài báo mới nhất (`iloc[:2]`) | 2 bản ghi mới nhất | Thiếu bài mới | Mất context mới, làm sụp đổ Hit Rate ở câu hỏi liên quan | Đọc lại từ bản raw snapshot gốc |
| **2** | **Blank summary** | Gán `summary = ""` ở 2 bài báo | 2 bản ghi | GX `ExpectColumnValueLengthsToBeBetween` FAIL | Agent không có nội dung tóm tắt để trả lời câu hỏi summary | Re-fetch & load lại từ raw records |
| **3** | **Inject text noise** | Thêm tiền tố chuỗi rác `### CORRUPTED_NOISE...` | 2 bản ghi | Phá vỡ khoảng cách vector embedding | Vector cosine distance bị lệch, trích xuất sai tài liệu | Tái tạo lại `text_for_embedding` từ raw |
| **4** | **Truncate title** | Cắt tiêu đề bài báo xuống 8 ký tự (< 10 ký tự) | 2 bản ghi | Mất tính mô tả của title | Khớp truy vấn exact lookup bị thất bại | Khôi phục tiêu đề gốc từ `PaperRecord` |
| **5** | **Stale date** | Đổi năm xuất bản về 5 năm trước (`age_days += 1825`) | 8 bản ghi | Freshness SLA cảnh báo **STALE** (tỷ lệ > 25%) | Agent trả lời sai mốc thời gian xuất bản | Ghi đè lại ngày ISO 8601 từ raw |
| **6** | **Duplicate rows** | Nhân bản 2 dòng dữ liệu | 2 bản ghi | GX `ExpectColumnValuesToBeUnique` **FAIL** | Làm loãng top-k search, nạp trùng bản ghi vào ChromaDB | Khử trùng lặp qua deduplication logic |

**Nhật ký lỗi (Corruption Log):**
- Đường dẫn: [data/results/corruption_log.json](file:///c:/VIN_AI_THUC_CHIEN/K4A-DAY10-Group16-T016/data/results/corruption_log.json)
- Trạng thái: **ĐẦY ĐỦ**
- Nhận xét: Ghi nhận chính xác 6 kịch bản, thời gian khởi tạo, tổng số dòng ban đầu (24), số dòng sau corrupt (24) và danh sách chi tiết các DOI bị tác động.

**Cơ chế Idempotent Repair:**
Thay vì sửa lỗi thủ công chắp vá trên file bẩn (anti-pattern), hệ thống áp dụng nguyên lý **Idempotency**: chạy lại toàn bộ hàm `build_clean_dataframe` trực tiếp từ nguồn dữ liệu thô ban đầu `data/raw/crossref_records.json`. Do bản raw luôn được giữ nguyên đai nguyên kiện, quy trình biến đổi luôn tạo ra cùng một kết quả sạch duy nhất bất kể chạy bao nhiêu lần, đảm bảo 100% tính toàn vẹn của dữ liệu.

---

## 10. Bảng so sánh 3 trạng thái: Baseline vs Corrupted vs Repaired

| Chỉ số / Tín hiệu đánh giá | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu bẩn) | Repaired (Sau phục hồi) | Thay đổi do corruption | Mức phục hồi | Nhận xét phân tích |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **0.00%** | **100.00%** | Giảm tuyệt đối -100% | **Phục hồi 100%** | Dữ liệu lỗi khiến ChromaDB trích xuất sai hoàn toàn context; sau repair Agent tìm lại đúng 100% tài liệu |
| **Mean Token F1** | **0.4125** | **0.0000** | **0.4125** | Giảm về 0 | **Phục hồi 100%** | Khi context bị mất hoặc nhiễu, câu trả lời không còn từ khóa ground-truth; sau repair độ tương đồng lấy lại hoàn toàn |
| **LLM Judge Score** | **2.60 / 5.0** | **1.00 / 5.0** | **2.60 / 5.0** | Giảm xuống mức sàn (1.0) | **Phục hồi 100%** | AI Agent bị Silent Failure khi gặp dữ liệu lỗi; lấy lại toàn bộ phong độ sau khi dữ liệu được làm sạch |
| **GX Quality Status** | **PASSED** | **FAILED** | **PASSED** | Báo động đỏ | **Khôi phục PASSED** | Quality Gate chặn đứng vi phạm trùng lặp và thiếu độ dài tóm tắt |
| **Freshness SLA Status** | **FRESH** | **STALE** | **FRESH** | Cảnh báo quá hạn | **Khôi phục FRESH** | Tỷ lệ bài quá hạn giảm từ 37.5% về mức an toàn 4.17% |

### Hai kết luận nhân quả được hỗ trợ bởi Artifacts:
1. **[Data Corruption] → [Quality/Freshness Signal] → [Agent Performance Drop]:**  
   Khi thực hiện xóa tóm tắt và đổi ngày về 5 năm trước, Great Expectations lập tức báo lỗi `ExpectColumnValueLengthsToBeBetween: FAILED` và Freshness báo `is_fresh = False`. Sự suy giảm dữ liệu này trực tiếp kéo theo **Retrieval Hit Rate sụt từ 100% về 0.00%** và **Judge Score giảm từ 2.60 xuống 1.00**, chứng minh hiện tượng Silent Failure.
2. **[Idempotent Repair] → [Quality Signal Recovery] → [Agent Performance Recovery]:**  
   Hành động nạp lại dữ liệu từ `data/raw/crossref_records.json` đã phục hồi toàn bộ schema sạch, đưa trạng thái GX 1.x trở lại `PASSED` và Freshness trở lại `FRESH`. Kết quả là toàn bộ các chỉ số của Agent (`Retrieval Hit Rate`, `Token F1`, `Judge Score`) **lấy lại chính xác 100% giá trị Baseline**.

---

## 11. Vấn đề tích hợp quan trọng và cách xử lý

- **Triệu chứng:** Khi chạy script trên PowerShell ở máy Windows, chương trình gặp lỗi:  
  `UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>`
- **Nguyên nhân gốc:** Bảng mã mặc định của Windows PowerShell là `cp1252`, không tương thích khi in các chuỗi ký tự tiếng Việt có dấu (`Tín hiệu hoàn thành...`) từ Python mà không có cấu hình encoding cho stdout.
- **Cách xử lý:** 
  1. Cấu hình biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước khi thực thi lệnh trong PowerShell.
  2. Chuẩn hóa các thông báo log và console quan trọng bằng tiếng Việt không dấu hoặc text chuẩn an toàn, đồng thời thiết lập tham số `encoding="utf-8"` rõ ràng trong tất cả các thao tác đọc/ghi file (`write_text`, `open()`, `pd.to_csv()`).
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py`, toàn bộ pipeline hoàn thành trơn tru với exit code 0 mà không phát sinh bất kỳ ngoại lệ nào.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng thực tế | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Kích thước tập dữ liệu còn nhỏ (24 bài báo) | Chưa kiểm thử được giới hạn chịu tải lớn và phân mảnh bộ nhớ của Vector DB | Mở rộng tham số `max_results=500` và đo lường độ trễ truy vấn (latency benchmark) |
| Bộ câu hỏi benchmark gồm 5 câu | Chưa bao quát hết mọi tình huống biên (edge cases) | Tự động sinh bộ 50+ câu hỏi đa dạng bằng synthetic question generator |
| Kích hoạt Repair còn mang tính thủ công | Cần người vận hành chạy lệnh `run_corruption_flow.py` khi thấy cảnh báo | Tích hợp **Automated Self-Healing** (tự động rollback và repair ngay khi Quality Gate báo `FAILED`) |

---

## 13. Checklist nghiệm thu bài nộp

- [x] Thông tin nhóm (`Group 16`, `T016`) và repository chính xác.
- [x] Phân công công việc khớp 50% / 50% giữa Chu Minh Quân và Nguyễn Văn Ước.
- [x] Lệnh tái hiện đã được chạy lại và kiểm chứng thành công trên môi trường thực tế.
- [x] Baseline, Corrupted và Repaired đều dùng chung một bộ benchmark test set (`data/eval/test_set.json`).
- [x] Bảng metrics trong báo cáo khớp 100% với các file JSON trong `data/results/`.
- [x] Kết luận Data Quality và Freshness khớp 100% với các báo cáo trong `data/quality/`.
- [x] Tất cả các đường dẫn artifacts và báo cáo Markdown đều truy cập được.
- [x] Báo cáo của từng cá nhân (`2A202602709_ChuMinhQuan.md` và `2A202602445_NguyenVanUoc.md`) đã được tạo đầy đủ.
- [x] Hoàn toàn không có API Key bí mật hay token trong Git history hoặc nội dung báo cáo.
