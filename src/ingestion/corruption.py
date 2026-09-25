from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_json


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path | str | None = None,
) -> pd.DataFrame:
    """Simulate 6 realistic synthetic data corruption scenarios on a clean DataFrame.

    Scenarios:
    1. Drop latest records: Drop 20% freshest papers (simulates ingestion lag / loss).
    2. Blank summary: Set summary to empty on selected rows (simulates scrape/field missing).
    3. Inject text noise: Prepend meaningless garbage noise to summary/text.
    4. Truncate title: Truncate title to < 10 characters (simulates schema/buffer cutoff).
    5. Stale date: Change published date to 5 years ago (simulates stale/decayed data).
    6. Duplicate rows: Duplicate rows to create duplicate paper_id records.

    Writes detailed corruption action log to output_log_path.
    """
    if df.empty:
        return df.copy()

    # Work on a copy
    corrupted = df.copy().reset_index(drop=True)
    initial_count = len(corrupted)
    actions_log: list[dict[str, Any]] = []

    # 1. Drop latest records (bỏ 2 bài báo mới nhất để mô phỏng mất dữ liệu tươi)
    drop_count = 2 if initial_count >= 10 else 1
    dropped_records = corrupted.iloc[:drop_count]
    dropped_ids = [str(pid) for pid in dropped_records["paper_id"].tolist()]
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)

    actions_log.append(
        {
            "scenario": "drop_latest_records",
            "description": f"Bỏ rơi {drop_count} bài báo mới nhất (mô phỏng mất dữ liệu tươi)",
            "count": drop_count,
            "affected_paper_ids": dropped_ids,
        }
    )

    # 2. Blank summary (clear summary on 2 records)
    blank_indices = [0, 1] if len(corrupted) >= 2 else [0]
    blanked_ids = []
    for idx in blank_indices:
        blanked_ids.append(str(corrupted.at[idx, "paper_id"]))
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0

    actions_log.append(
        {
            "scenario": "blank_summary",
            "description": f"Xóa trắng phần tóm tắt ở {len(blank_indices)} dòng (mô phỏng thiếu thông tin)",
            "count": len(blank_indices),
            "affected_paper_ids": blanked_ids,
        }
    )

    # 3. Inject text noise (inject garbage tokens into summary)
    noise_indices = [2, 3] if len(corrupted) >= 4 else []
    noise_ids = []
    noise_text = "### CORRUPTED_NOISE_ERROR_404_GARBAGE_DATA_STREAM_#%&*$@! ### "
    for idx in noise_indices:
        noise_ids.append(str(corrupted.at[idx, "paper_id"]))
        orig_summary = str(corrupted.at[idx, "summary"])
        corrupted.at[idx, "summary"] = noise_text + orig_summary
        corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])

    actions_log.append(
        {
            "scenario": "inject_text_noise",
            "description": f"Chèn các chuỗi ký tự rác vô nghĩa vào tóm tắt ở {len(noise_indices)} dòng",
            "count": len(noise_indices),
            "affected_paper_ids": noise_ids,
        }
    )

    # 4. Truncate title (truncate title to under 10 chars)
    trunc_indices = [4, 5] if len(corrupted) >= 6 else []
    trunc_ids = []
    for idx in trunc_indices:
        trunc_ids.append(str(corrupted.at[idx, "paper_id"]))
        orig_title = str(corrupted.at[idx, "title"])
        corrupted.at[idx, "title"] = orig_title[:8]  # < 10 characters

    actions_log.append(
        {
            "scenario": "truncate_title",
            "description": f"Cắt ngắn tiêu đề bài báo xuống dưới 10 ký tự ở {len(trunc_indices)} dòng",
            "count": len(trunc_indices),
            "affected_paper_ids": trunc_ids,
        }
    )

    # 5. Stale date (push published date back 5 years ago on 8 records)
    stale_count = min(8, len(corrupted))
    stale_indices = list(range(len(corrupted) - stale_count, len(corrupted)))
    stale_ids = []
    for idx in stale_indices:
        stale_ids.append(str(corrupted.at[idx, "paper_id"]))
        orig_date_str = str(corrupted.at[idx, "published"])
        try:
            orig_year = int(orig_date_str[:4])
            stale_year = orig_year - 5
            stale_pub = f"{stale_year}{orig_date_str[4:10]}"
        except Exception:
            stale_pub = "2021-01-01"
        corrupted.at[idx, "published"] = stale_pub
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + (5 * 365)

    actions_log.append(
        {
            "scenario": "stale_date",
            "description": f"Đổi ngày xuất bản về 5 năm trước ở {len(stale_indices)} dòng (mô phỏng dữ liệu bị mốc meo)",
            "count": len(stale_indices),
            "affected_paper_ids": stale_ids,
        }
    )

    # 6. Duplicate rows (duplicate 2 rows to inject duplicate records)
    dup_candidates = corrupted.iloc[:2].copy()
    dup_ids = [str(pid) for pid in dup_candidates["paper_id"].tolist()]
    corrupted = pd.concat([corrupted, dup_candidates], ignore_index=True)

    actions_log.append(
        {
            "scenario": "duplicate_rows",
            "description": f"Nhân đôi {len(dup_candidates)} dòng để tạo bản ghi trùng lặp",
            "count": len(dup_candidates),
            "affected_paper_ids": dup_ids,
        }
    )

    # 7. Rebuild text_for_embedding for all rows
    rebuilt_texts: list[str] = []
    for _, row in corrupted.iterrows():
        title = normalize_whitespace(str(row["title"]))
        authors = normalize_whitespace(str(row.get("authors_joined", "")))
        published = normalize_whitespace(str(row.get("published", "")))
        categories = normalize_whitespace(str(row.get("categories_joined", "")))
        summary = normalize_whitespace(str(row.get("summary", "")))

        text = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Published: {published}\n"
            f"Categories: {categories}\n"
            f"Summary: {summary}"
        )
        rebuilt_texts.append(text)

    corrupted["text_for_embedding"] = rebuilt_texts

    # 8. Write detailed corruption log
    log_payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "original_rows": initial_count,
        "corrupted_rows": len(corrupted),
        "actions": actions_log,
    }

    if output_log_path is not None:
        target_path = Path(output_log_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(target_path, log_payload)

    return corrupted

