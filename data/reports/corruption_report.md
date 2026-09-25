# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

**Thời gian tạo:** `2026-09-25 09:01:56 UTC`  
**Mục tiêu:** Đo lường sự suy giảm chất lượng khi dữ liệu bị lỗi và chứng minh tính năng tự phục hồi (Idempotent Repair).

---

## 1. Bảng So Sánh Hiệu Năng 3 Trạng Thái (Performance Comparison)

| Chỉ số đánh giá | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu bẩn) | Repaired (Sau phục hồi) | Nhận xét tác động |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **0.00%** | **100.00%** | Suy giảm nghiêm trọng khi bị tiêm lỗi; phục hồi hoàn toàn sau repair. |
| **Mean Token F1** | **0.4125** | **0.0000** | **0.4125** | Dữ liệu bẩn làm sụt giảm độ chính xác câu trả lời. |
| **LLM Judge Score** | **2.60 / 5.0** | **1.00 / 5.0** | **2.60 / 5.0** | AI lấy lại phong độ tối đa sau khi nguồn dữ liệu được làm sạch lại. |

---

## 2. Kiểm Soát Chất Lượng Dữ Liệu (Data Observability Comparison)

| Trạng thái | GX 1.x Validation | Freshness SLA | Số dòng | Tỉ lệ lỗi / quá hạn |
| :--- | :---: | :---: | :---: | :--- |
| **Corrupted Data** | FAILED | STALE | 21 | Stale: 38.10% |
| **Repaired Data** | PASSED | FRESH | 24 | Stale: 4.17% |

---

## 3. Kết Luận & Đánh Giá
- Khi dữ liệu bị tiêm lỗi (Data Corruption: rỗng summary, sai lệch ngày, trùng lặp, cắt ngắn tiêu đề), hệ thống trích xuất vector và LLM Agent bị ảnh hưởng rõ rệt (Silent Failure).
- Cơ chế Idempotent Repair bằng cách nạp lại từ bản sao lưu thô (Raw Preservation) đã giúp hệ thống khôi phục hoàn toàn chỉ số về mức ban đầu.
