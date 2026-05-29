from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from framework.analysis_surface import (
    dedupe_rows_by_player,
)
from framework.eval_analysis import EvalAnalysisConfig, run_configured_eval_analysis, standard_game_threshold_sensitivity
from framework.loading import summarize_input_contract
from framework.mapping import seed_eci_mapping
from framework.statistics import (
    add_release_month_columns,
    bootstrap_corr,
    named_corr,
)

EVAL_ID = "eci"
EVAL_LABEL = "Epoch ECI"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = CROSS_REF_ROOT / "evals" / "eci"
SOURCE_PATH = EVAL_ROOT / "epoch_eci_may_2026.csv"
SOURCE_NOTE_PATH = EVAL_ROOT / "SOURCE.md"


def _parse_epoch_ci(value: object) -> tuple[float | None, float | None]:
    if pd.isna(value):
        return (None, None)
    raw = str(value).strip()
    if not raw or raw.upper() == "NA":
        return (None, None)
    raw = raw.strip("()")
    try:
        low, high = [float(part.strip()) for part in raw.split("-")]
    except ValueError:
        return (None, None)
    return (low, high)


def _parse_rate(source: pd.Series, parsed: pd.Series) -> float:
    non_null = int(source.notna().sum())
    parsed_non_null = int(parsed.notna().sum())
    return 1.0 if non_null == 0 else parsed_non_null / non_null


def _prepare_eci_sample(
    joined_rows: pd.DataFrame,
    elo_valid: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    method: str,
) -> pd.DataFrame:
    sample = dedupe_rows_by_player(joined_rows, score_column="score_numeric", method=method)
    sample = sample.merge(
        elo_valid,
        left_on="llm_chess_player",
        right_on="Player",
        how="inner",
    )
    sample = sample.merge(
        metadata[["model", "date_released", "reasoning_status"]],
        left_on="llm_chess_player",
        right_on="model",
        how="left",
    )
    return add_release_month_columns(sample, date_column="date_released")


def _weighted_fit(sample: pd.DataFrame) -> dict[str, float | None] | None:
    if len(sample) < 2:
        return None
    positive_moe = sample["elo_moe_95"].dropna()
    positive_moe = positive_moe[positive_moe > 0]
    fallback = float(positive_moe.median()) if not positive_moe.empty else 1.0
    weights = 1.0 / np.square(sample["elo_moe_95"].fillna(fallback).replace(0, fallback))
    coefficients = np.polyfit(sample["score_numeric"], sample["elo"], 1, w=weights)
    predictions = np.polyval(coefficients, sample["score_numeric"])
    weighted_ss_res = np.sum(weights * np.square(sample["elo"] - predictions))
    weighted_mean = np.average(sample["elo"], weights=weights)
    weighted_ss_tot = np.sum(weights * np.square(sample["elo"] - weighted_mean))
    weighted_r2 = None if weighted_ss_tot == 0 else float(1.0 - weighted_ss_res / weighted_ss_tot)
    return {
        "slope": float(coefficients[0]),
        "intercept": float(coefficients[1]),
        "weighted_r2": weighted_r2,
    }


def _leave_one_out_influence(sample: pd.DataFrame) -> list[dict[str, float | str]]:
    base = named_corr("eci_vs_elo", sample["score_numeric"], sample["elo"])
    if base.get("n", 0) < 4 or "pearson_r" not in base or "slope" not in base:
        return []
    rows = []
    for index, row in sample.iterrows():
        loo_sample = sample.drop(index=index)
        loo = named_corr("eci_vs_elo_loo", loo_sample["score_numeric"], loo_sample["elo"])
        if "pearson_r" not in loo or "slope" not in loo:
            continue
        rows.append(
            {
                "llm_chess_model": row["llm_chess_player"],
                "pearson_delta": float(loo["pearson_r"] - base["pearson_r"]),
                "slope_delta": float(loo["slope"] - base["slope"]),
            }
        )
    return sorted(rows, key=lambda item: abs(float(item["pearson_delta"])), reverse=True)[:12]


