from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]


def _clean_text(value: object) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.date()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into a deterministic table ready for indexing."""
    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for record in records:
        paper_id = _clean_text(record.paper_id)
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published_date = _parse_date(record.published)
        if not (paper_id and title and summary and published_date):
            continue
        unique_id = paper_id.casefold()
        if unique_id in seen_ids:
            continue
        seen_ids.add(unique_id)

        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published = published_date.isoformat()
        updated_date = _parse_date(record.updated) or published_date
        abs_url = _clean_text(record.abs_url)
        pdf_url = _clean_text(record.pdf_url) or abs_url
        text_for_embedding = "\n".join(
            (
                f"Title: {title}",
                f"Authors: {authors_joined}",
                f"Published: {published}",
                f"Categories: {categories_joined}",
                f"Summary: {summary}",
            )
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": _clean_text(record.primary_category) or (categories[0] if categories else ""),
                "published": published,
                "updated": updated_date.isoformat(),
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": _clean_text(record.comment),
                "age_days": (run_date.date() - published_date).days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    dataframe = pd.DataFrame(rows, columns=_COLUMNS)
    return dataframe.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
