# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung |
| ----------------- | ------------------------------------------------------ |
| **Họ và tên**     | **Nguyễn Văn Ước** |
| **MSSV**          | **2A202602445** |
| **Khóa/Lớp**      | K4 — DAY10 |
| **Tên nhóm**      | Group 16 (`T016` / `K4A-DAY10-Group16-T016`) |
| **Vai trò chính** | **Data Foundation, Vector Retrieval & Corruption Specialist** |
| **Repository**    | https://github.com/quanchu14104/K4A-DAY10-Group16-T016 |
| **Ngày hoàn thành** | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu (50% tỷ trọng dự án)

| Module / deliverable | File / hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Ingestion & Lineage** | `src/ingestion/crossref.py`<br>`fetch_source_records`<br>`parse_crossref_payload` | Crossref REST API hoặc local snapshot | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Hoàn thành |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>`build_clean_dataframe` | Danh sách `PaperRecord` từ raw records | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 dòng sạch) | Hoàn thành |
| **Vector Store & Indexing** | `src/retrieval/index.py`<br>`LocalEmbeddingIndex.build`<br>`semantic_search` | Cleaned DataFrame, MiniLM embedding | ChromaDB collection `papers-baseline` & `papers_embeddings.json` | Hoàn thành |
| **Benchmark Test Set** | `src/evaluation/testset.py`<br>`build_test_set`<br>`load_or_create_test_set` | Cleaned DataFrame | `data/eval/test_set.json` (5 câu hỏi chuẩn 5 dạng nghiệp vụ) | Hoàn thành |
| **Synthetic Data Corruption & Repair** | `src/ingestion/corruption.py`<br>`src/pipelines/corruption_flow.py` | Cleaned DataFrame & Raw snapshot | `data/results/corruption_log.json`<br>`corrupted_clean.csv`, `repaired_clean.csv` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Kiểm thử tích hợp Great Expectations 1.x** | Chu Minh Quân / Module Observability | Hỗ trợ kiểm thử các Expectation trên dữ liệu sau khi clean, đảm bảo không có trường nào bị null trước khi chuyển sang trạm kiểm dịch. |
| **Tối ưu hóa câu hỏi Benchmark** | Module `src/evaluation/metrics.py` | Tinh chỉnh ground-truth text và định dạng câu hỏi trong `test_set.json` để khớp chuẩn xác với thuật toán tính Token F1 và trích xuất ngữ cảnh. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Thu thập dữ liệu thô (Dual-Mode)** | `src/ingestion/crossref.py` | Thu thập và bóc tách thành công 24 bài báo học thuật chuẩn DOI | `fetch_source_records(s)` in ra: `Đã nạp 24 bài báo` |
| **Làm sạch & Chuẩn hóa ngữ cảnh** | `src/ingestion/cleaning.py` | Loại bỏ rác XML, khử trùng lặp, tạo `text_for_embedding` 5 phần | `build_clean_dataframe(...)` in ra: `Clean thành công 24 dòng` |
| **Lập chỉ mục Vector ChromaDB** | `src/retrieval/index.py` | Index 24 vector vào ChromaDB với mô hình `all-MiniLM-L6-v2` | `idx.semantic_search('machine learning', top_k=2)` tìm thấy 2 tài liệu |
| **Bộ câu hỏi Benchmark Ground Truth** | `src/evaluation/testset.py` | Sinh 5 câu hỏi phủ đủ 5 nhóm: summary, authors, date, category, multi_hop | `load_or_create_test_set(...)` in ra: `Test set gồm 5 câu hỏi` |
| **Tiêm độc tố dữ liệu (6 kịch bản)** | `src/ingestion/corruption.py` | Triển khai đủ 6 kịch bản lỗi, ghi log chi tiết vào JSON | Console in ra: `Tín hiệu hoàn thành: Corrupted 24 dòng` |
| **Idempotent Self-Healing Repair** | `src/pipelines/corruption_flow.py` | Khôi phục 100% dữ liệu sạch từ raw snapshot, đưa điểm số về ban đầu | Bảng đối chiếu in ra console và file `data/reports/corruption_report.md` |

