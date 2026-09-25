from __future__ import annotations

from datetime import date, timedelta
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


_REQUIRED_COLUMNS = {
    "paper_id", "title", "summary", "authors_joined", "categories_joined",
    "published", "age_days", "summary_chars", "text_for_embedding",
}


def _positions(length: int, fractions: tuple[float, ...]) -> list[int]:
    """Select stable, spread-out row positions after sorting the input."""
    return sorted({round(fraction * (length - 1)) for fraction in fractions})


def _embedding_text(row: pd.Series) -> str:
    return "\n".join(
        (
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        )
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six reproducible defects into a copy of a clean dataframe."""
    missing = _REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")
    if len(df) < 10:
        raise ValueError("At least 10 clean records are required for the corruption suite")

    ordered = df.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True).copy(deep=True)
    drop_count = ceil(len(ordered) * 0.20)
    dropped_ids = ordered.iloc[:drop_count]["paper_id"].tolist()
    corrupted = ordered.iloc[drop_count:].reset_index(drop=True).copy(deep=True)
    operations: list[dict] = [
        {
            "type": "drop_latest_records",
            "count": drop_count,
            "paper_ids": dropped_ids,
            "fraction_of_baseline": drop_count / len(ordered),
        }
    ]

    blank_changes = []
    for position in _positions(len(corrupted), (0.0, 0.28, 0.56)):
        blank_changes.append(
            {"paper_id": corrupted.at[position, "paper_id"],
             "original_summary_chars": len(str(corrupted.at[position, "summary"]))}
        )
        corrupted.at[position, "summary"] = ""
    operations.append({"type": "blank_summary", "count": len(blank_changes), "changes": blank_changes})

    noise = " [NOISE: @@@###!!!???]"
    noise_changes = []
    for position in _positions(len(corrupted), (0.17, 0.44, 0.72)):
        corrupted.at[position, "summary"] = str(corrupted.at[position, "summary"]) + noise
        noise_changes.append({"paper_id": corrupted.at[position, "paper_id"], "injected_text": noise.strip()})
    operations.append({"type": "inject_noise", "count": len(noise_changes), "changes": noise_changes})

    title_changes = []
    for position in _positions(len(corrupted), (0.17, 0.44, 0.72)):
        original = str(corrupted.at[position, "title"])
        shortened = original[:7]
        corrupted.at[position, "title"] = shortened
        title_changes.append(
            {"paper_id": corrupted.at[position, "paper_id"],
             "before": original, "after": shortened}
        )
    operations.append({"type": "truncate_title", "count": len(title_changes), "changes": title_changes})

    reference = corrupted.iloc[0]
    run_date = date.fromisoformat(str(reference["published"])[:10]) + timedelta(days=int(reference["age_days"]))
    stale_published = (run_date - timedelta(days=365)).isoformat()
    stale_changes = []
    for position in _positions(len(corrupted), (0.0, 0.28, 0.56, 0.72, 0.83, 1.0)):
        original = str(corrupted.at[position, "published"])
        corrupted.at[position, "published"] = stale_published
        corrupted.at[position, "age_days"] = 365
        stale_changes.append(
            {"paper_id": corrupted.at[position, "paper_id"],
             "before": original, "after": stale_published}
        )
    operations.append({"type": "stale_date", "count": len(stale_changes), "changes": stale_changes})

    duplicate_positions = _positions(len(corrupted), (0.11, 0.67))
    duplicates = corrupted.iloc[duplicate_positions].copy(deep=True)
    duplicated_ids = duplicates["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    operations.append(
        {"type": "duplicate_rows", "count": len(duplicated_ids), "paper_ids": duplicated_ids}
    )

    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)
    log = {
        "baseline_rows": len(df),
        "corrupted_rows": len(corrupted),
        "selection": "published descending, then paper_id ascending",
        "operations": operations,
    }
    write_json(Path(output_log_path), log)
    return corrupted
