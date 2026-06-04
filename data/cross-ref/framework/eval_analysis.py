from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from framework.analysis_surface import (
    ELO_STAGE_ID,
    METRIC_STAGE_ID,
    annotate_coverage_rows,
    build_analysis_samples,
    build_analysis_surfaces,
    build_funnel,
)
from framework.data_quality import (
    MISTAKE_STATS_TRUSTED_AFTER,
    REPAIRABLE_MISTAKE_METRICS,
    clean_mistake_stats_mask,
)
from framework.loading import load_llm_chess_inputs
from framework.mapping import ACCEPTED_MAPPING_STATUSES, apply_mapping, summarize_mapping
from framework.rendering import render_summary_html
from framework.serialization import json_safe
from framework.statistics import (
    DEFAULT_SELECTED_METRICS,
    build_game_threshold_sensitivity,
    build_metric_relationships,
    build_prediction_summary,
    named_corr,
    partial_corr_release_month,
)

NormalizedSource = Callable[[Path | None], tuple[pd.DataFrame, dict[str, object]]]


@dataclass(frozen=True)
class EvalAnalysisConfig:
    eval_id: str
    eval_label: str
    summary_tagline: str
    target_score_column: str
    prediction_target: str
    repo_root: Path
    source_note_path: Path
    default_source_path: Path
    default_mapping_path: Path
    mapping_basis: str
    source_seed_column: str | None
    fresh_review_status: str
    relationship_name: str
    selected_metrics: list[str] = field(default_factory=lambda: list(DEFAULT_SELECTED_METRICS))
    prediction_candidate_metrics: list[str] = field(
        default_factory=lambda: [metric for metric in DEFAULT_SELECTED_METRICS if metric != "elo"]
    )
    accepted_row_filter: Callable[[pd.DataFrame], pd.Series] | None = None
    relationship_extras: Callable[[pd.DataFrame, str], dict[str, object]] | None = None
    mapping_source_extras: Callable[[pd.DataFrame, pd.DataFrame], dict[str, object]] | None = None
    mapping_summary_extras: Callable[[pd.DataFrame, pd.DataFrame], dict[str, object]] | None = None
    coverage_extras: Callable[[EvalAnalysisConfig, dict[str, object]], dict[str, object]] | None = None
    coverage_output_transform: Callable[[pd.DataFrame], pd.DataFrame] | None = None
    sensitivity_builder: Callable[[EvalAnalysisConfig, dict[str, object]], dict[str, object]] | None = None
    limitations: list[str] = field(default_factory=list)


def _ordered_extend(base: list[str], extra: list[str]) -> list[str]:
    out = list(base)
    for item in extra:
        if item not in out:
            out.append(item)
    return out


def _report_path(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)


def _accepted_rows(config: EvalAnalysisConfig, merged_mapping: pd.DataFrame) -> pd.DataFrame:
    accepted_mask = (
        merged_mapping["mapping_status"].isin(ACCEPTED_MAPPING_STATUSES)
        & merged_mapping["llm_chess_player"].notna()
    )
    if config.accepted_row_filter is not None:
        accepted_mask = accepted_mask & config.accepted_row_filter(merged_mapping)
    return merged_mapping[accepted_mask].copy()


def _metric_relationships(
    sample: pd.DataFrame,
    *,
    target_column: str,
    candidate_metrics: list[str],
    allowed_repaired: frozenset[str] | set[str] = frozenset(),
) -> list[dict[str, object]]:
    selected_metrics = build_metric_relationships(
        sample,
        target_column=target_column,
        candidate_metrics=candidate_metrics,
        allowed_repaired=allowed_repaired,
    )
    for metric in selected_metrics:
        metric["sample_stage_id"] = METRIC_STAGE_ID
    return selected_metrics


def _prediction_summary(
    sample: pd.DataFrame,
    *,
    target_column: str,
    target_label: str,
    candidate_metrics: list[str],
    allowed_repaired: frozenset[str] | set[str] = frozenset(),
) -> dict[str, object]:
    return {
        "target": target_label,
        "sample_stage_id": METRIC_STAGE_ID,
        "sample_n": int(len(sample)),
        **build_prediction_summary(
            sample,
            target_column=target_column,
            candidate_metrics=candidate_metrics,
            allowed_repaired=allowed_repaired,
        ),
    }


