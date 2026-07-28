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

EVAL_ID = "vals_index"
EVAL_LABEL = "Vals Index"
REPO_ROOT = Path(__file__).resolve().parents[3]
CROSS_REF_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = CROSS_REF_ROOT / "evals" / "vals-index"
SOURCE_PATH = SOURCE_DIR / "vals_index_v1_2_july_2026.csv"
SOURCE_NOTE_PATH = SOURCE_DIR / "SOURCE.md"

# The Vals Index is itself a composite: the published v1.2 formula is
#   Coding     = 0.25*SWE_Bench + 0.25*TBench + 0.5*VibeCodeBench
#   Vals_Index = (2.0 * AVG(CorpFin, FinanceAgent) + 1.4 * Coding) / 3.4
# vals_index is the framework's required single anchor column: it is the leaderboard's own headline
# number, the one the page ranks on. The five component task scores travel with it so the reported
# analysis can show whether the anchor's Elo relationship is carried by the finance side, the coding
# side, or neither, rather than resting on one aggregate whose weights we did not choose.
TASK_COLUMNS = ["corp_fin_v2", "finance_agent", "swebench", "terminal_bench_2_1", "vibe_code_bench"]
ANCHOR_COLUMN = "vals_index"
DERIVED_COLUMNS = ["finance_bucket", "coding_bucket"]
FACTOR_COLUMNS = [*TASK_COLUMNS, *DERIVED_COLUMNS]


def _parse_rate(source: pd.Series, parsed: pd.Series) -> float:
    non_null = int(source.notna().sum())
    parsed_non_null = int(parsed.notna().sum())
    return 1.0 if non_null == 0 else parsed_non_null / non_null


def _relationship_extras(sample: pd.DataFrame, target_column: str) -> dict[str, object]:
    # Multi-factor headline: Elo correlation for the composite anchor plus each component task and
    # each weighted bucket, so no single sub-benchmark silently drives the conclusion.
    task_relationships = []
    for column in FACTOR_COLUMNS:
        if column not in sample.columns:
            continue
        relationship = named_corr(f"{column}_vs_elo", sample[column], sample["elo"])
        relationship["factor"] = column
        task_relationships.append(relationship)
    return {
        "bootstrap_95": bootstrap_corr(sample[target_column], sample["elo"]),
        "vals_task_vs_elo": task_relationships,
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
        # Vals states an effort tier per row in reasoning_effort (most vendors) or compute_effort
        # (Anthropic), which is stronger tier evidence than the other evals carry. Surface how much
        # of the snapshot actually states one, since the mapping's clause choice depends on it.
        "stated_effort_counts": {
            key: int(value)
            for key, value in normalized["stated_effort"]
            .fillna("unstated")
            .value_counts()
            .sort_index()
            .items()
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

    # Per-task release-controlled Elo: does each component still track Elo once the linear
    # release-month trend is removed from both sides?
    task_release_controlled = []
    for column in FACTOR_COLUMNS:
        if column not in elo_sample.columns or "release_month_index" not in elo_sample.columns:
            continue
        partial = partial_corr_release_month(elo_sample[column], elo_sample["elo"], elo_sample["release_month_index"])
        task_release_controlled.append({"factor": column, "partial_release_month": partial})

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
                **named_corr(f"vals_index_vs_elo_{label}", sample[config.target_score_column], sample["elo"]),
            }
        )
    return {
        "vals_task_release_controlled": task_release_controlled,
        "mapping_status": status_sensitivity,
        "min_total_games": standard_game_threshold_sensitivity(config, context),
    }