def _relationship_extras(sample: pd.DataFrame, target_column: str) -> dict[str, object]:
    return {
        "weighted_fit": _weighted_fit(sample),
        "bootstrap_95": bootstrap_corr(
            sample[target_column],
            sample["elo"],
            seed=0,
            n_bootstrap=5000,
        ),
        "leave_one_out_top_influence": _leave_one_out_influence(sample),
    }


def _changed_matches(merged_mapping: pd.DataFrame) -> pd.DataFrame:
    return merged_mapping[
        merged_mapping["source_llm_chess_model"].notna()
        & (merged_mapping["source_llm_chess_model"] != merged_mapping["llm_chess_player"])
    ]


def _changed_match_examples(changed_matches: pd.DataFrame) -> list[dict[str, object]]:
    return changed_matches[
        ["eval_row_id", "eval_model_label", "source_llm_chess_model", "llm_chess_player", "mapping_status"]
    ].head(15).to_dict(orient="records")


def _mapping_source_extras(normalized: pd.DataFrame, merged_mapping: pd.DataFrame) -> dict[str, object]:
    changed_matches = _changed_matches(merged_mapping)
    return {
        "changed_source_bridge_matches": int(len(changed_matches)),
        "changed_source_bridge_examples": _changed_match_examples(changed_matches),
    }


def _mapping_summary_extras(normalized: pd.DataFrame, merged_mapping: pd.DataFrame) -> dict[str, object]:
    changed_matches = _changed_matches(merged_mapping)
    return {
        "legacy_bridge_non_null": int(normalized["source_llm_chess_model"].notna().sum()),
        "legacy_bridge_changed_matches": _changed_match_examples(changed_matches),
    }


def _coverage_extras(config: EvalAnalysisConfig, context: dict[str, object]) -> dict[str, object]:
    samples = context["samples"]
    normalized = context["normalized"]
    metric_joined_rows = samples["metric_joined_rows"]
    elo_joined_rows = samples["elo_joined_rows"]
    elo_joined_players = set(elo_joined_rows["llm_chess_player"].dropna())
    return {
        "rows_joined_to_llm_chess_elo": int(len(elo_joined_rows)),
        "regression_rows_max_dedupe": int(len(samples["elo_analysis_sample"])),
        "external_rows_without_llm_chess_elo_join": int(
            normalized[config.target_score_column].notna().sum() - len(elo_joined_rows)
        ),
        "external_rows_without_llm_chess_metric_join": int(
            normalized[config.target_score_column].notna().sum() - len(metric_joined_rows)
        ),
        "llm_chess_rows_without_eval_match": int(len(samples["elo_players"] - elo_joined_players)),
        "duplicate_metric_joined_player_rows": int(metric_joined_rows["llm_chess_player"].duplicated().sum()),
        "duplicate_joined_player_rows": int(elo_joined_rows["llm_chess_player"].duplicated().sum()),
    }


def _sensitivity(config: EvalAnalysisConfig, context: dict[str, object]) -> dict[str, object]:
    samples = context["samples"]
    metadata = context["metadata"]
    dedupe_sensitivity = []
    for method in ["max", "min", "mean", "median"]:
        sample = _prepare_eci_sample(samples["elo_joined_rows"], samples["elo_available"], metadata, method=method)
        dedupe_sensitivity.append(
            {
                "method": method,
                **named_corr(f"eci_vs_elo_{method}", sample[config.target_score_column], sample["elo"]),
            }
        )
    relationship = context["relationships"]["raw_elo"]
    elo_analysis = samples["elo_analysis_sample"]
    return {
        "dedupe": dedupe_sensitivity,
        "min_total_games": standard_game_threshold_sensitivity(config, context),
        "legacy_parity": {
            "matched_sample_max_dedupe": int(len(elo_analysis)),
            "raw_direct_matches": int(len(samples["elo_joined_rows"])),
            "pearson_r": relationship.get("pearson_r"),
            "r2": relationship.get("r2"),
        },
    }