def _build_core_relationships(
    config: EvalAnalysisConfig,
    elo_analysis: pd.DataFrame,
    metric_analysis: pd.DataFrame,
    *,
    selected_metrics: list[str],
    allowed_repaired: frozenset[str] | set[str] = frozenset(),
) -> dict[str, object]:
    raw_relationship = named_corr(
        config.relationship_name,
        elo_analysis[config.target_score_column],
        elo_analysis["elo"],
    )
    raw_relationship["sample_stage_id"] = ELO_STAGE_ID
    if config.relationship_extras is not None:
        raw_relationship.update(config.relationship_extras(elo_analysis, config.target_score_column))

    release_controlled = partial_corr_release_month(
        elo_analysis[config.target_score_column],
        elo_analysis["elo"],
        elo_analysis["release_month_index"],
    )
    if release_controlled is not None:
        release_controlled["sample_stage_id"] = ELO_STAGE_ID

    return {
        "raw_elo": raw_relationship,
        "release_controlled_elo": release_controlled,
        "selected_metrics": _metric_relationships(
            metric_analysis,
            target_column=config.target_score_column,
            candidate_metrics=selected_metrics,
            allowed_repaired=allowed_repaired,
        ),
    }


def _base_coverage(
    config: EvalAnalysisConfig,
    normalized: pd.DataFrame,
    accepted: pd.DataFrame,
    samples: dict[str, object],
) -> dict[str, object]:
    metric_joined_rows = samples["metric_joined_rows"]
    metric_analysis = samples["metric_analysis_sample"]
    elo_joined_rows = samples["elo_joined_rows"]
    elo_analysis = samples["elo_analysis_sample"]
    metric_joined_players = set(metric_joined_rows["llm_chess_player"].dropna())
    elo_joined_players = set(elo_joined_rows["llm_chess_player"].dropna())
    return {
        "external_rows": int(len(normalized)),
        "numeric_score_rows": int(normalized[config.target_score_column].notna().sum()),
        "accepted_mapping_rows": int(len(accepted)),
        "rows_joined_to_llm_chess_metric_rows": int(len(metric_joined_rows)),
        "unique_llm_chess_players_joined_to_metric_rows": int(len(metric_joined_players)),
        "metric_analysis_rows_max_dedupe": int(len(metric_analysis)),
        "rows_joined_to_llm_chess_rows_with_non_null_elo": int(len(elo_joined_rows)),
        "unique_llm_chess_players_joined_to_elo": int(len(elo_joined_players)),
        "elo_analysis_rows_max_dedupe": int(len(elo_analysis)),
    }


