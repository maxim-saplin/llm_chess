from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .serialization import json_safe

EXCLUDED_SUMMARY_FILES = {"cross_ref_summary.json", "audit_summary.json"}


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _report_path(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _top_non_elo_metric(rows: list[object]) -> dict[str, object] | None:
    candidates: list[tuple[float, float, dict[str, object]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("name") == "elo":
            continue
        pearson_r = _float_or_none(row.get("pearson_r"))
        sample_n = _float_or_none(row.get("n")) or 0.0
        if pearson_r is None:
            continue
        candidates.append((abs(pearson_r), sample_n, row))
    if not candidates:
        return None
    return dict(max(candidates, key=lambda item: (item[0], item[1]))[2])


def _coverage_snapshot(summary: dict[str, object]) -> dict[str, object]:
    coverage = _as_dict(summary.get("coverage"))
    analysis_surfaces = _as_dict(summary.get("analysis_surfaces"))
    mapping = _as_dict(summary.get("mapping"))
    status_counts = _as_dict(mapping.get("mapping_file_status_counts"))
    metric_analysis = _as_dict(analysis_surfaces.get("metric_analysis"))
    elo_analysis = _as_dict(analysis_surfaces.get("elo_analysis"))
    return {
        "numeric_score_rows": coverage.get("numeric_score_rows"),
        "accepted_mapping_rows": coverage.get("accepted_mapping_rows"),
        "rows_joined_to_llm_chess_metric_rows": coverage.get("rows_joined_to_llm_chess_metric_rows"),
        "metric_analysis_rows_max_dedupe": coverage.get(
            "metric_analysis_rows_max_dedupe",
            metric_analysis.get("count"),
        ),
        "rows_joined_to_llm_chess_elo": coverage.get(
            "rows_joined_to_llm_chess_elo",
            coverage.get("rows_joined_to_llm_chess_rows_with_non_null_elo"),
        ),
        "elo_analysis_rows_max_dedupe": coverage.get(
            "elo_analysis_rows_max_dedupe",
            elo_analysis.get("count"),
        ),
        "external_rows_without_llm_chess_match": coverage.get(
            "external_rows_without_llm_chess_match",
            status_counts.get("unmatched"),
        ),
    }


def _mapping_snapshot(summary: dict[str, object]) -> dict[str, object]:
    mapping = _as_dict(summary.get("mapping"))
    unresolved_rows = [
        row
        for row in _as_list(mapping.get("unresolved_high_impact_rows"))
        if isinstance(row, dict)
    ]
    return {
        "qa_verdict": mapping.get("qa_verdict"),
        "status_counts": _as_dict(mapping.get("mapping_file_status_counts")),
        "review_status_counts": _as_dict(mapping.get("mapping_review_status_counts")),
        "unresolved_high_impact_count": len(unresolved_rows),
        "unresolved_high_impact_examples": unresolved_rows[:5],
    }


def _relationship_snapshot(summary: dict[str, object]) -> dict[str, object]:
    relationships = _as_dict(summary.get("relationships"))
    raw_elo = _as_dict(relationships.get("raw_elo"))
    release_controlled = _as_dict(relationships.get("release_controlled_elo"))
    strongest_metric = _top_non_elo_metric(_as_list(relationships.get("selected_metrics")))
    return {
        "raw_elo": {
            "n": raw_elo.get("n"),
            "pearson_r": raw_elo.get("pearson_r"),
            "spearman_r": raw_elo.get("spearman_r"),
            "r2": raw_elo.get("r2"),
            "sample_stage_id": raw_elo.get("sample_stage_id"),
        },
        "release_controlled_elo": {
            "n": release_controlled.get("n"),
            "pearson_r": release_controlled.get("pearson_r"),
            "spearman_r": release_controlled.get("spearman_r"),
            "sample_stage_id": release_controlled.get("sample_stage_id"),
        },
        "strongest_non_elo_metric": strongest_metric,
    }


def _prediction_snapshot(summary: dict[str, object]) -> dict[str, object]:
    prediction = _as_dict(summary.get("prediction"))
    baseline = _as_dict(prediction.get("baseline_mean"))
    ols = _as_dict(prediction.get("ols"))
    return {
        "target": prediction.get("target"),
        "status": prediction.get("status"),
        "sample_stage_id": prediction.get("sample_stage_id"),
        "sample_n": prediction.get("sample_n"),
        "features": list(prediction.get("features", [])) if isinstance(prediction.get("features"), list) else [],
        "baseline_mean": {
            "r2": baseline.get("r2"),
            "rmse": baseline.get("rmse"),
            "mae": baseline.get("mae"),
            "rank_spearman": baseline.get("rank_spearman"),
        },
        "ols": {
            "r2": ols.get("r2"),
            "rmse": ols.get("rmse"),
            "mae": ols.get("mae"),
            "rank_spearman": ols.get("rank_spearman"),
        },
        "feature_selection": _as_dict(ols.get("feature_selection")),
        "selected_feature_counts": _as_dict(ols.get("selected_feature_counts")),
    }


def _source_entry(
    summary: dict[str, object],
    summary_path: Path,
    repo_root: Path,
) -> dict[str, object]:
    verification = _as_dict(summary.get("verification"))
    artifact_paths = _as_dict(verification.get("artifact_paths"))
    return {
        "eval_id": summary.get("eval_id"),
        "eval_label": summary.get("eval_label"),
        "summary_path": _report_path(summary_path, repo_root),
        "summary_sha256": _sha256(summary_path),
        "report_path": artifact_paths.get("html"),
        "coverage_path": artifact_paths.get("coverage_csv"),
    }


def _eval_entry(
    summary: dict[str, object],
    source_entry: dict[str, object],
) -> dict[str, object]:
    inputs = _as_dict(summary.get("inputs"))
    return {
        "eval_id": summary.get("eval_id"),
        "eval_label": summary.get("eval_label"),
        "summary_tagline": summary.get("summary_tagline"),
        "target_score_column": summary.get("target_score_column"),
        "source_summary_path": source_entry["summary_path"],
        "source_summary_sha256": source_entry["summary_sha256"],
        "published_artifacts": {
            "summary_json": source_entry["summary_path"],
            "html": source_entry.get("report_path"),
            "coverage_csv": source_entry.get("coverage_path"),
        },
        "source_note_path": inputs.get("source_note_path"),
        "coverage": _coverage_snapshot(summary),
        "mapping": _mapping_snapshot(summary),
        "relationships": _relationship_snapshot(summary),
        "prediction": _prediction_snapshot(summary),
        "limitations": [item for item in _as_list(summary.get("limitations")) if isinstance(item, str)],
    }


def _comparison_record(
    eval_summary: dict[str, object],
    value: object,
    field_name: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "eval_id": eval_summary.get("eval_id"),
        "eval_label": eval_summary.get("eval_label"),
        field_name: value,
    }
    if extra:
        payload.update(extra)
    return payload


def _best_eval(
    evals: list[dict[str, object]],
    score_fn,
) -> dict[str, object] | None:
    candidates: list[tuple[float, dict[str, object]]] = []
    for eval_summary in evals:
        score = _float_or_none(score_fn(eval_summary))
        if score is None:
            continue
        candidates.append((score, eval_summary))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def build_cross_eval_summary(
    results_dir: Path,
    summary_output: Path,
    report_output: Path,
    repo_root: Path,
) -> dict[str, object]:
    summary_paths = sorted(
        path
        for path in results_dir.glob("*_summary.json")
        if path.is_file() and path.name not in EXCLUDED_SUMMARY_FILES
    )
    if not summary_paths:
        raise ValueError(f"no published per-eval summaries found in {results_dir}")

    source_entries = []
    eval_summaries = []
    for summary_path in summary_paths:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(summary, dict) or not summary.get("eval_id"):
            continue
        source_entry = _source_entry(summary, summary_path, repo_root)
        source_entries.append(source_entry)
        eval_summaries.append(_eval_entry(summary, source_entry))

    if not source_entries:
        raise ValueError(f"no published per-eval summaries found in {results_dir}")

    strongest_raw_elo = _best_eval(
        eval_summaries,
        lambda item: _as_dict(item.get("relationships")).get("raw_elo", {}).get("pearson_r"),
    )
    strongest_release_controlled = _best_eval(
        eval_summaries,
        lambda item: _as_dict(item.get("relationships")).get("release_controlled_elo", {}).get("pearson_r"),
    )
    best_prediction = _best_eval(
        eval_summaries,
        lambda item: _as_dict(item.get("prediction")).get("ols", {}).get("r2"),
    )
    largest_metric_sample = _best_eval(
        eval_summaries,
        lambda item: _as_dict(item.get("coverage")).get("metric_analysis_rows_max_dedupe"),
    )

    comparisons: dict[str, object] = {}
    if strongest_raw_elo:
        raw_elo = _as_dict(_as_dict(strongest_raw_elo.get("relationships")).get("raw_elo"))
        comparisons["strongest_raw_elo"] = _comparison_record(
            strongest_raw_elo,
            raw_elo.get("pearson_r"),
            "pearson_r",
            extra={"n": raw_elo.get("n"), "r2": raw_elo.get("r2")},
        )
    if strongest_release_controlled:
        release_controlled = _as_dict(
            _as_dict(strongest_release_controlled.get("relationships")).get("release_controlled_elo")
        )
        comparisons["strongest_release_controlled_elo"] = _comparison_record(
            strongest_release_controlled,
            release_controlled.get("pearson_r"),
            "pearson_r",
            extra={"n": release_controlled.get("n")},
        )
    if best_prediction:
        prediction = _as_dict(_as_dict(best_prediction.get("prediction")).get("ols"))
        comparisons["best_prediction"] = _comparison_record(
            best_prediction,
            prediction.get("r2"),
            "r2",
            extra={
                "sample_n": _as_dict(best_prediction.get("prediction")).get("sample_n"),
                "rank_spearman": prediction.get("rank_spearman"),
            },
        )
    if largest_metric_sample:
        coverage = _as_dict(largest_metric_sample.get("coverage"))
        comparisons["largest_metric_analysis_sample"] = _comparison_record(
            largest_metric_sample,
            coverage.get("metric_analysis_rows_max_dedupe"),
            "sample_n",
        )

    return json_safe(
        {
            "artifact_kind": "cross_eval_summary",
            "generated_from": {
                "mode": "published_per_eval_summaries",
                "reran_evals": False,
                "results_dir": _report_path(results_dir, repo_root),
                "summary_count": len(source_entries),
                "summaries": source_entries,
            },
            "report_contract": {
                "primary_human_report": "data/cross-ref/CONSOLIDATED_REPORT.md",
                "generated_support_report": _report_path(report_output, repo_root),
                "primary_machine_summary": _report_path(summary_output, repo_root),
                "consolidated_report": "data/cross-ref/CONSOLIDATED_REPORT.md",
                "consolidated_report_role": "durable_human_report",
                "generated_report_role": "runner_owned_supporting_artifact",
            },
            "eval_count": len(eval_summaries),
            "evals": eval_summaries,
            "comparisons": comparisons,
        }
    )


def _format_number(value: object, digits: int = 3) -> str:
    number = _float_or_none(value)
    if number is None:
        return "n/a"
    if float(number).is_integer():
        return str(int(number))
    return f"{number:.{digits}f}"


def _format_status_counts(status_counts: dict[str, object]) -> str:
    if not status_counts:
        return "n/a"
    return ", ".join(f"{status} {count}" for status, count in status_counts.items())


def render_cross_eval_report_markdown(summary: dict[str, object]) -> str:
    generated_from = _as_dict(summary.get("generated_from"))
    report_contract = _as_dict(summary.get("report_contract"))
    source_entries = [entry for entry in _as_list(generated_from.get("summaries")) if isinstance(entry, dict)]
    eval_summaries = [entry for entry in _as_list(summary.get("evals")) if isinstance(entry, dict)]

    lines = [
        "# Cross-Eval Report",
        "",
        "Generated facts from published per-eval summaries. It does not rerun evals; regenerate with `run_cross_ref.py cross-eval --publish`.",
        "",
        "## Method",
        "",
        "- `raw Elo`: Pearson and Spearman correlation between external score and LLM Chess Elo on deduped mapped rows with non-null Elo.",
        "- `release-controlled`: Pearson correlation after both external score and Elo are residualized on release month.",
        "- `top chess metric`: strongest non-Elo LLM Chess metric by absolute Pearson correlation on the metric-analysis sample.",
        "- `OLS CV`: repeated 5-fold CV over 3 seeds. Features are selected inside each training fold from predeclared non-Elo chess metrics.",
        "- Deduplication keeps the highest external score per mapped LLM Chess player.",
        "",
        "## Inputs",
        "",
        "| Eval | Summary | SHA256 | Coverage |",
        "| --- | --- | --- | --- |",
    ]
    for source_entry in source_entries:
        lines.append(
            "| "
            f"{source_entry.get('eval_id')} | "
            f"`{source_entry.get('summary_path')}` | "
            f"`{str(source_entry.get('summary_sha256', ''))[:12]}` | "
            f"`{source_entry.get('coverage_path') or 'n/a'}` |"
        )

    lines.extend(
        [
            "",
            "## Signal",
            "",
            "| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    for eval_summary in eval_summaries:
        relationships = _as_dict(eval_summary.get("relationships"))
        strongest_metric = _as_dict(relationships.get("strongest_non_elo_metric"))
        raw_elo = _as_dict(relationships.get("raw_elo"))
        release_controlled = _as_dict(relationships.get("release_controlled_elo"))
        prediction = _as_dict(eval_summary.get("prediction"))
        baseline = _as_dict(prediction.get("baseline_mean"))
        ols = _as_dict(prediction.get("ols"))
        lines.append(
            "| "
            f"{eval_summary.get('eval_label')} | "
            f"r `{_format_number(raw_elo.get('pearson_r'))}`, rho `{_format_number(raw_elo.get('spearman_r'))}`, n `{_format_number(raw_elo.get('n'), digits=0)}` | "
            f"r `{_format_number(release_controlled.get('pearson_r'))}`, n `{_format_number(release_controlled.get('n'), digits=0)}` | "
            f"`{strongest_metric.get('name') or 'n/a'}`: r `{_format_number(strongest_metric.get('pearson_r'))}`, rho `{_format_number(strongest_metric.get('spearman_r'))}`, n `{_format_number(strongest_metric.get('n'), digits=0)}` | "
            f"R2 `{_format_number(ols.get('r2'))}` vs baseline `{_format_number(baseline.get('r2'))}`, rank rho `{_format_number(ols.get('rank_spearman'))}` |"
        )

    lines.extend(
        [
            "",
            "## Coverage",
            "",
            "| Eval | Numeric rows | Mapped rows | Metric sample | Elo sample | Unmatched external | High-impact unresolved |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for eval_summary in eval_summaries:
        coverage = _as_dict(eval_summary.get("coverage"))
        mapping = _as_dict(eval_summary.get("mapping"))
        lines.append(
            "| "
            f"{eval_summary.get('eval_label')} | "
            f"{_format_number(coverage.get('numeric_score_rows'), digits=0)} | "
            f"{_format_number(coverage.get('accepted_mapping_rows'), digits=0)} | "
            f"{_format_number(coverage.get('metric_analysis_rows_max_dedupe'), digits=0)} | "
            f"{_format_number(coverage.get('elo_analysis_rows_max_dedupe'), digits=0)} | "
            f"{_format_number(coverage.get('external_rows_without_llm_chess_match'), digits=0)} | "
            f"{_format_number(mapping.get('unresolved_high_impact_count'), digits=0)} |"
        )

    lines.extend(
        [
            "",
            f"Primary human report: `{report_contract.get('primary_human_report')}`.",
            f"Primary machine-readable artifact: `{report_contract.get('primary_machine_summary')}`.",
        ]
    )

    lines.append("")
    return "\n".join(lines)