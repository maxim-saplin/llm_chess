from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework.analysis_surface import build_analysis_samples
from framework.eval_analysis import EvalAnalysisConfig, run_configured_eval_analysis, standard_game_threshold_sensitivity
from framework.loading import summarize_input_contract
from framework.model_identity import infer_provider_or_family
from framework.normalization import parse_currency, parse_day_month_year, parse_percent, slugify_label
from framework.statistics import (
    bootstrap_corr,
    named_corr,
)

EVAL_ID = "arc_agi_2"
EVAL_LABEL = "ARC-AGI-2"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = CROSS_REF_ROOT / "evals" / "arc-agi-2"
SOURCE_PATH = SOURCE_DIR / "arc-agi-2-apr-2026.csv"
SOURCE_NOTE_PATH = SOURCE_DIR / "SOURCE.md"


def _parse_rate(source: pd.Series, parsed: pd.Series) -> float:
    non_null = int(source.notna().sum())
    parsed_non_null = int(parsed.notna().sum())
    return 1.0 if non_null == 0 else parsed_non_null / non_null


def _relationship_extras(sample: pd.DataFrame, target_column: str) -> dict[str, object]:
    return {
        "bootstrap_95": bootstrap_corr(sample[target_column], sample["elo"]),
    }


def _accepted_row_filter(merged_mapping: pd.DataFrame) -> pd.Series:
    return merged_mapping["score_arc_agi_2"].notna()


def _coverage_extras(config: EvalAnalysisConfig, context: dict[str, object]) -> dict[str, object]:
    samples = context["samples"]
    normalized = context["normalized"]
    metric_joined_rows = samples["metric_joined_rows"]
    elo_joined_rows = samples["elo_joined_rows"]
    elo_joined_players = set(elo_joined_rows["llm_chess_player"].dropna())
    return {
        "mapped_to_llm_chess_rows": int(len(metric_joined_rows)),
        "matched_llm_chess_rows": int(len(samples["elo_analysis_sample"])),
        "matched_unique_llm_chess_players": int(len(elo_joined_players)),
        "external_rows_without_llm_chess_match": int(
            normalized[config.target_score_column].notna().sum() - len(metric_joined_rows)
        ),
        "external_rows_without_llm_chess_elo_join": int(
            normalized[config.target_score_column].notna().sum() - len(elo_joined_rows)
        ),
        "llm_chess_rows_without_eval_match": int(len(samples["elo_players"] - elo_joined_players)),
        "duplicate_mapping_keys": int(metric_joined_rows["llm_chess_player"].duplicated().sum()),
        "duplicate_elo_joined_player_rows": int(elo_joined_rows["llm_chess_player"].duplicated().sum()),
        "system_type_counts": {
            key: int(value)
            for key, value in normalized["SYSTEM TYPE"].fillna("missing").value_counts().sort_index().items()
        },
    }


def _coverage_output_transform(coverage_output: pd.DataFrame) -> pd.DataFrame:
    coverage_output = coverage_output.copy()
    coverage_output["provider_or_family_inferred"] = coverage_output["eval_model_label"].map(
        lambda label: infer_provider_or_family(label)[0]
    )
    return coverage_output


def _sensitivity(config: EvalAnalysisConfig, context: dict[str, object]) -> dict[str, object]:
    merged_mapping = context["merged_mapping"]
    elo = context["elo"]
    metadata = context["metadata"]
    status_sensitivity = []
    for label, statuses in [
        ("accepted_only", {"accepted"}),
        ("accepted_alias_variant", {"accepted", "alias", "variant-compatible"}),
    ]:
        status_rows = merged_mapping[
            merged_mapping["mapping_status"].isin(statuses)
            & merged_mapping["llm_chess_player"].notna()
            & merged_mapping[config.target_score_column].notna()
        ].copy()
        sample = build_analysis_samples(
            status_rows,
            elo,
            metadata,
            score_column=config.target_score_column,
            method="max",
        )["elo_analysis_sample"]
        status_sensitivity.append(
            {
                "status_scope": label,
                **named_corr(f"arc_agi_2_vs_elo_{label}", sample[config.target_score_column], sample["elo"]),
            }
        )
    return {
        "mapping_status": status_sensitivity,
        "min_total_games": standard_game_threshold_sensitivity(config, context),
    }


CONFIG = EvalAnalysisConfig(
    eval_id=EVAL_ID,
    eval_label=EVAL_LABEL,
    summary_tagline="ARC Prize leaderboard rows normalized through the shared cross-ref contracts.",
    target_score_column="score_arc_agi_2",
    prediction_target="ARC-AGI-2 Score",
    repo_root=REPO_ROOT,
    source_note_path=SOURCE_NOTE_PATH,
    default_source_path=SOURCE_PATH,
    default_mapping_path=CROSS_REF_ROOT / "mappings" / "arc_agi_2.csv",
    mapping_basis="Run-time source of truth is the mapping CSV. For ARC it is a reviewed row-level mapping from leaderboard labels into the current LLM Chess inventory.",
    source_seed_column=None,
    fresh_review_status="mapping-csv-reviewed",
    relationship_name="arc_agi_2_vs_elo",
    accepted_row_filter=_accepted_row_filter,
    relationship_extras=_relationship_extras,
    coverage_extras=_coverage_extras,
    coverage_output_transform=_coverage_output_transform,
    sensitivity_builder=_sensitivity,
    limitations=[
        "ARC leaderboard rows can represent systems or reasoning configurations rather than plain base models.",
        "COST (V3) meaning was not defined in the official ARC sources located during this implementation.",
        "Correlations are exploratory and should not be over-interpreted when the matched sample is small or mapping status is unresolved.",
    ],
)


def normalize_source(source_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    actual_source_path = source_path or SOURCE_PATH
    raw = pd.read_csv(actual_source_path)
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
        file_path=actual_source_path,
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