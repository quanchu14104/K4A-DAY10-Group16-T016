# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung |
| ----------------- | ------------------------------------------------------ |
| **Họ và tên**     | **Chu Minh Quân** |
| **MSSV**          | **2A202602709** |
| **Khóa/Lớp**      | K4 — DAY10 |
| **Tên nhóm**      | Group 16 (`T016` / `K4A-DAY10-Group16-T016`) |
| **Vai trò chính** | **Trưởng nhóm / Architecture, Observability & Pipeline Integrator** |
| **Repository**    | https://github.com/quanchu14104/K4A-DAY10-Group16-T016 |
| **Ngày hoàn thành** | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu (50% tỷ trọng dự án)

| Module / deliverable | File / hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Hệ thống cấu hình** | `src/core/config.py`<br>`src/core/utils.py` | Biến môi trường `.env`, cấu trúc thư mục dự án | Đối tượng `Settings` an toàn, quản lý toàn bộ paths của 3 trạng thái | Hoàn thành |
| **Data Observability Gate** | `src/observability/quality.py`<br>`run_data_quality_checks`<br>`build_freshness_report` | Cleaned `pd.DataFrame`, cấu hình `Settings` | `data/quality/baseline_quality_report.json`<br>`data/quality/freshness_report.json` | Hoàn thành |
| **Baseline Orchestration** | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Toàn bộ các module thành phần của Phase 1 | Pipeline chạy 1 lệnh, sinh đủ 5 artifacts của Phase 1 | Hoàn thành |
| **Hệ thống báo cáo Markdown** | `src/observability/reporting.py`<br>`generate_phase1_report`<br>`generate_corruption_report` | Metrics, Quality report, Freshness report | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Điều phối kiến trúc & xử lý encoding UTF-8** | Nguyễn Văn Ước / Console scripts | Khắc phục triệt để lỗi `UnicodeEncodeError` trên Windows PowerShell bằng biến môi trường `PYTHONIOENCODING="utf-8"`. |
| **Tích hợp provider LLM local 9router** | Module `src/retrieval/llm.py` | Cấu hình cho phép hệ thống fallback mượt mà sang `9router` (`parrotgo`) tại `http://localhost:20128/v1` mà không làm gián đoạn bài lab khi không có OpenAI/Gemini key. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Cấu hình đa tầng & Paths** | `src/core/config.py` | Đối tượng `Settings` đóng gói đường dẫn 3 trạng thái (baseline, corrupted, repaired) | `python -c "from core.config import load_settings; s=load_settings(); print(s.llm_provider)"` in ra `9router` |
| **Trạm kiểm soát GX 1.x** | `src/observability/quality.py` | Thẩm định 4 kỳ vọng thiết yếu và đo lường độ tươi `age_days` | `run_data_quality_checks(...)` trả về `overall_success = True` |
| **Phase 1 Pipeline End-to-End** | `src/pipelines/phase1.py` | Tự động hóa 7 bước, kết nối Ingestion -> Cleaning -> Index -> Eval -> Observability | `python script/run_phase1.py` hoàn thành xuất sắc với exit code 0 |
| **Tự động xuất báo cáo Markdown** | `src/observability/reporting.py` | Xuất 2 báo cáo chi tiết đầy đủ bảng số liệu đối chiếu định dạng Markdown | Tệp tin `phase1_report.md` và `corruption_report.md` xuất hiện trong `data/reports/` |