def run_configured_eval_analysis(
    config: EvalAnalysisConfig,
    normalize_source: NormalizedSource,
    mapping: pd.DataFrame,
    *,
    verification: dict[str, object],
    source_path: Path | None = None,
    mapping_path: Path | None = None,
    mistake_stats: str = "excluded",
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, str]:
    if mistake_stats not in ("excluded", "clean_only"):
        raise ValueError(f"mistake_stats must be 'excluded' or 'clean_only', got {mistake_stats!r}")
    actual_source_path = source_path or config.default_source_path
    actual_mapping_path = mapping_path or config.default_mapping_path
    normalized, source_contract = normalize_source(actual_source_path)
    merged_mapping = apply_mapping(normalized, mapping)
    accepted = _accepted_rows(config, merged_mapping)
    elo, metadata, llm_chess_inputs = load_llm_chess_inputs(config.repo_root)

    # Mistake-stats mode. By default the historically tainted error metrics stay excluded. In
    # "clean_only" we restrict the sample to models stamped clean (min_game_date >= cutoff) and
    # re-enable the repaired rate metrics for that sample. Pre-cutoff models are dropped wholesale;
    # we never recompute an individual model's stats.
    clean_mask = clean_mistake_stats_mask(elo)
    clean_players = sorted(elo.loc[clean_mask, "Player"].dropna())
    dropped_players = sorted(elo.loc[~clean_mask, "Player"].dropna())
    if mistake_stats == "clean_only":
        elo = elo.loc[clean_mask].reset_index(drop=True)
        allowed_repaired = frozenset(m for m in REPAIRABLE_MISTAKE_METRICS if m in elo.columns)
        selected_metrics = _ordered_extend(config.selected_metrics, sorted(allowed_repaired))
        prediction_candidates = _ordered_extend(config.prediction_candidate_metrics, sorted(allowed_repaired))
    else:
        allowed_repaired = frozenset()
        selected_metrics = list(config.selected_metrics)
        prediction_candidates = list(config.prediction_candidate_metrics)

    samples = build_analysis_samples(
        accepted,
        elo,
        metadata,
        score_column=config.target_score_column,
        method="max",
    )

    metric_joined_rows = samples["metric_joined_rows"]
    metric_analysis_rows = samples["metric_analysis_rows"]
    metric_analysis = samples["metric_analysis_sample"]
    elo_joined_rows = samples["elo_joined_rows"]
    elo_analysis_rows = samples["elo_analysis_rows"]
    elo_analysis = samples["elo_analysis_sample"]

    relationships = _build_core_relationships(
        config,
        elo_analysis,
        metric_analysis,
        selected_metrics=selected_metrics,
        allowed_repaired=allowed_repaired,
    )
    prediction = _prediction_summary(
        metric_analysis,
        target_column=config.target_score_column,
        target_label=config.prediction_target,
        candidate_metrics=prediction_candidates,
        allowed_repaired=allowed_repaired,
    )
    mapping_summary = summarize_mapping(
        merged_mapping,
        score_column=config.target_score_column,
        qa_verdict=verification.get("mapping_qa_status"),
    )
    mapping_summary["mapping_file_path"] = _report_path(actual_mapping_path, config.repo_root)
    if config.mapping_summary_extras is not None:
        mapping_summary.update(config.mapping_summary_extras(normalized, merged_mapping))

    mapping_source_of_truth = {
        "mapping_file": _report_path(actual_mapping_path, config.repo_root),
        "mapping_basis": config.mapping_basis,
        "source_seed_column": config.source_seed_column,
        "run_used_mapping_file_directly": True,
        "fresh_review_status": config.fresh_review_status,
        "changed_source_bridge_matches": 0,
        "changed_source_bridge_examples": [],
    }
    if config.mapping_source_extras is not None:
        mapping_source_of_truth.update(config.mapping_source_extras(normalized, merged_mapping))

    coverage = _base_coverage(config, normalized, accepted, samples)
    context = {
        "normalized": normalized,
        "merged_mapping": merged_mapping,
        "accepted": accepted,
        "elo": elo,
        "metadata": metadata,
        "samples": samples,
        "relationships": relationships,
        "prediction": prediction,
    }
    if config.coverage_extras is not None:
        coverage.update(config.coverage_extras(config, context))

    coverage_output = annotate_coverage_rows(
        merged_mapping,
        score_column=config.target_score_column,
        metric_joined_rows=metric_joined_rows,
        metric_analysis_rows=metric_analysis_rows,
        elo_joined_rows=elo_joined_rows,
        elo_analysis_rows=elo_analysis_rows,
    )
    if config.coverage_output_transform is not None:
        coverage_output = config.coverage_output_transform(coverage_output)

    sensitivity = {}
    if config.sensitivity_builder is not None:
        sensitivity = config.sensitivity_builder(config, context)

    summary = {
        "eval_id": config.eval_id,
        "eval_label": config.eval_label,
        "summary_tagline": config.summary_tagline,
        "target_score_column": config.target_score_column,
        "inputs": {
            "source": source_contract,
            "source_note_path": str(config.source_note_path.relative_to(config.repo_root)),
            "source_file_paths": [_report_path(actual_source_path, config.repo_root)],
        },
        "llm_chess_inputs": llm_chess_inputs,
        "mistake_stats": {
            "mode": mistake_stats,
            "trusted_after": MISTAKE_STATS_TRUSTED_AFTER,
            "repaired_metrics_enabled": sorted(allowed_repaired),
            "clean_player_count": len(clean_players),
            "pre_cutoff_player_count": len(dropped_players),
            "pre_cutoff_players_dropped": dropped_players if mistake_stats == "clean_only" else [],
        },
        "mapping_source_of_truth": mapping_source_of_truth,
        "mapping": mapping_summary,
        "coverage": coverage,
        "analysis_surfaces": build_analysis_surfaces(
            metric_count=len(metric_analysis),
            elo_count=len(elo_analysis),
        ),
        "funnel": build_funnel(
            numeric_score_rows=int(normalized[config.target_score_column].notna().sum()),
            accepted_mapping_rows=int(len(accepted)),
            rows_joined_to_any_llm_chess_row=int(len(metric_joined_rows)),
            metric_analysis_rows_max_dedupe=int(len(metric_analysis)),
            rows_joined_to_llm_chess_rows_with_non_null_elo=int(len(elo_joined_rows)),
            elo_analysis_rows_max_dedupe=int(len(elo_analysis)),
        ),
        "relationships": relationships,
        "prediction": prediction,
        "sensitivity": sensitivity,
        "verification": verification,
    }
    if config.limitations:
        summary["limitations"] = list(config.limitations)

    summary = json_safe(summary)
    normalized_output = normalized.copy()
    return summary, normalized_output, coverage_output, render_summary_html(summary)


def standard_game_threshold_sensitivity(config: EvalAnalysisConfig, context: dict[str, object]) -> list[dict[str, object]]:
    return build_game_threshold_sensitivity(
        context["samples"]["elo_analysis_sample"],
        target_column=config.target_score_column,
    )