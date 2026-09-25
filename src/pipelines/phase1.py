from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from core.utils import ensure_parent, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run raw ingestion, quality gate, indexing, evaluation, and reporting."""
    settings = load_settings()
    paths = settings.paths

    print("[1/6] Loading Crossref records")
    records = fetch_source_records(settings)
    df = build_clean_dataframe(records, datetime.now(UTC))
    write_csv(df, paths.clean_csv)
    ensure_parent(paths.clean_json)
    df.to_json(paths.clean_json, orient="records", indent=2, force_ascii=False)

    print("[2/6] Validating data quality and freshness")
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError(
            f"Baseline quality gate failed; see {paths.baseline_quality_report}"
        )

    print("[3/6] Preparing the benchmark set")
    if paths.eval_testset.is_file() and not settings.refresh_test_set:
        test_set = read_json(paths.eval_testset)
        available_ids = set(df["paper_id"])
        valid = (
            isinstance(test_set, list)
            and len(test_set) == 10
            and all(
                isinstance(item, dict)
                and set(item.get("ground_truth_doc_ids", [])) <= available_ids
                for item in test_set
            )
        )
        if not valid:
            build_test_set(df, paths.eval_testset)
    else:
        build_test_set(df, paths.eval_testset)

    print("[4/6] Building the Chroma index")
    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)

    print("[5/6] Evaluating retrieval and answers")
    evaluation = evaluate_pipeline(
        settings,
        index,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_answers,
    )

    print("[6/6] Writing the baseline report")
    source_summary = {
        "source": (
            f"{settings.source_api} (snapshot fallback possible)"
            if settings.refresh_source else "Preserved Crossref snapshot"
        ),
        "refresh_requested": settings.refresh_source,
        "raw_records": len(records),
        "clean_records": len(df),
        "query": settings.source_query,
    }
    generate_phase1_report(
        paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )
    print(f"Baseline complete: {len(df)} papers, {evaluation.summary['samples']} questions")
    print(f"Hit Rate: {evaluation.summary['retrieval_hit_rate']:.3f}")
    print(f"Token F1: {evaluation.summary['mean_token_f1']:.3f}")
    print(f"Report: {paths.baseline_report}")
