# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** Group 16 (`T016`)
- **Mã Nhóm / Lớp:** K4 — DAY10
- **Tên Repository Nộp Bài:** K4A-DAY10-Group16-T016
- **Repository URL:** https://github.com/quanchu14104/K4A-DAY10-Group16-T016

---

## 1. Danh Sách Thành Viên (Nhóm 2 Thành Viên - Phân Chia 50/50)

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | **Chu Minh Quân** | 2A202602709 | quan.cm@example.com | **Trưởng nhóm / Architecture, Observability & Pipeline Integrator** (`core/config.py`, `observability/quality.py`, `phase1.py`, `reporting.py`) | [`report/2A202602709_ChuMinhQuan.md`](../report/2A202602709_ChuMinhQuan.md) |
| 2 | **Nguyễn Văn Ước** | 2A202602445 | uoc.nv@example.com | **Data Foundation, Vector Retrieval & Corruption Suite Specialist** (`crossref.py`, `cleaning.py`, `retrieval/index.py`, `corruption.py`, `corruption_flow.py`) | [`report/2A202602445_NguyenVanUoc.md`](../report/2A202602445_NguyenVanUoc.md) |

---

## 2. Báo Cáo Đóng Góp Chi Tiết Từng Cá Nhân

### Chu Minh Quân — 2A202602709
- **Vai trò:** Trưởng nhóm & Kiến trúc sư Pipeline / Observability.
- **Tỷ lệ đóng góp:** 50%
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình dự án đa tầng, quản lý môi trường ảo độc lập qua `.venv` và nạp biến môi trường đa LLM provider (`9router`, `customllm`, `gemini`, `openai`, `mock`) trong `src/core/config.py` và `src/core/utils.py`.
  - Thiết kế và triển khai trạm kiểm soát chất lượng **Data Observability Gate** theo chuẩn mới **Great Expectations 1.x** (ephemeral execution context) với 4 kỳ vọng thiết yếu và cơ chế giám sát **Freshness SLA** (> 180 ngày) trong `src/observability/quality.py`.
  - Tích hợp và điều phối toàn bộ luồng thực thi **Phase 1 Baseline Pipeline** (`src/pipelines/phase1.py` & `script/run_phase1.py`), kiểm soát tính toàn vẹn của dữ liệu và sinh đầy đủ 5 artifacts.
  - Xây dựng module tự động xuất báo cáo Markdown chuyên sâu trong `src/observability/reporting.py` (`data/reports/phase1_report.md` và `data/reports/corruption_report.md`).
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Data Observability Gate hiện đại với Great Expectations 1.x và Freshness SLA, hiểu sâu về nguyên lý ngăn chặn hiện tượng Silent Failure trong các ứng dụng RAG Agent trước khi nạp dữ liệu vào Vector Store.

---

### Nguyễn Văn Ước — 2A202602445
- **Vai trò:** Chuyên viên Data Ingestion, Vector Search & Synthetic Corruption Suite.
- **Tỷ lệ đóng góp:** 50%
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập metadata bài báo khoa học từ Crossref REST API có cơ chế Offline Fallback Dual-Mode và bảo toàn bản sao thô (Raw Preservation) trong `src/ingestion/crossref.py`.
  - Thiết kế quy trình tiền xử lý, khử trùng lặp theo `paper_id`, tính `age_days` và tạo trường tổng hợp 5 phần `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Khởi tạo và quản lý ChromaDB Persistent Client, lập chỉ mục vector cho 24 tài liệu sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` (`src/retrieval/index.py`, `retrieval/qa.py`).
  - Xây dựng bộ câu hỏi chuẩn Benchmark Test Set phủ đủ các nhóm nghiệp vụ (`src/evaluation/testset.py`, `src/evaluation/metrics.py`).
  - Cài đặt trọn vẹn 6 kịch bản làm bẩn dữ liệu trong `src/ingestion/corruption.py`, đo lường sự sụt giảm hiệu năng và thực thi cơ chế tự phục hồi **Idempotent Repair** trong `src/pipelines/corruption_flow.py`.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ nguyên lý Data Lineage và tính Idempotency trong Data Engineering; chứng minh được bằng thực nghiệm rằng dữ liệu bẩn làm sụp đổ hoàn toàn độ chính xác của AI Agent và chỉ có thể khắc phục triệt để bằng cơ chế khôi phục từ nguồn Raw đáng tin cậy.
