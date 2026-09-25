from datetime import date, datetime
import re
from typing import Sequence

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: Sequence[PaperRecord], run_date: datetime | date) -> pd.DataFrame:
    """Clean raw paper records and prepare a normalized pandas DataFrame for vector indexing."""
    if isinstance(run_date, datetime):
        run_d = run_date.date()
    else:
        run_d = run_date

    cleaned_rows: list[dict] = []
    seen_paper_ids: set[str] = set()

    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        if not paper_id or paper_id in seen_paper_ids:
            continue

        title = normalize_whitespace(r.title)
        if not title:
            continue

        summary = normalize_whitespace(r.summary)
        authors = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        if not authors:
            authors = ["Unknown Author"]
        authors_joined = compact_join(authors, ", ")

        categories = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        if not categories:
            categories = ["Artificial Intelligence"]
        categories_joined = compact_join(categories, ", ")
        primary_category = normalize_whitespace(r.primary_category) or categories[0]

        published = normalize_whitespace(r.published) or "2026-01-01"
        try:
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d").date()
        except Exception:
            pub_date = run_d

        age_days = max(0, (run_d - pub_date).days)
        updated = normalize_whitespace(r.updated) or published

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )
        seen_paper_ids.add(paper_id)

    df = pd.DataFrame(cleaned_rows)
    if not df.empty:
        df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