**Output cụ thể chứng minh kết quả:**  
Báo cáo tổng hợp [data/reports/phase1_report.md](file:///c:/VIN_AI_THUC_CHIEN/K4A-DAY10-Group16-T016/data/reports/phase1_report.md) được tạo tự động với đầy đủ kết quả kiểm tra GX 1.x (6/6 checks PASSED), chỉ số Freshness SLA (4.17% stale, đạt chuẩn FRESH), và bảng đối chiếu metrics (Retrieval Hit Rate: 100.00%, Token F1: 0.4125, Judge Score: 2.60).

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG rất dễ gặp hiện tượng **Silent Failure**: khi dữ liệu đầu vào bị thiếu trường, trùng lặp hoặc quá hạn, ứng dụng không hề báo lỗi crash mà vẫn sinh câu trả lời với sự tự tin cao nhưng sai lệch sự thật. Để giải quyết vấn đề này, tôi cần:
1. Xây dựng một **Data Quality Gate** tự động kiểm định dữ liệu ngay trước khi được nạp vào Vector Database.
2. Giám sát độ tươi mới dữ liệu theo thỏa thuận mức dịch vụ (**Freshness SLA**) để tránh nạp dữ liệu cũ quá 180 ngày.
3. Ghép nối toàn bộ luồng thực thi trong một lệnh duy nhất có tính lặp lại (Idempotency) và xuất báo cáo minh bạch.

### Cách triển khai
1. **Chuẩn Great Expectations 1.x (ephemeral context):**
   Thay vì dùng API cũ `context.sources.pandas_default` vốn đã bị deprecate và gây lỗi trên GX 1.x, tôi triển khai chuẩn API mới chạy tạm thời trên RAM để đạt tốc độ cao và không sinh file rác:
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name=f"papers_source_{safe_name}")
   data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{safe_name}")
   batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{safe_name}")
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   ```
2. **Thiết lập 4 kỳ vọng bắt buộc:**
   - `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`
   - `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding`
   - `ExpectColumnValuesToBeUnique` cho `paper_id`
   - `ExpectColumnValueLengthsToBeBetween` cho `summary` (độ dài >= 30 ký tự)
3. **Freshness SLA Monitoring:**
   Tính toán tỷ lệ bản ghi có `age_days > 180`. Nếu tỷ lệ vượt quá 25%, hệ thống lập tức gắn cờ `is_fresh = False`.
4. **Pipeline Orchestrator:**
   Trong `src/pipelines/phase1.py`, tôi liên kết tuần tự từ việc đọc dữ liệu thô, biến đổi, index vào ChromaDB, đánh giá trên Benchmark Test Set và sinh báo cáo tổng hợp.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Cleaned DataFrame `df` chứa đầy đủ các cột dữ liệu đã chuẩn hóa |
| **Output** | `report_payload` dictionary và file JSON report tại `data/quality/` |
| **Module phụ thuộc** | `src/ingestion/cleaning.py` (cung cấp cleaned DataFrame) |
| **Module sử dụng output** | `src/retrieval/index.py` (chỉ index khi Quality Gate pass), `src/observability/reporting.py` |
| **Điều kiện lỗi xử lý** | DataFrame rỗng, cột bị thiếu, hoặc giá trị `published` không đúng định dạng ngày tháng |

### Cách xác minh

```powershell
python script/run_phase1.py
```

- **Kết quả mong đợi:** Toàn bộ pipeline chạy thành công, console in thông báo hoàn thành kèm bảng tóm tắt chỉ số, file `data/reports/phase1_report.md` xuất hiện.
- **Kết quả thực tế:** Pipeline chạy với exit code 0, Hit Rate đạt 100.00%, GX Status: PASSED, Freshness: FRESH.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức triển khai Great Expectations giữa việc tạo thư mục cấu hình file tĩnh (`gx/great_expectations.yml`) và sử dụng chế độ bộ nhớ đệm (`ephemeral mode`).
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Khởi tạo thư mục `gx/` trên đĩa cứng và lưu trữ Data Context dưới dạng file YAML.
  - *Phương án B:* Khởi tạo Data Context theo cơ chế `ephemeral` (tạm thời trên RAM) trực tiếp qua mã nguồn Python.
- **Phương án đã chọn:** Phương án B (`mode="ephemeral"`).
- **Lý do:** Chế độ `ephemeral` giúp pipeline chạy cực nhanh, không đẻ các file metadata rác vào repo Git, không phụ thuộc vào đường dẫn tuyệt đối local của máy người chấm, đồng thời phù hợp hoàn hảo với kiến trúc pipeline CI/CD hiện đại.
- **Bằng chứng phù hợp:** Thời gian thực thi kiểm định toàn bộ 24 dòng và 6 expectations chỉ mất chưa tới 0.15 giây.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng / Lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>
  ```
- **Lệnh tái hiện:** Chạy bất kỳ lệnh Python nào có lệnh `print("Môi trường sẵn sàng")` trên terminal Windows PowerShell mặc định.
- **Nguyên nhân gốc:** Windows PowerShell sử dụng bảng mã mặc định là `cp1252` thay vì `utf-8`, dẫn đến việc không thể mã hóa các ký tự tiếng Việt có dấu khi in ra `sys.stdout`.
- **Cách xử lý:** 
  1. Thêm cấu hình biến môi trường trước khi chạy lệnh: `$env:PYTHONIOENCODING="utf-8"`.
  2. Bổ sung tham số `encoding="utf-8"` trong tất cả các hàm ghi file báo cáo Markdown (`Path.write_text(..., encoding="utf-8")`).
  3. Chuẩn hóa các thông báo print tóm tắt cuối cùng bằng tiếng Việt không dấu an toàn.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh trên PowerShell, console in ra mượt mà không còn bất kỳ lỗi mã hóa nào.
- **Điều học được:** Luôn chủ động quản lý encoding trên môi trường cross-platform (đặc biệt là Windows) trong các dự án dữ liệu và AI.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Crossref REST API trả về JSON thô -> Lưu trữ nguyên đai nguyên kiện vào `crossref_response.json` (bảo toàn Lineage) -> Bóc tách thành `PaperRecord` lưu vào `crossref_records.json` -> Làm sạch, lọc thẻ XML, tính `age_days`, ghép `text_for_embedding` -> Thẩm định qua Great Expectations 1.x -> Sinh vector nhúng bằng `all-MiniLM-L6-v2` và lưu trữ vào ChromaDB PersistentClient.
2. **Vai trò của Evaluation set và Ground-truth document IDs:**  
   Evaluation set đóng vai trò là "đề thi chuẩn", mỗi câu hỏi có kèm theo mã DOI của tài liệu chứa đáp án chuẩn (`ground_truth_doc_ids`). Khi Agent trích xuất các tài liệu qua tìm kiếm ngữ nghĩa, ta so sánh tập `retrieved_doc_ids` với `ground_truth_doc_ids`. Nếu tài liệu chuẩn nằm trong top-k, hệ thống được tính là 1 điểm Hit (`retrieval_hit = True`).
