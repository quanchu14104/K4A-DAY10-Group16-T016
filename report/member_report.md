# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| **Họ và tên**     | `[Điền Họ và tên của bạn]`                                              |
| **MSSV**          | `[Điền MSSV của bạn]`                                                    |
| **Khóa/Lớp**      | K4 — L3 — DAY10                                                          |
| **Tên nhóm**      | Group 16 (`K4A-DAY10-Group16-T016`)                                      |
| **Vai trò chính** | Data Engineering, Observability & Benchmark Lead (Pha 2 & Pha 3)         |
| **Repository**    | `https://github.com/quanchu14104/K4A-DAY10-Group16-T016`                 |
| **Ngày hoàn thành** | 2026-09-25                                                             |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module / deliverable | File / hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Ingestion** | `src/ingestion/crossref.py`<br>`parse_crossref_payload`<br>`fetch_source_records` | JSON payload từ Crossref REST API hoặc local snapshot | `data/raw/crossref_records.json` (24 bài báo chuẩn hóa) | Hoàn thành |
| **Data Cleaning** | `src/ingestion/cleaning.py`<br>`build_clean_dataframe` | List `PaperRecord` từ raw JSON snapshot | `data/clean/papers_clean.csv`, `papers_clean.json` (24 dòng) | Hoàn thành |
| **Data Observability** | `src/observability/quality.py`<br>`run_data_quality_checks`<br>`build_freshness_report` | Cleaned `pd.DataFrame`, cấu hình `Settings` | `data/quality/test_quality_report.json`, `freshness_report.json` | Hoàn thành |
| **Benchmark Test Set** | `src/evaluation/testset.py`<br>`TestSet`, `build_test_set`<br>`load_or_create_test_set` | Cleaned `pd.DataFrame` | `data/eval/test_set.json` (5 câu hỏi chuẩn 5 dạng nghiệp vụ) | Hoàn thành |
| **Vector Indexing** | `src/retrieval/index.py`<br>`LocalEmbeddingIndex.build_from_clean`<br>`semantic_search` | Cleaned dataset, MiniLM embedding model | Collection `papers-baseline` trên ChromaDB & manifest JSON | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Khởi tạo & cô lập môi trường chuẩn** | Toàn bộ nhóm / Workspace | Khắc phục xung đột môi trường Python 3.14 (không tương thích với Great Expectations 1.x) bằng cách triển khai `uv` để quản lý độc lập CPython 3.12.14 và cài đặt 160 packages sạch vào `.venv`. |
| **Fix mã hóa Unicode trên Windows** | Toàn bộ pipeline console outputs | Cấu hình `PYTHONIOENCODING="utf-8"` khắc phục triệt để lỗi `UnicodeEncodeError: 'charmap'` khi xuất text tiếng Việt trên PowerShell. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Ingestion Dual-Mode** | `src/ingestion/crossref.py`<br>`data/raw/crossref_records.json` | Tải và parse sạch 24 bài báo khoa học từ Crossref | `fetch_source_records(s)` in ra: `Đã nạp 24 bài báo` |
| **Data Transformation** | `src/ingestion/cleaning.py`<br>`data/clean/papers_clean.csv` | Chuẩn hóa schema, tính `age_days`, ghép `text_for_embedding` | `build_clean_dataframe(...)` in ra: `Clean thành công 24 dòng` |
| **Data Quality Gate** | `src/observability/quality.py`<br>`data/quality/test_quality_report.json` | Đạt 100% 4 kỳ vọng GX 1.x và Freshness SLA | `run_data_quality_checks(...)` in ra: `Quality check status = True` |
| **Benchmark Test Set** | `src/evaluation/testset.py`<br>`data/eval/test_set.json` | 5 câu hỏi phủ đủ 5 dạng: summary, authors, date, category, multi_hop | `load_or_create_test_set(...)` in ra: `Test set gồm 5 câu hỏi` |
| **ChromaDB Indexing** | `src/retrieval/index.py`<br>`data/chroma/` | Nạp 24 vector vào ChromaDB collection `papers-baseline` | `idx.semantic_search('machine learning', top_k=2)` in ra: `Tìm thấy 2 tài liệu liên quan` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong các hệ thống RAG thực tế, dữ liệu bẩn (missing metadata, rác HTML/XML, bản ghi bị rỗng tóm tắt hoặc dữ liệu bị mốc) không làm sập ứng dụng với exception đỏ mà dẫn tới **Silent Failure** (AI trả lời tự tin nhưng sai sự thật / hallucination). Phần việc này giải quyết:
1. Thu thập dữ liệu an toàn có cơ chế bảo toàn dữ liệu gốc (Raw Preservation) và tự động cứu hộ khi mất mạng (Offline Fallback).
2. Chuẩn hóa ngữ cảnh và đo lường độ tươi (`age_days`) trước khi đưa vào embedding.
3. Thiết lập trạm kiểm soát chất lượng tự động chặn đứng dữ liệu hỏng bằng **Great Expectations 1.x**.
4. Xây dựng đề thi chuẩn (Benchmark Ground Truth) và chỉ mục tìm kiếm ngữ nghĩa trên ChromaDB.