**Output cụ thể chứng minh kết quả:**  
File nhật ký lỗi [data/results/corruption_log.json](file:///c:/VIN_AI_THUC_CHIEN/K4A-DAY10-Group16-T016/data/results/corruption_log.json) ghi nhận đầy đủ 6 hành động tiêm lỗi có chủ đích, và lệnh chạy `python script/run_corruption_flow.py` chứng minh sự sụt giảm và phục hồi hoàn toàn của hệ thống RAG Agent.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Rủi ro phụ thuộc API bên ngoài:** Khi cào dữ liệu từ Crossref API, hệ thống rất dễ bị gián đoạn do lỗi rate limit (`429 Too Many Requests`) hoặc mất mạng. Cần cơ chế tự động chuyển vùng sang snapshot lưu trữ sẵn (Dual-Mode Fallback).
2. **Nguyên lý bảo toàn dữ liệu gốc (Raw Preservation):** Nếu lưu đè hoặc sửa đổi trực tiếp dữ liệu thô, khi có lỗi xảy ra trong pipeline ta sẽ mất vĩnh viễn khả năng khôi phục.
3. **Mô phỏng sự cố dữ liệu thực tế (Data Corruption):** Cần một bộ kịch bản lỗi thực tế (mất bài mới, rỗng tóm tắt, nhiễu ký tự, tiêu đề bị cụt, mốc thời gian, bản ghi trùng lặp) để chứng minh Data Quality Gate hoạt động hiệu quả và đo lường sự suy giảm của AI Agent.
4. **Tự phục hồi an toàn (Idempotent Repair):** Xây dựng luồng sửa chữa tự động từ nguồn Raw tin cậy mà không sửa thủ công trên file lỗi.

### Cách triển khai
1. **Module `crossref.py` (Ingestion Dual-Mode):**
   - Thử gửi request tới Crossref API với query và filter quy định.
   - Nếu thành công, ghi đè snapshot thô `crossref_response.json`.
   - Nếu thất bại hoặc `refresh_source=False`, tự động đọc bản sao lưu có sẵn tại `data/raw/crossref_response.json`.
   - Bóc tách các trường dữ liệu và lưu danh sách `PaperRecord` chuẩn vào `data/raw/crossref_records.json`.
2. **Module `cleaning.py` (Chuẩn hóa tiền Vector):**
   - Dùng Regex `re.sub(r"<[^>]+>", " ", text)` để bóc tách toàn bộ thẻ JATS XML như `<jats:p>`.
   - Khử trùng lặp bản ghi qua `seen_paper_ids`.
   - Tính toán `age_days = (run_date - pub_date).days`.
   - Ghép trường `text_for_embedding` có cấu trúc rõ ràng: Title, Authors, Published, Categories, Summary.
3. **Module `corruption.py` (6 kịch bản lỗi có chủ đích):**
   - *Drop latest:* Bỏ 2 bài báo mới nhất để làm mất context thời sự.
   - *Blank summary:* Xóa rỗng trường `summary = ""` ở 2 bài báo.
   - *Inject noise:* Thêm tiền tố chuỗi ký tự rác vô nghĩa vào tóm tắt.
   - *Truncate title:* Cắt ngắn tiêu đề bài báo xuống 8 ký tự (< 10 ký tự).
   - *Stale date:* Lùi ngày xuất bản về 5 năm trước (`age_days += 1825`) để kích hoạt cảnh báo Freshness.
   - *Duplicate rows:* Nhân đôi 2 dòng dữ liệu đưa tổng số dòng về đúng 24 bản ghi, kích hoạt vi phạm Unique.
   - Tái tạo lại toàn bộ `text_for_embedding` và ghi log chi tiết ra `corruption_log.json`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | JSON payload từ Crossref API hoặc file snapshot `data/raw/crossref_response.json` |
| **Output** | `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/results/corruption_log.json` |
| **Module phụ thuộc** | `src/core/config.py` (lấy đường dẫn file và cấu hình) |
| **Module sử dụng output** | `src/observability/quality.py` (kiểm định), `src/retrieval/index.py` (tạo vector index) |
| **Điều kiện lỗi xử lý** | Mất mạng, mã lỗi HTTP 429, ngày xuất bản thiếu `date-parts`, tiêu đề có ký tự lạ |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```

- **Kết quả mong đợi:** Console in ra chuỗi `Tín hiệu hoàn thành: Corrupted 24 dòng`, tệp `data/results/corruption_log.json` được tạo thành công ghi nhận đủ 6 kịch bản.
- **Kết quả thực tế:** Hoàn toàn chính xác, log ghi nhận 24 dòng corrupted và 6 kịch bản lỗi chi tiết.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức sửa chữa dữ liệu (Data Repair) khi phát hiện dữ liệu bị ô nhiễm.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Viết script rà soát trên DataFrame bẩn và tìm cách "vá lỗi" tại chỗ (ví dụ: tìm dòng trùng thì xóa, tìm dòng rỗng thì gán giá trị mặc định).
  - *Phương án B (Idempotent Re-ingestion):* Vứt bỏ hoàn toàn dữ liệu bẩn và chạy lại quy trình làm sạch từ bản lưu trữ thô ban đầu `data/raw/crossref_records.json`.
- **Phương án đã chọn:** Phương án B (Idempotent Re-ingestion từ Raw Snapshot).
- **Lý do:** Phương án A chỉ là giải pháp tạm thời, không thể khôi phục được những thông tin đã bị mất (như các bài báo bị xóa hoặc tóm tắt bị tẩy trắng). Phương án B tuân thủ nguyên lý **Idempotency** và **Data Lineage** của kỹ nghệ dữ liệu hiện đại, đảm bảo dữ liệu phục hồi luôn đạt độ tin cậy tuyệt đối 100%.
- **Bằng chứng phù hợp:** Sau khi chạy repair theo phương án B, các chỉ số Retrieval Hit Rate và Token F1 của Agent phục hồi chính xác 100% về mức ban đầu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng / Lỗi nguyên văn:**
  ```text
  urllib.error.HTTPError: HTTP Error 429: Too Many Requests
  ```
- **Lệnh tái hiện:** Chạy hàm `fetch_source_records` gọi trực tiếp API Crossref nhiều lần liên tục khi nhiều nhóm trong phòng lab cùng gửi truy vấn.
- **Nguyên nhân gốc:** API Crossref áp dụng cơ chế Rate Limiting nghiêm ngặt đối với các IP gửi quá nhiều request cùng lúc mà không có token trả phí.
- **Cách xử lý:** Bổ sung khối lệnh `try...except` bắt lỗi mạng và HTTP errors trong `src/ingestion/crossref.py`. Nếu gặp lỗi, hệ thống tự động in log cảnh báo và chuyển vùng sang đọc snapshot offline có sẵn tại `data/raw/crossref_response.json`.
- **Cách xác minh sau khi sửa:** Ngắt kết nối mạng wifi và chạy lại lệnh ingestion, hệ thống vẫn nạp thành công 24 bài báo mà không bị crash.
- **Điều học được:** Mọi Data Pipeline sản xuất đều bắt buộc phải có cơ chế Fallback / Circuit Breaker để bảo vệ hệ thống trước sự bất định của các dịch vụ bên thứ ba.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Payload JSON gốc từ Crossref được bảo lưu an toàn tại `crossref_response.json` -> Bóc tách cấu trúc vào `crossref_records.json` -> Làm sạch văn bản, loại bỏ thẻ rác, tính `age_days` và tạo `text_for_embedding` vào `papers_clean.csv` -> Thẩm định qua Great Expectations 1.x -> Chuyển thành vector số thực 384 chiều qua mô hình MiniLM -> Lưu vào ChromaDB collection `papers-baseline`.
2. **Vai trò của Evaluation set và Ground-truth document IDs:**  
   Bộ testset chuẩn định nghĩa trước câu hỏi và mã DOI của tài liệu chứa chân lý (`ground_truth_doc_ids`). Khi Agent thực hiện tìm kiếm, ta kiểm tra xem DOI của tài liệu truy xuất có nằm trong tập ground truth hay không để tính chỉ số Retrieval Hit Rate một cách hoàn toàn khách quan.
3. **Sự khác biệt giữa Quality checks và Freshness monitoring:**  
   Quality checks thẩm tra xem dữ liệu có bị "rách" không (thiếu trường, sai kiểu, trùng lặp, rỗng). Freshness monitoring thẩm tra xem dữ liệu có bị "ôi thiu" không (bài báo xuất bản quá 180 ngày). Dữ liệu có thể hoàn toàn sạch về mặt cấu trúc nhưng vẫn bị quá hạn về mặt thời gian.
4. **Lý do dùng chung test set cho cả 3 trạng thái:**  
   Giữ nguyên test set là điều kiện tiên quyết để đảm bảo tính hợp lệ của phương pháp nghiên cứu thực nghiệm. Khi tập câu hỏi cố định, mọi sự sụt giảm hay phục hồi về điểm số đều phản ánh chính xác chất lượng của dữ liệu trong Vector Database.
5. **Tiêu chuẩn công nhận Repair thành công:**  
   Repair thành công khi:
   - Dữ liệu được khôi phục nguyên vẹn từ nguồn Raw gốc đã lưu trữ.
   - Great Expectations và Freshness SLA đều chuyển trạng thái sang `PASSED` và `FRESH`.
   - Điểm số hiệu năng của Agent (Hit Rate, Token F1, Judge Score) khôi phục hoàn toàn về mức Baseline.

---

## 8. Phân tích kết quả

### Bảng chỉ số đối chiếu 3 trạng thái

| Metric / Signal | Baseline (Sạch) | Corrupted (Lỗi) | Repaired (Phục hồi) | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.00%** | **0.00%** | **100.00%** | Việc drop bài mới và tiêm noise đã làm sụp đổ hoàn toàn khả năng trích xuất; sau repair lấy lại 100% |
| `mean_token_f1` | **0.4125** | **0.0000** | **0.4125** | Câu trả lời không còn chứa thông tin ground truth khi dữ liệu bị lỗi; lấy lại độ chính xác sau repair |
| `mean_judge_score` | **2.60 / 5.0** | **1.00 / 5.0** | **2.60 / 5.0** | Điểm số đánh giá chất lượng phản ánh trung thực hiện tượng Silent Failure và sự hồi sinh sau repair |
| `GX Quality status` | **PASSED** | **FAILED** | **PASSED** | Phát hiện chuẩn xác vi phạm trùng lặp và thiếu tóm tắt |
| `Freshness SLA` | **FRESH** | **STALE** | **FRESH** | Phát hiện chuẩn xác các bài báo bị lùi ngày về 5 năm trước |

### Hai chuỗi quan hệ nhân quả:
1. `[Drop 2 bài báo mới nhất & làm rỗng tóm tắt]` → `[GX báo FAILED & Vector search trích xuất sai]` → `[Hit Rate tụt từ 100% về 0% và Token F1 tụt về 0.0000]`.
2. `[Re-fetch và nạp lại từ raw records]` → `[GX báo PASSED & Vector index tái lập chuẩn]` → `[Hit Rate và Token F1 phục hồi 100% về mức Baseline ban đầu]`.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. **Về Data Ingestion & Lineage:** Luôn lưu trữ nguyên vẹn dữ liệu thô (Raw Preservation) ngay tại điểm tiếp nhận đầu tiên. Đây là "bảo hiểm dữ liệu" quan trọng nhất của mọi hệ thống.
2. **Về Vector Search:** Vector search rất nhạy cảm với nhiễu văn bản và thiếu sót thông tin. Một sự sai lệch nhỏ trong tóm tắt có thể làm vector nhảy sang cụm ngữ nghĩa hoàn toàn khác.
3. **Về Idempotent Design:** Thiết kế quy trình biến đổi dữ liệu có tính chất Idempotent giúp hệ thống có khả năng tự phục hồi (Self-Healing) cực kỳ mạnh mẽ trước mọi sự cố.

### Nếu có thêm thời gian:
Tôi sẽ bổ sung thêm các kịch bản tiêm lỗi nâng cao hơn như Semantic Drift (thay đổi ý nghĩa câu bằng các từ đồng nghĩa giả định) và đa dạng hóa mô hình nhúng (thử nghiệm thêm BGE-small hoặc OpenAI text-embedding-3-small) để so sánh độ bền vững của từng mô hình trước dữ liệu nhiễu.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và sự hiểu biết thực tế của tôi.
- [x] Tôi nắm rõ toàn bộ quy trình end-to-end từ Ingestion, Cleaning, Indexing đến Corruption và Repair.
- [x] Mọi số liệu trong báo cáo đều có bằng chứng từ các file kết quả thực tế trong repo.
- [x] Báo cáo tuyệt đối không chứa thông tin nhạy cảm hay API Key bí mật.

**Họ và tên:** Nguyễn Văn Ước  
**Ngày xác nhận:** 2026-09-25