3. **Sự khác biệt giữa Quality checks và Freshness monitoring:**  
   Quality checks thẩm định tính đúng đắn về mặt cấu trúc và nội hàm của dữ liệu tại thời điểm nạp (Schema, Nullability, Uniqueness, Min Length). Còn Freshness monitoring đo lường sự suy thoái theo thời gian (Data Decay / Drift), cảnh báo khi tỷ lệ bài báo quá cũ vượt ngưỡng cho phép dù dữ liệu đó vẫn đúng cấu trúc schema.
4. **Lý do dùng chung test set cho cả 3 trạng thái:**  
   Để đánh giá công bằng và khoa học, tập đề thi phải là hằng số bất biến. Nếu thay đổi câu hỏi giữa các lần chạy, sự thay đổi điểm số sẽ không thể quy kết là do chất lượng dữ liệu bẩn hay do độ khó của câu hỏi mới.
5. **Tiêu chuẩn công nhận Repair thành công:**  
   Repair được coi là thành công khi:
   - Dữ liệu sạch được tái lập 100% từ bản sao lưu thô ban đầu (Idempotent).
   - Great Expectations chuyển trạng thái từ `FAILED` về `PASSED`.
   - Freshness SLA chuyển trạng thái từ `STALE` về `FRESH`.
   - Toàn bộ các chỉ số của Agent (`Retrieval Hit Rate`, `Token F1`, `Judge Score`) khôi phục lại hoàn toàn mức điểm Baseline ban đầu.

---

## 8. Phân tích kết quả

### Bảng chỉ số đối chiếu 3 trạng thái

| Metric / Signal | Baseline (Sạch) | Corrupted (Lỗi) | Repaired (Phục hồi) | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.00%** | **0.00%** | **100.00%** | Dữ liệu lỗi làm mất hoàn toàn khả năng tìm kiếm tài liệu chuẩn; phục hồi triệt để sau repair |
| `mean_token_f1` | **0.4125** | **0.0000** | **0.4125** | Do không tìm được tài liệu, câu trả lời không khớp từ vựng; khôi phục 100% sau repair |
| `mean_judge_score` | **2.60 / 5.0** | **1.00 / 5.0** | **2.60 / 5.0** | Điểm số đánh giá chất lượng giảm xuống mức thấp nhất và lấy lại hoàn toàn phong độ |
| `GX Quality status` | **PASSED** | **FAILED** | **PASSED** | Quality Gate chặn đứng lỗi trùng lặp và thiếu tóm tắt |
| `Freshness SLA` | **FRESH** | **STALE** | **FRESH** | Tỷ lệ bài quá hạn giảm từ 37.5% về mức an toàn 4.17% |

### Hai chuỗi quan hệ nhân quả:
1. `[Tiêm lỗi xóa summary & mốc thời gian]` → `[GX báo FAILED & Freshness báo STALE]` → `[Hit Rate giảm từ 100% về 0% và Judge Score giảm từ 2.60 về 1.00]`.
2. `[Idempotent Repair nạp lại từ raw]` → `[GX trở lại PASSED & Freshness trở lại FRESH]` → `[Hit Rate phục hồi về 100% và Judge Score phục hồi về 2.60]`.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. **Về Data Pipeline:** Pipeline phải được thiết kế có tính **Idempotent** (bất biến với số lần chạy lại) và luôn bảo tồn dữ liệu thô (Raw Preservation) làm lá chắn phòng thủ cao nhất.
2. **Về Data Quality / Observability:** Great Expectations 1.x kết hợp cùng Freshness SLA tạo thành một "chốt kiểm dịch" vững chắc, phát hiện tức thì các sự cố dữ liệu trước khi chúng xâm nhập vào không gian vector.
3. **Về tác động của dữ liệu lên AI Agent:** "Garbage in, Garbage out" — AI Agent dù thông minh đến đâu cũng sẽ bị vô hiệu hóa (Silent Failure) nếu tầng dữ liệu nền tảng bị ô nhiễm.

### Nếu có thêm thời gian:
Tôi sẽ xây dựng cơ chế **Automated Self-Healing**: Khi Data Quality Gate phát hiện vi phạm, hệ thống sẽ tự động kích hoạt tiến trình rollback hoặc nạp lại từ Raw Snapshot mà không cần con người phải can thiệp thủ công.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh trung thực phần việc và mức độ hiểu biết của tôi.
- [x] Tôi có thể tự tin bảo vệ và giải thích trọn vẹn luồng end-to-end trước Giảng viên và lớp.
- [x] Mọi kết luận và số liệu trong báo cáo đều được trích xuất trực tiếp từ các file artifacts thực tế.
- [x] Báo cáo tuyệt đối không chứa API Key, token bí mật hay file cấu hình `.env`.

**Họ và tên:** Chu Minh Quân  
**Ngày xác nhận:** 2026-09-25
