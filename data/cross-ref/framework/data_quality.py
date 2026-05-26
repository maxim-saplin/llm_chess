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

# Historical logs before 2025-03-16 underreported wrong actions and wrong moves.
# The current aggregate elo_refined.csv does not preserve row-level run-date provenance,
# so multifactor analysis must exclude these metrics until provenance is carried through.
HISTORICALLY_TAINTED_MULTIFACTOR_METRICS = (
    "player_wrong_actions",
    "player_wrong_moves",
    "wrong_actions_per_1000moves",
    "wrong_moves_per_1000moves",
    "mistakes_per_1000moves",
    "moe_mistakes_per_1000moves",
)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def filter_multifactor_candidate_metrics(candidate_metrics: list[str] | None) -> tuple[list[str], list[str]]:
    filtered: list[str] = []
    excluded: list[str] = []
    for metric in candidate_metrics or []:
        if metric in HISTORICALLY_TAINTED_MULTIFACTOR_METRICS:
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