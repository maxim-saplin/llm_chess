from __future__ import annotations

import numpy as np
import pandas as pd

GROK_INVALID_TOKEN_AND_COST_COLUMNS = (
    "completion_tokens_black_per_move",
    "moe_completion_tokens_black_per_move",
    "average_game_cost",
    "moe_average_game_cost",
    "price_per_1000_moves",
    "moe_price_per_1000_moves",
)

# Logs before this date underreported wrong actions and wrong moves. Models whose earliest LLM Chess
# game (elo_refined.csv `min_game_date`) is on/after this date have trustworthy error metrics.
# This is the single source of truth for the cutoff; everything else reads it.
MISTAKE_STATS_TRUSTED_AFTER = "2025-03-16"

# Historical logs before MISTAKE_STATS_TRUSTED_AFTER underreported wrong actions and wrong moves.
# These metrics are excluded from analysis by default. They can be re-enabled only on a sample
# restricted to models stamped clean (min_game_date >= cutoff); see clean_mistake_stats_mask and the
# eval analysis `mistake_stats="clean_only"` mode. We never repair individual models — we drop the
# pre-cutoff ones wholesale, since the aggregate rows cannot be safely recomputed per model.
HISTORICALLY_TAINTED_MULTIFACTOR_METRICS = (
    "player_wrong_actions",
    "player_wrong_moves",
    "wrong_actions_per_1000moves",
    "wrong_moves_per_1000moves",
    "mistakes_per_1000moves",
    "moe_mistakes_per_1000moves",
)

# The error/discipline rate metrics analysis can use once the sample is restricted to clean models.
REPAIRABLE_MISTAKE_METRICS = (
    "wrong_actions_per_1000moves",
    "wrong_moves_per_1000moves",
    "mistakes_per_1000moves",
)


def clean_mistake_stats_mask(elo: pd.DataFrame, *, cutoff: str = MISTAKE_STATS_TRUSTED_AFTER) -> pd.Series:
    """Boolean mask of elo rows whose earliest game ran on/after the cutoff.

    Rows with a missing/blank ``min_game_date`` are treated as NOT clean (dropped), because we cannot
    vouch for when those games ran.
    """
    if "min_game_date" not in elo.columns:
        return pd.Series(False, index=elo.index)
    stamped = elo["min_game_date"].astype(str).str.strip()
    return stamped.ne("") & stamped.ne("nan") & (stamped >= cutoff)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def filter_multifactor_candidate_metrics(
    candidate_metrics: list[str] | None,
    allowed_repaired: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[str], list[str]]:
    """Split candidates into kept/excluded, dropping historically tainted metrics.

    Metrics in ``allowed_repaired`` are exempt from exclusion: callers pass these only when the
    analysis sample has been restricted to models stamped clean (min_game_date >= cutoff), so the
    metric values are trustworthy for that sample.
    """
    filtered: list[str] = []
    excluded: list[str] = []
    for metric in candidate_metrics or []:
        if metric in HISTORICALLY_TAINTED_MULTIFACTOR_METRICS and metric not in allowed_repaired:
            excluded.append(metric)
            continue
        filtered.append(metric)
    return _ordered_unique(filtered), _ordered_unique(excluded)


def apply_elo_data_quality_overrides(elo: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    adjusted = elo.copy()
    player_labels = adjusted["Player"].fillna("").astype(str)
    grok_mask = player_labels.str.startswith("grok-")

    grok_mask_counts: dict[str, int] = {}
    for column in GROK_INVALID_TOKEN_AND_COST_COLUMNS:
        if column not in adjusted.columns:
            continue
        grok_mask_counts[column] = int((grok_mask & adjusted[column].notna()).sum())
        adjusted.loc[grok_mask, column] = np.nan

    quality_summary = {
        "row_level_masks": [
            {
                "rule_id": "grok_token_and_cost_metrics_masked",
                "scope": "row_level",
                "reason": "Grok token accounting is not comparable across models, so token and derived cost metrics are masked for analysis instead of treated as real zeros.",
                "row_selector": "Player startswith 'grok-'",
                "affected_row_count": int(grok_mask.sum()),
                "masked_columns": list(GROK_INVALID_TOKEN_AND_COST_COLUMNS),
                "masked_non_null_counts": grok_mask_counts,
            }
        ],
        "global_multifactor_metric_exclusions": [
            {
                "rule_id": "historical_wrong_action_metrics_excluded",
                "scope": "global_metric_exclusion",
                "reason": "Logs before 2025-03-16 underreported wrong actions and wrong moves, and the aggregate elo_refined.csv rows do not preserve enough run-date provenance to repair those metrics safely inside multifactor analysis.",
                "metric_columns": list(HISTORICALLY_TAINTED_MULTIFACTOR_METRICS),
            }
        ],
    }
    return adjusted, quality_summary