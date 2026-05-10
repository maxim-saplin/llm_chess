from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework.analysis_surface import (
    ELO_STAGE_ID,
    METRIC_STAGE_ID,
    annotate_coverage_rows,
    build_analysis_samples,
    build_analysis_surfaces,
    build_funnel,
)
from framework.loading import load_llm_chess_inputs, summarize_input_contract
from framework.mapping import ACCEPTED_MAPPING_STATUSES, apply_mapping, summarize_mapping
from framework.model_identity import infer_provider_or_family
from framework.normalization import parse_currency, parse_day_month_year, parse_percent, slugify_label
from framework.rendering import render_summary_html
from framework.serialization import json_safe
from framework.statistics import (
    DEFAULT_SELECTED_METRICS,
    add_release_month_columns,
    bootstrap_corr,
    build_game_threshold_sensitivity,
    build_metric_relationships,
    build_prediction_summary,
    named_corr,
    partial_corr_release_month,
)

EVAL_ID = "arc_agi_2"
EVAL_LABEL = "ARC-AGI-2"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = CROSS_REF_ROOT / "evals" / "arc-agi-2"
SOURCE_PATH = SOURCE_DIR / "arc-agi-2-apr-2026.csv"
SOURCE_NOTE_PATH = SOURCE_DIR / "SOURCE.md"
NON_ELO_SELECTED_METRICS = [metric for metric in DEFAULT_SELECTED_METRICS if metric != "elo"]


def _parse_rate(source: pd.Series, parsed: pd.Series) -> float:
    non_null = int(source.notna().sum())
    parsed_non_null = int(parsed.notna().sum())
    return 1.0 if non_null == 0 else parsed_non_null / non_null


def normalize_source() -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_csv(SOURCE_PATH)
    normalized = raw.reset_index(names="source_row_index").copy()
    normalized["eval_id"] = EVAL_ID
    normalized["eval_row_id"] = normalized.apply(
        lambda row: f"{EVAL_ID}:{row['source_row_index']:04d}:{slugify_label(row['AI SYSTEM'])}",
        axis=1,
    )
    normalized["eval_model_label"] = normalized["AI SYSTEM"].astype(str).str.strip()
    normalized["eval_variant_label"] = normalized["eval_model_label"]
    normalized["source_date"] = normalized["DATE"].map(parse_day_month_year)
    normalized["score_arc_agi_1"] = normalized["ARC-AGI-1"].map(parse_percent)
    normalized["score_arc_agi_2"] = normalized["ARC-AGI-2"].map(parse_percent)
    normalized["score_arc_agi_3"] = normalized["ARC-AGI-3"].map(parse_percent)
    normalized["score_numeric"] = normalized["score_arc_agi_2"]
    normalized["cost_per_task"] = normalized["COST/TASK"].map(parse_currency)
    normalized["cost_v3"] = normalized["COST (V3)"].map(parse_currency)
    normalized["score_label"] = "ARC-AGI-2"
    contract = summarize_input_contract(
        df=raw,
        file_path=SOURCE_PATH,
        required_columns=[
            "AI SYSTEM",
            "AUTHOR",
            "DATE",
            "SYSTEM TYPE",
            "ARC-AGI-1",
            "ARC-AGI-2",
            "ARC-AGI-3",
            "COST/TASK",
            "COST (V3)",
            "CODE / PAPER",
        ],
        key_column="AI SYSTEM",
        numeric_columns=[],
    )
    contract["numeric_parse_rates"] = {
        "score_arc_agi_1": _parse_rate(raw["ARC-AGI-1"], normalized["score_arc_agi_1"]),
        "score_arc_agi_2": _parse_rate(raw["ARC-AGI-2"], normalized["score_arc_agi_2"]),
        "score_arc_agi_3": _parse_rate(raw["ARC-AGI-3"], normalized["score_arc_agi_3"]),
        "cost_per_task": _parse_rate(raw["COST/TASK"], normalized["cost_per_task"]),
        "cost_v3": _parse_rate(raw["COST (V3)"], normalized["cost_v3"]),
    }
    return normalized, contract


