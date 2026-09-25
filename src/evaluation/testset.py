from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


_QUESTION_TYPES = (
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
)


def _text(value: object) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a repeatable ten-question benchmark from distinct clean papers."""
    required = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")

    candidates: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for row in df.to_dict(orient="records"):
        paper_id = _text(row["paper_id"])
        title = _text(row["title"])
        summary = _text(row["summary"])
        authors = _text(row["authors_joined"])
        categories = _text(row["categories_joined"])
        published = pd.to_datetime(row["published"], errors="coerce", utc=True)
        if not (paper_id and title and summary and authors and categories) or pd.isna(published):
            continue
        if paper_id.casefold() in seen_ids:
            continue
        seen_ids.add(paper_id.casefold())
        candidates.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "published": published.date().isoformat(),
            }
        )

    if len(candidates) < len(_QUESTION_TYPES):
        raise ValueError("At least 10 distinct papers with complete metadata are required")

    candidates.sort(key=lambda paper: paper["paper_id"].casefold())
    candidates.sort(key=lambda paper: paper["published"], reverse=True)
    positions = [round(index * (len(candidates) - 1) / (len(_QUESTION_TYPES) - 1))
                 for index in range(len(_QUESTION_TYPES))]

    test_set: list[dict[str, Any]] = []
    for index, (position, question_type) in enumerate(zip(positions, _QUESTION_TYPES, strict=True), start=1):
        paper = candidates[position]
        title = paper["title"]
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(paper["summary"])
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = paper["authors"]
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = paper["published"]
        else:
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = paper["categories"]
        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper["paper_id"]],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
