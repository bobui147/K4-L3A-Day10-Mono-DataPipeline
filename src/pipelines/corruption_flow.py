from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings
from core.utils import ensure_parent, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    ensure_parent(json_path)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def _same_paper_content(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    columns = [
        "paper_id", "title", "summary", "authors_joined", "categories_joined",
        "published", "text_for_embedding",
    ]
    if len(left) != len(right):
        return False
    left_rows = left[columns].sort_values("paper_id").to_dict(orient="records")
    right_rows = right[columns].sort_values("paper_id").to_dict(orient="records")
    return left_rows == right_rows


def main() -> None:
    """Measure a controlled failure, then rebuild and verify from raw records."""
    settings = load_settings()
    paths = settings.paths
    prerequisites = (
        paths.clean_json,
        paths.raw_records_json,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_quality_report,
        paths.freshness_report,
    )
    missing = [str(path) for path in prerequisites if not path.is_file()]
    if missing:
        raise RuntimeError("Run script/run_phase1.py first; missing: " + ", ".join(missing))

    baseline_df = pd.read_json(paths.clean_json)
    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_quality = read_json(paths.baseline_quality_report)
    baseline_freshness = read_json(paths.freshness_report)
    if not baseline_quality["success"]:
        raise RuntimeError("Baseline quality report failed; rerun phase 1 before corruption")

    print("[1/5] Injecting six data defects")
    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    _save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corruption_log = read_json(paths.corruption_log)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        paths.quality_dir / "corrupted_freshness_report.json",
    )
    if corrupted_quality["success"]:
        raise RuntimeError("Corruption was not detected by the quality gate")

    print("[2/5] Evaluating the isolated corrupted index")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, paths.corrupted_embeddings_json
    )
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        paths.eval_testset,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )

    print("[3/5] Repairing from preserved raw records")
    repaired_df = build_clean_dataframe(
        load_raw_records(paths.raw_records_json), datetime.now(UTC)
    )
    repair_matches_baseline = _same_paper_content(baseline_df, repaired_df)
    if not repair_matches_baseline:
        raise RuntimeError("Raw records do not reproduce baseline paper content; rerun phase 1")
    _save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        paths.quality_dir / "repaired_freshness_report.json",
    )
    if not repaired_quality["success"]:
        raise RuntimeError("Repaired data still fails the quality gate")

    print("[4/5] Evaluating the isolated repaired index")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, paths.repaired_embeddings_json
    )
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        paths.eval_testset,
        paths.repaired_metrics,
        paths.repaired_answers,
    )

    print("[5/5] Writing the three-state comparison")
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
        corruption_log=corruption_log,
        repair_matches_baseline=repair_matches_baseline,
    )
    print("State       Hit Rate  Token F1  Quality  Freshness")
    for label, metrics, quality, freshness in (
        ("Baseline", baseline_metrics, baseline_quality, baseline_freshness),
        ("Corrupted", corrupted_evaluation.summary, corrupted_quality, corrupted_freshness),
        ("Repaired", repaired_evaluation.summary, repaired_quality, repaired_freshness),
    ):
        print(
            f"{label:<10}  {metrics['retrieval_hit_rate']:.3f}     "
            f"{metrics['mean_token_f1']:.3f}     "
            f"{'PASS' if quality['success'] else 'FAIL':<7}  "
            f"{'PASS' if freshness['is_fresh'] else 'FAIL'}"
        )
    print(f"Report: {paths.comparison_report}")