def run_analysis(
    inventory: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    verification: dict[str, object],
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, str]:
    normalized, source_contract = normalize_source()
    merged_mapping = apply_mapping(normalized, mapping)
    elo, metadata, llm_chess_inputs = load_llm_chess_inputs(REPO_ROOT)
    accepted = merged_mapping[
        merged_mapping["mapping_status"].isin(ACCEPTED_MAPPING_STATUSES)
        & merged_mapping["llm_chess_player"].notna()
        & merged_mapping["score_arc_agi_2"].notna()
    ].copy()
    samples = build_analysis_samples(
        accepted,
        elo,
        metadata,
        score_column="score_arc_agi_2",
        method="max",
    )
    metric_joined_rows = samples["metric_joined_rows"]
    metric_analysis = samples["metric_analysis_sample"]
    elo_joined_rows = samples["elo_joined_rows"]
    elo_analysis = samples["elo_analysis_sample"]

    raw_relationship = named_corr("arc_agi_2_vs_elo", elo_analysis["score_arc_agi_2"], elo_analysis["elo"])
    raw_relationship["sample_stage_id"] = ELO_STAGE_ID
    raw_relationship["bootstrap_95"] = bootstrap_corr(elo_analysis["score_arc_agi_2"], elo_analysis["elo"])
    release_controlled = partial_corr_release_month(
        elo_analysis["score_arc_agi_2"],
        elo_analysis["elo"],
        elo_analysis["release_month_index"],
    )
    if release_controlled is not None:
        release_controlled["sample_stage_id"] = ELO_STAGE_ID
    selected_metrics = build_metric_relationships(
        metric_analysis,
        target_column="score_arc_agi_2",
        candidate_metrics=DEFAULT_SELECTED_METRICS,
    )
    for metric in selected_metrics:
        metric["sample_stage_id"] = METRIC_STAGE_ID
    prediction = build_prediction_summary(
        metric_analysis,
        target_column="score_arc_agi_2",
        candidate_metrics=NON_ELO_SELECTED_METRICS,
    )
    prediction = {
        "target": "ARC-AGI-2 Score",
        "sample_stage_id": METRIC_STAGE_ID,
        "sample_n": int(len(metric_analysis)),
        **prediction,
    }
    mapping_summary = summarize_mapping(merged_mapping, score_column="score_arc_agi_2", qa_verdict=verification.get("mapping_qa_status"))
    mapping_summary["mapping_file_path"] = str((CROSS_REF_ROOT / "mappings" / "arc_agi_2.csv").relative_to(REPO_ROOT))

    metric_joined_players = set(metric_joined_rows["llm_chess_player"].dropna())
    elo_joined_players = set(elo_joined_rows["llm_chess_player"].dropna())
    status_sensitivity = []
    for label, statuses in [
        ("accepted_only", {"accepted"}),
        ("accepted_alias_variant", ACCEPTED_MAPPING_STATUSES),
    ]:
        status_rows = merged_mapping[
            merged_mapping["mapping_status"].isin(statuses)
            & merged_mapping["llm_chess_player"].notna()
            & merged_mapping["score_arc_agi_2"].notna()
        ].copy()
        sample = build_analysis_samples(
            status_rows,
            elo,
            metadata,
            score_column="score_arc_agi_2",
            method="max",
        )["elo_analysis_sample"]
        status_sensitivity.append(
            {
                "status_scope": label,
                **named_corr(f"arc_agi_2_vs_elo_{label}", sample["score_arc_agi_2"], sample["elo"]),
            }
        )

    coverage_output = annotate_coverage_rows(
        merged_mapping,
        score_column="score_arc_agi_2",
        metric_joined_rows=metric_joined_rows,
        metric_analysis_rows=samples["metric_analysis_rows"],
        elo_joined_rows=elo_joined_rows,
        elo_analysis_rows=samples["elo_analysis_rows"],
    )
    coverage_output["provider_or_family_inferred"] = coverage_output["eval_model_label"].map(
        lambda label: infer_provider_or_family(label)[0]
    )

    summary = {
        "eval_id": EVAL_ID,
        "eval_label": EVAL_LABEL,
        "summary_tagline": "ARC Prize leaderboard rows normalized through the shared cross-ref contracts.",
        "target_score_column": "score_arc_agi_2",
        "inputs": {
            "source": source_contract,
            "source_note_path": str(SOURCE_NOTE_PATH.relative_to(REPO_ROOT)),
            "source_file_paths": [str(SOURCE_PATH.relative_to(REPO_ROOT))],
        },
        "llm_chess_inputs": llm_chess_inputs,
        "mapping_source_of_truth": {
            "mapping_file": str((CROSS_REF_ROOT / "mappings" / "arc_agi_2.csv").relative_to(REPO_ROOT)),
            "mapping_basis": "Run-time source of truth is the mapping CSV. For ARC it is a reviewed row-level mapping from leaderboard labels into the current LLM Chess inventory.",
            "source_seed_column": None,
            "run_used_mapping_file_directly": True,
            "fresh_review_status": "mapping-csv-reviewed",
            "changed_source_bridge_matches": 0,
            "changed_source_bridge_examples": [],
        },
        "mapping": mapping_summary,
        "coverage": {
            "external_rows": int(len(normalized)),
            "numeric_score_rows": int(normalized["score_arc_agi_2"].notna().sum()),
            "accepted_mapping_rows": int(len(accepted)),
            "rows_joined_to_llm_chess_metric_rows": int(len(metric_joined_rows)),
            "unique_llm_chess_players_joined_to_metric_rows": int(len(metric_joined_players)),
            "metric_analysis_rows_max_dedupe": int(len(metric_analysis)),
            "rows_joined_to_llm_chess_rows_with_non_null_elo": int(len(elo_joined_rows)),
            "unique_llm_chess_players_joined_to_elo": int(len(elo_joined_players)),
            "elo_analysis_rows_max_dedupe": int(len(elo_analysis)),
            "mapped_to_llm_chess_rows": int(len(metric_joined_rows)),
            "matched_llm_chess_rows": int(len(elo_analysis)),
            "matched_unique_llm_chess_players": int(len(elo_joined_players)),
            "external_rows_without_llm_chess_match": int(
                normalized["score_arc_agi_2"].notna().sum() - len(metric_joined_rows)
            ),
            "external_rows_without_llm_chess_elo_join": int(
                normalized["score_arc_agi_2"].notna().sum() - len(elo_joined_rows)
            ),
            "llm_chess_rows_without_eval_match": int(len(samples["elo_players"] - elo_joined_players)),
            "duplicate_mapping_keys": int(metric_joined_rows["llm_chess_player"].duplicated().sum()),
            "duplicate_elo_joined_player_rows": int(elo_joined_rows["llm_chess_player"].duplicated().sum()),
            "system_type_counts": {
                key: int(value)
                for key, value in normalized["SYSTEM TYPE"].fillna("missing").value_counts().sort_index().items()
            },
        },
        "analysis_surfaces": build_analysis_surfaces(
            metric_count=len(metric_analysis),
            elo_count=len(elo_analysis),
        ),
        "funnel": build_funnel(
            numeric_score_rows=int(normalized["score_arc_agi_2"].notna().sum()),
            accepted_mapping_rows=int(len(accepted)),
            rows_joined_to_any_llm_chess_row=int(len(metric_joined_rows)),
            metric_analysis_rows_max_dedupe=int(len(metric_analysis)),
            rows_joined_to_llm_chess_rows_with_non_null_elo=int(len(elo_joined_rows)),
            elo_analysis_rows_max_dedupe=int(len(elo_analysis)),
        ),
        "relationships": {
            "raw_elo": raw_relationship,
            "release_controlled_elo": release_controlled,
            "selected_metrics": selected_metrics,
        },
        "prediction": prediction,
        "sensitivity": {
            "mapping_status": status_sensitivity,
            "min_total_games": build_game_threshold_sensitivity(elo_analysis, target_column="score_arc_agi_2"),
        },
        "limitations": [
            "ARC leaderboard rows can represent systems or reasoning configurations rather than plain base models.",
            "COST (V3) meaning was not defined in the official ARC sources located during this implementation.",
            "Correlations are exploratory and should not be over-interpreted when the matched sample is small or mapping status is unresolved.",
        ],
        "verification": verification,
    }
    summary = json_safe(summary)
    normalized_output = normalized.copy()
    return summary, normalized_output, coverage_output, render_summary_html(summary)