CONFIG = EvalAnalysisConfig(
    eval_id=EVAL_ID,
    eval_label=EVAL_LABEL,
    summary_tagline="Vals Index v1.2 weighted finance-and-coding composite normalized through the shared cross-ref contracts.",
    target_score_column=ANCHOR_COLUMN,
    prediction_target="Vals Index v1.2 score",
    repo_root=REPO_ROOT,
    source_note_path=SOURCE_NOTE_PATH,
    default_source_path=SOURCE_PATH,
    default_mapping_path=CROSS_REF_ROOT / "mappings" / "vals_index.csv",
    mapping_basis="Run-time source of truth is the mapping CSV. For the Vals Index it is a reviewed row-level mapping from the leaderboard's own provider/slug model_key into the current LLM Chess inventory; most rows state an effort tier (reasoning_effort, or compute_effort for Anthropic), so the reasoning-effort rule usually resolves by exact match or by direction-aware nearest-tier rather than by assumption.",
    source_seed_column=None,
    fresh_review_status="mapping-csv-reviewed",
    relationship_name="vals_index_vs_elo",
    accepted_row_filter=_accepted_row_filter,
    relationship_extras=_relationship_extras,
    coverage_extras=_coverage_extras,
    coverage_output_transform=_coverage_output_transform,
    sensitivity_builder=_sensitivity,
    limitations=[
        "Source is an undocumented Astro props blob embedded in https://www.vals.ai/benchmarks/vals_index, not a published data file; Vals offers no CSV, JSON API, or sitemap, so the retrieval path can break without notice.",
        "The snapshot is pinned to Vals Index v1.2. The composite's definition changed three times in 2026 (Terminal-Bench 2.1 swap, Finance Agent v2, Vibe Code Bench added and the Law/CaseLaw sector dropped with the denominator rebalanced 3.7 to 3.4), so scores are not comparable across index versions.",
        "The index measures weighted finance and coding task performance, not broad capability, and can diverge from chess Elo.",
        "The payload carries no display-name field, so model identity is keyed on the provider/slug model_key; model_slug is derived from it mechanically and is presentational only.",
        "vals_index is the framework anchor; the reported result is the Elo correlation profile across the composite plus its five component tasks and two weighted buckets, not a single sub-benchmark.",
        "The matched sample is small (17 of 40 rows), so correlations are exploratory and a single row can move them materially.",
    ],
)


def normalize_source(source_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    actual_source_path = source_path or SOURCE_PATH
    raw = pd.read_csv(actual_source_path)
    normalized = raw.reset_index(names="source_row_index").copy()
    normalized["eval_id"] = EVAL_ID
    normalized["eval_row_id"] = normalized.apply(
        lambda row: f"{EVAL_ID}:{row['source_row_index']:04d}:{slugify_label(row['model_key'])}",
        axis=1,
    )
    normalized["eval_model_label"] = normalized["model_key"].astype(str).str.strip()
    normalized["eval_variant_label"] = normalized["eval_model_label"]
    normalized["provider"] = normalized["provider"].astype(str).str.strip()
    for column in [ANCHOR_COLUMN, *TASK_COLUMNS]:
        normalized[column] = raw[column].map(safe_float)
    normalized["finance_bucket"] = normalized[["corp_fin_v2", "finance_agent"]].mean(axis=1, skipna=False)
    normalized["coding_bucket"] = (
        0.25 * normalized["swebench"] + 0.25 * normalized["terminal_bench_2_1"] + 0.5 * normalized["vibe_code_bench"]
    )
    # Vals records the effort tier in reasoning_effort for most vendors and in compute_effort for
    # Anthropic rows; neither column alone tells you whether a row stated one.
    normalized["stated_effort"] = raw["reasoning_effort"].fillna(raw["compute_effort"])
    normalized["score_numeric"] = normalized[ANCHOR_COLUMN]
    normalized["score_label"] = "Vals Index v1.2"
    contract = summarize_input_contract(
        df=raw,
        file_path=actual_source_path,
        required_columns=["model_key", "provider", ANCHOR_COLUMN, *TASK_COLUMNS],
        key_column="model_key",
        numeric_columns=[],
    )
    contract["numeric_parse_rates"] = {
        column: _parse_rate(raw[column], normalized[column]) for column in [ANCHOR_COLUMN, *TASK_COLUMNS]
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
