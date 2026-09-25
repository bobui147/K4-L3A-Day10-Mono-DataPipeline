from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate a cleaned batch with GX 1.x and include the freshness SLA."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        *(gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
          for column in ("paper_id", "title", "summary", "text_for_embedding")),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="paper_id", min_value=1),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="text_for_embedding", min_value=30),
    ]
    results = []
    for expectation in expectations:
        validation = batch.validate(expectation).to_json_dict()
        results.append(
            {
                "expectation_type": validation["expectation_config"]["type"],
                "column": validation["expectation_config"]["kwargs"].get("column"),
                "success": bool(validation["success"]),
                "result": validation["result"],
            }
        )

    freshness = _freshness_summary(df, settings)
    gx_success = all(result["success"] for result in results)
    report = {
        "report_name": report_name,
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "row_count": len(df),
        "freshness": freshness,
        "expectations": results,
    }
    path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
    write_json(path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Write the publication-date and age-based freshness report."""
    report = _freshness_summary(df, settings)
    write_json(Path(report_path), report)
    return report


def _freshness_summary(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = len(df)
    ages = pd.to_numeric(df.get("age_days", pd.Series(index=df.index, dtype=float)), errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    missing_age_rows = int(ages.isna().sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0

    dates = pd.to_datetime(df.get("published", pd.Series(index=df.index, dtype=str)), errors="coerce", utc=True)
    valid_dates = dates.dropna()
    report = {
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "missing_age_rows": missing_age_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(total_rows and missing_age_rows == 0 and stale_ratio <= 0.25),
    }
    return report