### Cách triển khai
1. **Module `crossref.py`**:
   - Sử dụng Regex `re.sub(r"<[^>]+>", " ", abstract)` loại bỏ triệt để các thẻ JATS XML rác (`<jats:p>`, `</jats:p>`).
   - Parse ngày xuất bản từ `date-parts` thành chuỗi chuẩn ISO 8601 (`YYYY-MM-DD`).
   - Xây dựng cơ chế Dual-Mode: kiểm tra cờ `settings.refresh_source`, nếu có lỗi mạng hoặc mã `429 Too Many Requests` sẽ tự động đọc từ snapshot có sẵn `data/raw/crossref_response.json`.
2. **Module `cleaning.py`**:
   - Tính toán `age_days = (run_d - pub_date).days` hỗ trợ cả datetime có/không có timezone.
   - Ghép cấu trúc 5 thành phần `text_for_embedding`:
     ```text
     Title: <title>
     Authors: <authors_joined>
     Published: <published>
     Categories: <categories_joined>
     Summary: <summary>
     ```
   - Khử trùng lặp bản ghi theo khóa duy nhất `paper_id`.
3. **Module `quality.py`**:
   - Khởi tạo Great Expectations 1.x ephemeral mode (`gx.get_context(mode="ephemeral")`) để chạy hoàn toàn trên RAM, không sinh file rác.
   - Định nghĩa Expectation Suite với 4 kỳ vọng: `ExpectTableRowCountToBeBetween(5, 5000)`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween(summary >= 30)`.
   - Giám sát Freshness SLA: Cảnh báo `is_fresh = False` khi tỉ lệ bản ghi có `age_days > 180` vượt ngưỡng 25%.
4. **Module `testset.py` & `index.py`**:
   - Thiết kế lớp `TestSet(list)` với thuộc tính `.samples` cho phép vừa tương thích truy cập list, vừa hỗ trợ API đối tượng.
   - Mở rộng `LocalEmbeddingIndex` với hàm `build_from_clean()` tự động đọc clean data, nhúng vector bằng mô hình `sentence-transformers/all-MiniLM-L6-v2` và lưu vào ChromaDB collection `papers-baseline`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Dữ liệu Crossref payload (`dict`) hoặc raw snapshot `data/raw/crossref_response.json`. |
| **Output** | Dataframe sạch (`data/clean/papers_clean.csv`), Quality report (`baseline_quality_report.json`), Test set (`test_set.json`), Chroma vector collection (`papers-baseline`). |
| **Module phụ thuộc** | `core.config.Settings`, `core.utils`. |
| **Module sử dụng output** | `retrieval.qa`, `pipelines.phase1`, `pipelines.corruption_flow`. |
| **Điều kiện lỗi xử lý** | Mất mạng Internet / API 429; ngày xuất bản thiếu tháng/ngày; dữ liệu trùng lặp `paper_id`; console Windows cp1252. |

### Cách xác minh
Chạy kịch bản tự động kiểm tra toàn diện cả 5 bước của Pha 2 và Pha 3:
```powershell
$env:PYTHONIOENCODING="utf-8"
python -c "
from datetime import datetime, timezone
import pandas as pd
from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from observability.quality import run_data_quality_checks
from evaluation.testset import load_or_create_test_set
from retrieval.index import LocalEmbeddingIndex

