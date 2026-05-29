from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework.analysis_surface import build_analysis_samples
from framework.eval_analysis import EvalAnalysisConfig, run_configured_eval_analysis, standard_game_threshold_sensitivity
from framework.loading import summarize_input_contract
from framework.normalization import safe_float, slugify_label
from framework.statistics import (
    bootstrap_corr,
    named_corr,
)

EVAL_ID = "bullshit_bench"
EVAL_LABEL = "BullshitBench v2"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = CROSS_REF_ROOT / "evals" / "bullshit-bench"
SOURCE_PATH = SOURCE_DIR / "bullshit_bench_v2_may_2026.csv"
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
    return merged_mapping["score_numeric"].notna()


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
        "org_counts": {
            key: int(value)
            for key, value in normalized["org"].fillna("missing").value_counts().sort_index().items()
        },
        "reasoning_level_counts": {
            key: int(value)
            for key, value in normalized["reasoning"].fillna("missing").value_counts().sort_index().items()
        },
    }


def _coverage_output_transform(coverage_output: pd.DataFrame) -> pd.DataFrame:
    coverage_output = coverage_output.copy()
    coverage_output["provider_or_family_inferred"] = coverage_output["org"]
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
                **named_corr(f"bullshit_bench_vs_elo_{label}", sample[config.target_score_column], sample["elo"]),
            }
        )
    return {
        "mapping_status": status_sensitivity,
        "min_total_games": standard_game_threshold_sensitivity(config, context),
    }


CONFIG = EvalAnalysisConfig(
    eval_id=EVAL_ID,
    eval_label=EVAL_LABEL,
    summary_tagline="BullshitBench v2 nonsense-detection leaderboard normalized through the shared cross-ref contracts.",
    target_score_column="score_numeric",
    prediction_target="BullshitBench avg_score",
    repo_root=REPO_ROOT,
    source_note_path=SOURCE_NOTE_PATH,
    default_source_path=SOURCE_PATH,
    default_mapping_path=CROSS_REF_ROOT / "mappings" / "bullshit_bench.csv",
    mapping_basis="Run-time source of truth is the mapping CSV. For BullshitBench it is a reviewed row-level mapping from per-reasoning-level leaderboard rows into the current LLM Chess inventory, matching reasoning effort where both sides expose it.",
    source_seed_column=None,
    fresh_review_status="mapping-csv-reviewed",
    relationship_name="bullshit_bench_vs_elo",
    accepted_row_filter=_accepted_row_filter,
    relationship_extras=_relationship_extras,
    coverage_extras=_coverage_extras,
    coverage_output_transform=_coverage_output_transform,
    sensitivity_builder=_sensitivity,
    limitations=[
        "avg_score measures one behavior (nonsense detection), not broad capability; it can diverge from or invert raw capability rankings.",
        "Leaderboard rows are per reasoning level, so one base model contributes several external rows that are deduped by keeping the highest avg_score per LLM Chess player.",
        "Many leaderboard models have no LLM Chess counterpart (distinct host tier, open-weight long-tail, or stealth rows) and remain unmatched.",
        "Correlations are exploratory and should not be over-interpreted when the matched sample is small or mapping status is unresolved.",
    ],
)


def normalize_source(source_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    actual_source_path = source_path or SOURCE_PATH
    raw = pd.read_csv(actual_source_path)
    normalized = raw.reset_index(names="source_row_index").copy()
    normalized["eval_id"] = EVAL_ID
    normalized["eval_row_id"] = normalized.apply(
        lambda row: f"{EVAL_ID}:{row['source_row_index']:04d}:{slugify_label(row['model'])}",
        axis=1,
    )
    normalized["eval_model_label"] = normalized["model"].astype(str).str.strip()
    normalized["eval_variant_label"] = normalized["eval_model_label"]
    normalized["score_numeric"] = normalized["avg_score"].map(safe_float)
    normalized["green_rate_numeric"] = normalized["green_rate"].map(safe_float)
    normalized["red_rate_numeric"] = normalized["red_rate"].map(safe_float)
    normalized["score_label"] = "BullshitBench avg_score"
    contract = summarize_input_contract(
        df=raw,
        file_path=actual_source_path,
        required_columns=[
            "rank",
            "model",
            "org",
            "reasoning",
            "avg_score",
            "green_rate",
            "red_rate",
            "score_2",
            "score_1",
            "score_0",
            "nonsense_count",
            "error_count",
        ],
        key_column="model",
        numeric_columns=["avg_score", "green_rate", "red_rate"],
    )
    contract["numeric_parse_rates"] = {
        "score_numeric": _parse_rate(raw["avg_score"], normalized["score_numeric"]),
        "green_rate_numeric": _parse_rate(raw["green_rate"], normalized["green_rate_numeric"]),
        "red_rate_numeric": _parse_rate(raw["red_rate"], normalized["red_rate_numeric"]),
    }
    return normalized, contract


def run_analysis(
    inventory: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    verification: dict[str, object],
    source_path: Path | None = None,
    mapping_path: Path | None = None,
    mistake_stats: str = "excluded",
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, str]:
    return run_configured_eval_analysis(
        CONFIG,
        normalize_source,
        mapping,
        verification=verification,
        source_path=source_path,
        mapping_path=mapping_path,
        mistake_stats=mistake_stats,
    )
