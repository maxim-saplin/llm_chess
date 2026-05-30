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
    partial_corr_release_month,
)

EVAL_ID = "delegate_52"
EVAL_LABEL = "DELEGATE-52"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = CROSS_REF_ROOT / "evals" / "delegate-52"
SOURCE_PATH = SOURCE_DIR / "delegate-52-may-2026.csv"
SOURCE_NOTE_PATH = SOURCE_DIR / "SOURCE.md"

# DELEGATE-52 reports a Reconstruction Score curve (RS@k) per model, not one number. We keep every
# interaction depth and report the Elo relationship at each, plus two derived robustness measures.
# rs_at_20 is the framework's required single anchor column (the paper's headline long-horizon
# endpoint and the most discriminating depth); it does not limit the reported analysis.
RS_DEPTH_COLUMNS = [f"rs_at_{k}" for k in range(2, 21, 2)]
ANCHOR_COLUMN = "rs_at_20"
DERIVED_COLUMNS = ["rs_mean", "rs_degradation"]
FACTOR_COLUMNS = [*RS_DEPTH_COLUMNS, *DERIVED_COLUMNS]


def _parse_rate(source: pd.Series, parsed: pd.Series) -> float:
    non_null = int(source.notna().sum())
    parsed_non_null = int(parsed.notna().sum())
    return 1.0 if non_null == 0 else parsed_non_null / non_null


def _relationship_extras(sample: pd.DataFrame, target_column: str) -> dict[str, object]:
    # Multi-factor headline: Elo correlation at every interaction depth plus the mean curve level and
    # the degradation slope (rs_at_2 - rs_at_20), so no single arbitrarily chosen depth drives the
    # conclusion.
    depth_relationships = []
    for column in FACTOR_COLUMNS:
        if column not in sample.columns:
            continue
        relationship = named_corr(f"{column}_vs_elo", sample[column], sample["elo"])
        relationship["factor"] = column
        depth_relationships.append(relationship)
    return {
        "bootstrap_95": bootstrap_corr(sample[target_column], sample["elo"]),
        "rs_depth_vs_elo": depth_relationships,
    }


def _accepted_row_filter(merged_mapping: pd.DataFrame) -> pd.Series:
    return merged_mapping[ANCHOR_COLUMN].notna()


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
        "provider_counts": {
            key: int(value)
            for key, value in normalized["provider"].fillna("missing").value_counts().sort_index().items()
        },
    }


def _coverage_output_transform(coverage_output: pd.DataFrame) -> pd.DataFrame:
    coverage_output = coverage_output.copy()
    coverage_output["provider_or_family_inferred"] = coverage_output["provider"]
    return coverage_output


def _sensitivity(config: EvalAnalysisConfig, context: dict[str, object]) -> dict[str, object]:
    merged_mapping = context["merged_mapping"]
    elo = context["elo"]
    metadata = context["metadata"]
    elo_sample = context["samples"]["elo_analysis_sample"]

    # Per-depth release-controlled Elo: does each interaction depth still track Elo once the linear
    # release-month trend is removed from both sides?
    depth_release_controlled = []
    for column in FACTOR_COLUMNS:
        if column not in elo_sample.columns or "release_month_index" not in elo_sample.columns:
            continue
        partial = partial_corr_release_month(elo_sample[column], elo_sample["elo"], elo_sample["release_month_index"])
        depth_release_controlled.append({"factor": column, "partial_release_month": partial})

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
                **named_corr(f"delegate_52_vs_elo_{label}", sample[config.target_score_column], sample["elo"]),
            }
        )
    return {
        "rs_depth_release_controlled": depth_release_controlled,
        "mapping_status": status_sensitivity,
        "min_total_games": standard_game_threshold_sensitivity(config, context),
    }


CONFIG = EvalAnalysisConfig(
    eval_id=EVAL_ID,
    eval_label=EVAL_LABEL,
    summary_tagline="DELEGATE-52 round-trip relay reconstruction-score curve normalized through the shared cross-ref contracts.",
    target_score_column=ANCHOR_COLUMN,
    prediction_target="DELEGATE-52 RS@20",
    repo_root=REPO_ROOT,
    source_note_path=SOURCE_NOTE_PATH,
    default_source_path=SOURCE_PATH,
    default_mapping_path=CROSS_REF_ROOT / "mappings" / "delegate_52.csv",
    mapping_basis="Run-time source of truth is the mapping CSV. For DELEGATE-52 it is a reviewed row-level mapping from paper Table 1 display names into the current LLM Chess inventory; reasoning configs are unspecified by the paper so the established tier convention is applied with a config caveat.",
    source_seed_column=None,
    fresh_review_status="mapping-csv-reviewed",
    relationship_name="delegate_52_vs_elo",
    accepted_row_filter=_accepted_row_filter,
    relationship_extras=_relationship_extras,
    coverage_extras=_coverage_extras,
    coverage_output_transform=_coverage_output_transform,
    sensitivity_builder=_sensitivity,
    limitations=[
        "Source is the paper's Table 1 (arXiv 2604.15597v1), transcribed by hand; DELEGATE-52 publishes no machine-readable results file.",
        "Reconstruction Score measures one behavior (long-horizon delegated document-editing fidelity), not broad capability, and can diverge from chess Elo.",
        "Per-model reasoning effort and exact API versions are in the paper's Appendix L (not machine-extractable); the mapping treats reasoning config as unspecified and applies the tier convention with a caveat.",
        "rs_at_20 is the framework anchor; the reported result is the Elo correlation profile across all depths plus the degradation slope, not a single depth.",
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
    normalized["provider"] = normalized["provider"].astype(str).str.strip()
    for column in RS_DEPTH_COLUMNS:
        normalized[column] = raw[column].map(safe_float)
    normalized["rs_mean"] = normalized[RS_DEPTH_COLUMNS].mean(axis=1, skipna=False)
    normalized["rs_degradation"] = normalized["rs_at_2"] - normalized["rs_at_20"]
    normalized["score_numeric"] = normalized[ANCHOR_COLUMN]
    normalized["score_label"] = "DELEGATE-52 RS@20"
    contract = summarize_input_contract(
        df=raw,
        file_path=actual_source_path,
        required_columns=["model", "provider", *RS_DEPTH_COLUMNS],
        key_column="model",
        numeric_columns=[],
    )
    contract["numeric_parse_rates"] = {
        column: _parse_rate(raw[column], normalized[column]) for column in RS_DEPTH_COLUMNS
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
