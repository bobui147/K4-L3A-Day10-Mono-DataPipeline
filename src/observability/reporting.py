from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a readable record of the baseline run and its quality checks."""
    def score(name: str) -> str:
        value = metrics.get(name)
        return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"

    fallback_count = int(metrics.get("judge_fallback_count", 0))
    lines = [
        "# Baseline Pipeline Report",
        "",
        "## Data source",
        "",
        f"- Source: {source_summary['source']}",
        f"- Live refresh requested: {source_summary['refresh_requested']}",
        f"- Raw records: {source_summary['raw_records']}",
        f"- Clean records: {source_summary['clean_records']}",
        f"- Query: {source_summary['query']}",
        "",
        "## Evaluation",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Questions | {metrics.get('samples', 0)} |",
        f"| Retrieval Hit Rate | {score('retrieval_hit_rate')} |",
        f"| Mean Token F1 | {score('mean_token_f1')} |",
        f"| Judge Accuracy | {score('judge_accuracy')} |",
        f"| Mean Judge Score (1-5) | {score('mean_judge_score')} |",
        f"| Judge heuristic fallbacks | {fallback_count} |",
        "",
        "## Data quality",
        "",
        f"- Quality gate: {'PASS' if quality['success'] else 'FAIL'}",
        f"- GX checks: {'PASS' if quality['gx_success'] else 'FAIL'}",
        f"- Freshness SLA: {'PASS' if freshness['is_fresh'] else 'FAIL'}",
        "",
        "| GX expectation | Column | Result |",
        "| --- | --- | --- |",
    ]
    for item in quality.get("expectations", []):
        lines.append(
            f"| {item['expectation_type']} | {item['column'] or '-'} | "
            f"{'PASS' if item['success'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Freshness",
            "",
            f"- Latest publication: {freshness['latest_published']}",
            f"- Oldest publication: {freshness['oldest_published']}",
            f"- Stale records: {freshness['stale_rows']}/{freshness['total_rows']}",
            f"- Stale ratio: {freshness['stale_ratio']:.1%}",
            f"- Threshold: older than {freshness['threshold_days']} days; alert above 25% stale",
            "",
        ]
    )
    ragas = metrics.get("ragas", {})
    if isinstance(ragas, dict) and ragas.get("skipped"):
        lines.extend(["## Ragas", "", f"- {ragas['skipped']}", ""])
    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    *,
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
    repair_matches_baseline: bool | None = None,
) -> None:
    """Write the measured comparison of clean, corrupted, and repaired states."""
    baseline_quality = baseline_quality or {}
    baseline_freshness = baseline_freshness or {}

    def number(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"

    def status(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        return "PASS" if value is True else "FAIL" if value is False else "n/a"

    def fraction(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        return f"{value:.1%}" if isinstance(value, (int, float)) else "n/a"

    rows = [
        ("Questions", "samples", str),
        ("Retrieval Hit Rate@4", "retrieval_hit_rate", number),
        ("Mean Token F1", "mean_token_f1", number),
        ("Judge Accuracy", "judge_accuracy", number),
        ("Mean Judge Score (1-5)", "mean_judge_score", number),
        ("Judge heuristic fallbacks", "judge_fallback_count", str),
    ]
    lines = [
        "# Corruption and Repair Report",
        "",
        "## Three-state comparison",
        "",
        "| Metric | Clean baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, key, formatter in rows:
        if formatter is number:
            values = [number(payload, key) for payload in
                      (baseline_metrics, corrupted_metrics, repaired_metrics)]
        else:
            values = [str(payload.get(key, "n/a")) for payload in
                      (baseline_metrics, corrupted_metrics, repaired_metrics)]
        lines.append(f"| {label} | {' | '.join(values)} |")

    lines.extend(
        [
            f"| Quality gate | {status(baseline_quality, 'success')} | "
            f"{status(corrupted_quality, 'success')} | {status(repaired_quality, 'success')} |",
            f"| Freshness SLA | {status(baseline_freshness, 'is_fresh')} | "
            f"{status(corrupted_freshness, 'is_fresh')} | {status(repaired_freshness, 'is_fresh')} |",
            f"| Stale ratio | {fraction(baseline_freshness, 'stale_ratio')} | "
            f"{fraction(corrupted_freshness, 'stale_ratio')} | "
            f"{fraction(repaired_freshness, 'stale_ratio')} |",
            "",
            "## Controlled corruption",
            "",
            "| Defect | Affected records |",
            "| --- | ---: |",
        ]
    )
    for operation in (corruption_log or {}).get("operations", []):
        lines.append(f"| {operation['type']} | {operation['count']} |")

    failed_checks = [
        f"{item['expectation_type']} ({item['column'] or 'table'})"
        for item in corrupted_quality.get("expectations", []) if not item["success"]
    ]
    retrieval_recovered = (
        repaired_metrics.get("retrieval_hit_rate") == baseline_metrics.get("retrieval_hit_rate")
    )
    f1_recovered = abs(
        repaired_metrics.get("mean_token_f1", 0) - baseline_metrics.get("mean_token_f1", 0)
    ) < 1e-9
    lines.extend(
        [
            "",
            "## Detection and recovery",
            "",
            f"- Corrupted GX failures: {', '.join(failed_checks) if failed_checks else 'none'}.",
            f"- Repaired paper content matches baseline: {repair_matches_baseline}.",
            f"- Retrieval Hit Rate restored: {retrieval_recovered}.",
            f"- Mean Token F1 restored: {f1_recovered}.",
            "- Repair source: preserved `data/raw/crossref_records.json`.",
            "",
        ]
    )
    write_text(Path(report_path), "\n".join(lines))