s = load_settings()
print('Signal 1:', f'Đã nạp {len(fetch_source_records(s))} bài báo')
df = build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc))
print('Signal 2:', f'Clean thành công {len(df)} dòng')
clean_df = pd.read_json(s.paths.clean_json)
print('Signal 3:', f'Quality check status = {run_data_quality_checks(clean_df, s, \"test\")[\"success\"]}')
ts = load_or_create_test_set(clean_df, s.paths.test_set_json)
print('Signal 4:', f'Test set gồm {len(ts.samples)} câu hỏi')
idx = LocalEmbeddingIndex(s, collection_name=\"papers-baseline\")
idx.build_from_clean()
print('Signal 5:', f'Tìm thấy {len(idx.semantic_search(\"machine learning\", top_k=2))} tài liệu liên quan')
"
```
* **Kết quả thực tế:**
  ```text
  Signal 1: Đã nạp 24 bài báo
  Signal 2: Clean thành công 24 dòng
  Signal 3: Quality check status = True
  Signal 4: Test set gồm 5 câu hỏi
  Signal 5: Tìm thấy 2 tài liệu liên quan
  ```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức khởi tạo và vận hành Great Expectations 1.x trong pipeline dữ liệu tự động.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Dùng cấu hình Filesystem truyền thống (`gx.get_context()`) sinh thư mục `gx/` trên ổ đĩa.
  2. *Phương án B:* Dùng cú pháp cũ GX 0.x (`context.sources.pandas_default`).
  3. *Phương án C:* Sử dụng Ephemeral Mode (`gx.get_context(mode="ephemeral")`) kết hợp Data Source Pandas động theo chuẩn GX 1.x.
- **Phương án đã chọn:** *Phương án C (Ephemeral Mode).*
- **Lý do:**
  - Cú pháp GX 0.x ở phương án B đã bị loại bỏ hoàn toàn trên phiên bản `great-expectations>=1.0.0`, nếu dùng sẽ gặp lỗi `AttributeError`.
  - Phương án A sinh ra nhiều file cấu hình `.yml` thừa thãi trên ổ cứng, dễ gây xung đột khi chạy lặp lại trong môi trường CI/CD.
  - Ephemeral Mode chạy 100% trên bộ nhớ RAM, thời gian khởi tạo chỉ mất vài mili-giây, hoàn toàn cô lập và dọn dẹp bộ nhớ ngay sau khi validation kết thúc.
- **Bằng chứng quyết định phù hợp:** Thời gian chạy toàn bộ 4 kỳ vọng trên 24 bản ghi chỉ mất chưa tới 0.3 giây, xuất ra artifact JSON rõ ràng và không để lại file rác trong workspace.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ERROR: Ignored the following versions that require a different python version: 1.0.0 Requires-Python >=3.8,<3.12...
  ERROR: No matching distribution found for great-expectations>=1.16.1
  ```
- **Lệnh tái hiện:**
  `python -m pip install -r requirements.txt` trên môi trường Python mặc định của máy.
- **Nguyên nhân gốc:**
  Hệ thống đang chạy Python 3.14.7. Thư viện `great-expectations` (và file `pyproject.toml`) đặt ràng buộc chặt chẽ `requires-python = ">=3.11,<3.14"`. Vì Python 3.14 chưa được các thư viện Machine Learning và Great Expectations hỗ trợ prebuilt wheels, `pip` tự động loại bỏ tất cả các phiên bản của thư viện này.
- **Cách xử lý:**
  1. Cài đặt công cụ quản lý Python tốc độ cao `uv`.
  2. Dùng `uv python install 3.12` để tải runtime CPython 3.12.14 chuẩn xác.
  3. Khởi tạo lại môi trường ảo: `uv venv .venv --python 3.12 --clear`.
  4. Đồng bộ 160 packages dự án từ lockfile bằng `uv sync --extra dev`.
- **Cách xác minh sau khi sửa:**
  Chạy lệnh `.venv\Scripts\python.exe -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"` cho kết quả `Môi trường sẵn sàng` (Exit code 0).
- **Điều học được:** Luôn đối chiếu yêu cầu phiên bản Python trong `pyproject.toml` trước khi dựng môi trường; sử dụng các công cụ quản lý môi trường hiện đại như `uv` giúp cô lập phiên bản Python mà không làm ảnh hưởng đến cấu hình máy chủ/máy trạm.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - API Crossref trả về payload JSON thô $\rightarrow$ được bảo toàn nguyên trạng tại `data/raw/crossref_response.json`.
   - `crossref.py` bóc tách thành danh sách `PaperRecord` và lưu tại `data/raw/crossref_records.json`.
   - `cleaning.py` loại bỏ ký tự rác, tính `age_days`, tạo trường ngữ cảnh `text_for_embedding` và khử trùng lặp $\rightarrow$ xuất ra `data/clean/papers_clean.csv`.
   - `quality.py` thực hiện chốt kiểm dịch GX 1.x. Khi đạt chuẩn `success=True`, dữ liệu được chuyển sang `LocalEmbeddingIndex` để sinh vector 384 chiều bằng `all-MiniLM-L6-v2` và nạp vào ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Mỗi mẫu trong `test_set.json` có câu hỏi (`question`), câu trả lời mẫu (`ground_truth`) và danh sách ID bài báo liên quan (`ground_truth_doc_ids`).
   - **Retrieval Hit Rate:** Kiểm tra xem trong top-$K$ bài báo được vector search trả về có chứa ít nhất một `paper_id` thuộc `ground_truth_doc_ids` hay không (đo lường độ chính xác của tầng tìm kiếm).
   - **Token F1 & Judge Score:** So sánh câu trả lời do mô hình sinh ra với `ground_truth` để đo độ chính xác ngữ nghĩa và hạn chế hiện tượng ảo giác (hallucination).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (Great Expectations):** Đo lường tính toàn vẹn về mặt cấu trúc và cú pháp (Schema & Syntax Integrity) như số dòng, trường không được null, khóa không trùng lặp, độ dài tối thiểu của tóm tắt.
   - **Freshness monitoring (Freshness SLA):** Đo lường tính hợp lệ về mặt thời gian (Temporal Validity). Dữ liệu có thể rất sạch và chuẩn cấu trúc, nhưng nếu đã quá cũ (`age_days > 180`), thông tin trong Vector Store sẽ trở nên lỗi thời, khiến RAG Agent tư vấn kiến thức cũ (Stale Knowledge).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính khách quan và khoa học theo nguyên tắc đối chứng (A/B testing). Nếu mỗi trạng thái dùng một bộ câu hỏi khác nhau, độ biến thiên của điểm số có thể do độ khó của câu hỏi chứ không phản ánh đúng tác động của chất lượng dữ liệu. Giữ cố định `test_set.json` giúp cô lập biến số duy nhất là: **chất lượng của Vector Index**.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Về Artifact:** Sinh ra `data/clean/papers_clean_repaired.csv` đồng nhất với bản clean ban đầu và `corruption_report.md` có đầy đủ bảng so sánh 3 cột: Baseline vs Corrupted vs Repaired.
   - **Về Metric:** `retrieval_hit_rate` và `mean_token_f1` ở trạng thái Repaired phải phục hồi tương đương hoặc bằng trạng thái Baseline, đồng thời Quality checks của GX 1.x chuyển từ `False` (bị chặn ở Corrupted) trở lại `True`.

---

## 8. Phân tích kết quả

### Metrics chính (Baseline Clean Data)

| Metric / Signal | Giá trị Baseline | Nhận xét của cá nhân |
| :--- | :---: | :--- |
| **Số lượng bài báo** | 24 | Đầy đủ bản ghi, không bị mất mát dữ liệu |
| **Quality checks (GX 1.x)** | `True` | 100% 4 kỳ vọng bắt buộc đều đạt |
| **Freshness SLA** | `True` (0% stale) | 100% bài báo đều mới trong vòng 65 - 130 ngày (< 180 ngày) |
| **Benchmark Test Set** | 5 câu hỏi | Phủ đủ 5 nghiệp vụ: summary, authors, date, category, multi_hop |
| **Retrieval Sample Search** | 2 tài liệu | Truy vấn semantic search với ChromaDB hoạt động chính xác |

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Bảo toàn dữ liệu gốc (Raw Data Preservation):** Luôn lưu trữ bản sao thô (Raw Snapshot) nguyên đai nguyên kiện từ API bên ngoài. Đây là nền tảng sống còn cho cơ chế phục hồi bất biến (Idempotent Repair) mà không phải cào lại dữ liệu khi xảy ra lỗi.
2. **Data Observability không chỉ là kiểm tra Schema:** Một Data Pipeline cho AI cần cả hai chốt chặn: Kiểm tra tính nguyên vẹn của dữ liệu (Data Quality Gate qua Great Expectations) và Giám sát tính tươi mới (Freshness SLA).
3. **Hiểm họa Silent Failure trong RAG:** Dữ liệu lỗi không làm ứng dụng báo lỗi Exception mà làm suy giảm chất lượng câu trả lời của LLM. Do đó, việc tự động hóa kiểm dịch dữ liệu trước khi nạp vào Vector Store là bắt buộc.

### Nếu có thêm thời gian
- Xây dựng thêm bộ lọc tự động phát hiện ngôn ngữ (Language Detection) và tự động chuẩn hóa các ký tự đặc biệt theo bảng mã Unicode chuẩn (NFC) nhằm nâng cao hơn nữa chất lượng embedding cho các tài liệu đa ngôn ngữ.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Người báo cáo:** `[Điền Họ và tên của bạn]`  
**Ngày xác nhận:** 2026-09-25
