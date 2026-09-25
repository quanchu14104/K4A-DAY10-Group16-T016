from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any
import urllib.request
import urllib.parse

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref API response payload into a list of PaperRecord objects."""
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else payload.get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            continue

        # Title
        title_raw = item.get("title", [])
        if isinstance(title_raw, list):
            title = title_raw[0] if title_raw else ""
        else:
            title = str(title_raw)
        title = normalize_whitespace(title)
        if not title:
            continue

        # Abstract / Summary (remove HTML/JATS XML tags)
        abstract_raw = item.get("abstract", "")
        clean_abstract = re.sub(r"<[^>]+>", " ", abstract_raw)
        summary = normalize_whitespace(clean_abstract)

        # Authors
        authors: list[str] = []
        author_items = item.get("author", [])
        if isinstance(author_items, list):
            for a in author_items:
                if isinstance(a, dict):
                    given = str(a.get("given", "")).strip()
                    family = str(a.get("family", "")).strip()
                    full_name = f"{given} {family}".strip()
                    if not full_name and "name" in a:
                        full_name = str(a["name"]).strip()
                    if full_name:
                        authors.append(full_name)
                elif isinstance(a, str) and a.strip():
                    authors.append(a.strip())
        if not authors:
            authors = ["Unknown Author"]

        # Subject / Categories
        subjects = item.get("subject", [])
        categories: list[str] = []
        if isinstance(subjects, list):
            categories = [normalize_whitespace(str(s)) for s in subjects if str(s).strip()]
        elif isinstance(subjects, str) and subjects.strip():
            categories = [normalize_whitespace(subjects)]
        if not categories:
            categories = ["Artificial Intelligence"]
        primary_category = categories[0]

        # Published date
        published = "2026-01-01"
        pub_dict = item.get("published") or item.get("issued") or item.get("created")
        if isinstance(pub_dict, dict):
            date_parts = pub_dict.get("date-parts", [[]])
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                parts = date_parts[0]
                year = parts[0]
                month = parts[1] if len(parts) >= 2 else 1
                day = parts[2] if len(parts) >= 3 else 1
                published = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            elif "date-time" in pub_dict:
                published = str(pub_dict["date-time"])[:10]

        # Updated date
        updated = published
        created_dict = item.get("created")
        if isinstance(created_dict, dict) and "date-time" in created_dict:
            updated = str(created_dict["date-time"])[:10]

        url = item.get("URL") or f"https://doi.org/{doi}"
        comment = f"Crossref record {doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API or fallback to local snapshot (Dual-Mode)."""
    payload: dict[str, Any] | None = None

    if settings.refresh_source:
        try:
            params = urllib.parse.urlencode(
                {
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                }
            )
            req = urllib.request.Request(
                f"https://api.crossref.org/works?{params}",
                headers={"User-Agent": "Day10Lab/1.0 (mailto:lab@university.edu)"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload:
                write_json(settings.paths.raw_api_response, payload)
        except Exception as exc:
            logger.warning("Could not fetch from live Crossref API (%s). Falling back to snapshot.", exc)

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise FileNotFoundError(f"Raw API snapshot not found at {settings.paths.raw_api_response}")

    records = parse_crossref_payload(payload)

    # Save parsed records to raw_records_json
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load raw records from JSON snapshot and map into PaperRecord instances."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