CONFIG = EvalAnalysisConfig(
    eval_id=EVAL_ID,
    eval_label=EVAL_LABEL,
    summary_tagline="Epoch ECI analysis computed directly in the shared cross-ref framework.",
    target_score_column="score_numeric",
    prediction_target="Epoch Score",
    repo_root=REPO_ROOT,
    source_note_path=SOURCE_NOTE_PATH,
    default_source_path=SOURCE_PATH,
    default_mapping_path=CROSS_REF_ROOT / "mappings" / "eci.csv",
    mapping_basis="Run-time source of truth is the mapping CSV. For ECI it is seeded from the source llm_chess_model bridge and then reviewed in data/cross-ref/mappings/eci.csv.",
    source_seed_column="llm_chess_model",
    fresh_review_status="source-bridge-seeded-qa-passed",
    relationship_name="eci_vs_elo",
    relationship_extras=_relationship_extras,
    mapping_source_extras=_mapping_source_extras,
    mapping_summary_extras=_mapping_summary_extras,
    coverage_extras=_coverage_extras,
    sensitivity_builder=_sensitivity,
)


def normalize_source(source_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    actual_source_path = source_path or SOURCE_PATH
    raw = pd.read_csv(actual_source_path)
    normalized = raw.copy()
    normalized["Score"] = pd.to_numeric(normalized["Score"], errors="coerce")
    cis = normalized["90% CI"].apply(_parse_epoch_ci)
    normalized["eci_ci_low"] = [low for low, _ in cis]
    normalized["eci_ci_high"] = [high for _, high in cis]
    normalized["eci_ci90_half_width"] = (normalized["eci_ci_high"] - normalized["eci_ci_low"]) / 2.0
    normalized = normalized.reset_index(names="source_row_index").copy()
    normalized["eval_id"] = EVAL_ID
    normalized["eval_row_id"] = normalized["source_row_index"].map(lambda idx: f"eci:{idx:04d}")
    normalized["eval_model_label"] = normalized["Model"].astype(str).str.strip()
    normalized["eval_variant_label"] = normalized["eval_model_label"]
    normalized["score_numeric"] = normalized["Score"]
    normalized["score_label"] = "ECI"
    normalized["source_llm_chess_model"] = normalized["llm_chess_model"].astype(str).str.strip()
    normalized.loc[normalized["source_llm_chess_model"].isin(["", "nan", "NaN"]), "source_llm_chess_model"] = pd.NA
    contract = summarize_input_contract(
        df=raw,
        file_path=actual_source_path,
        required_columns=["Model", "Score", "90% CI", "llm_chess_model"],
        key_column="Model",
        numeric_columns=["Score"],
    )
    contract["numeric_parse_rates"] = {
        "score_numeric": _parse_rate(raw["Score"], normalized["score_numeric"]),
        "eci_ci_low": _parse_rate(raw["90% CI"], normalized["eci_ci_low"]),
        "eci_ci_high": _parse_rate(raw["90% CI"], normalized["eci_ci_high"]),
        "eci_ci90_half_width": _parse_rate(raw["90% CI"], normalized["eci_ci90_half_width"]),
    }
    return normalized, contract


def build_seed_mapping(inventory: pd.DataFrame, source_path: Path | None = None) -> pd.DataFrame:
    normalized, _ = normalize_source(source_path)
    return seed_eci_mapping(normalized, inventory)


def run_analysis(
    inventory: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    verification: dict[str, object],
    source_path: Path | None = None,
    mapping_path: Path | None = None,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, str]:
    return run_configured_eval_analysis(
        CONFIG,
        normalize_source,
        mapping,
        verification=verification,
        source_path=source_path,
        mapping_path=mapping_path,
    )