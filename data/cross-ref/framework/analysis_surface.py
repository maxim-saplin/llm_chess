from __future__ import annotations

import pandas as pd

from framework.mapping import ACCEPTED_MAPPING_STATUSES
from framework.statistics import add_release_month_columns

NUMERIC_STAGE_ID = "numeric_external_eval_rows"
ACCEPTED_STAGE_ID = "accepted_mapping_rows"
JOINED_METRIC_STAGE_ID = "rows_joined_to_llm_chess_metric_rows"
METRIC_STAGE_ID = "metric_analysis_rows_max_dedupe"
JOINED_ELO_STAGE_ID = "rows_joined_to_llm_chess_rows_with_non_null_elo"
ELO_STAGE_ID = "elo_analysis_rows_max_dedupe"


def dedupe_rows_by_player(rows: pd.DataFrame, *, score_column: str, method: str) -> pd.DataFrame:
    if method == "max":
        return (
            rows.sort_values(["llm_chess_player", score_column, "eval_row_id"], ascending=[True, False, True])
            .drop_duplicates("llm_chess_player", keep="first")
            .reset_index(drop=True)
        )
    if method == "min":
        return (
            rows.sort_values(["llm_chess_player", score_column, "eval_row_id"], ascending=[True, True, True])
            .drop_duplicates("llm_chess_player", keep="first")
            .reset_index(drop=True)
        )
    if method in {"mean", "median"}:
        return (
            rows.groupby("llm_chess_player", as_index=False)
            .agg({score_column: method, "eval_model_label": "first"})
            .reset_index(drop=True)
        )
    raise ValueError(f"Unsupported dedupe method: {method}")


def _merge_with_chess_inputs(
    rows: pd.DataFrame,
    chess_rows: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    sample = rows.merge(
        chess_rows,
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


def build_analysis_samples(
    accepted_rows: pd.DataFrame,
    chess_rows: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    score_column: str,
    method: str = "max",
) -> dict[str, object]:
    chess_available = chess_rows.dropna(subset=["Player"]).copy()
    chess_players = set(chess_available["Player"].dropna())
    elo_available = chess_available.dropna(subset=["elo"]).copy()
    elo_players = set(elo_available["Player"].dropna())

    metric_joined_rows = accepted_rows[
        accepted_rows[score_column].notna() & accepted_rows["llm_chess_player"].isin(chess_players)
    ].copy()
    elo_joined_rows = metric_joined_rows[metric_joined_rows["llm_chess_player"].isin(elo_players)].copy()

    metric_analysis_rows = dedupe_rows_by_player(metric_joined_rows, score_column=score_column, method=method)
    elo_analysis_rows = dedupe_rows_by_player(elo_joined_rows, score_column=score_column, method=method)

    return {
        "chess_available": chess_available,
        "chess_players": chess_players,
        "elo_available": elo_available,
        "elo_players": elo_players,
        "metric_joined_rows": metric_joined_rows,
        "metric_analysis_rows": metric_analysis_rows,
        "metric_analysis_sample": _merge_with_chess_inputs(metric_analysis_rows, chess_available, metadata),
        "elo_joined_rows": elo_joined_rows,
        "elo_analysis_rows": elo_analysis_rows,
        "elo_analysis_sample": _merge_with_chess_inputs(elo_analysis_rows, elo_available, metadata),
    }


def build_analysis_surfaces(*, metric_count: int, elo_count: int) -> dict[str, object]:
    return {
        "metric_analysis": {
            "stage_id": METRIC_STAGE_ID,
            "count": int(metric_count),
            "used_by": ["relationships.selected_metrics", "prediction"],
            "description": "Deduped eval rows joined to LLM Chess metric rows, even when Elo is missing.",
        },
        "elo_analysis": {
            "stage_id": ELO_STAGE_ID,
            "count": int(elo_count),
            "used_by": ["relationships.raw_elo", "relationships.release_controlled_elo"],
            "description": "Deduped eval rows joined to LLM Chess players with non-null Elo.",
        },
    }


def build_funnel(
    *,
    numeric_score_rows: int,
    accepted_mapping_rows: int,
    rows_joined_to_any_llm_chess_row: int,
    metric_analysis_rows_max_dedupe: int,
    rows_joined_to_llm_chess_rows_with_non_null_elo: int,
    elo_analysis_rows_max_dedupe: int,
) -> dict[str, object]:
    counts = {
        NUMERIC_STAGE_ID: int(numeric_score_rows),
        ACCEPTED_STAGE_ID: int(accepted_mapping_rows),
        JOINED_METRIC_STAGE_ID: int(rows_joined_to_any_llm_chess_row),
        METRIC_STAGE_ID: int(metric_analysis_rows_max_dedupe),
        JOINED_ELO_STAGE_ID: int(rows_joined_to_llm_chess_rows_with_non_null_elo),
        ELO_STAGE_ID: int(elo_analysis_rows_max_dedupe),
    }
    stage_specs = [
        {
            "stage_id": NUMERIC_STAGE_ID,
            "label": "External eval rows with a numeric score",
            "branch": "base",
            "filter_side": "eval",
            "required_condition": "The eval row has a parsed numeric target score.",
            "previous_stage_id": None,
        },
        {
            "stage_id": ACCEPTED_STAGE_ID,
            "label": "Numeric eval rows with an accepted mapping",
            "branch": "base",
            "filter_side": "mapping",
            "required_condition": "The mapping status is accepted, alias, or variant-compatible, and a LLM Chess player is assigned.",
            "previous_stage_id": NUMERIC_STAGE_ID,
        },
        {
            "stage_id": JOINED_METRIC_STAGE_ID,
            "label": "Accepted eval rows joined to LLM Chess metric rows",
            "branch": "base",
            "filter_side": "chess",
            "required_condition": "The mapped LLM Chess player exists in the current LLM Chess metrics table in data/elo_refined.csv.",
            "previous_stage_id": ACCEPTED_STAGE_ID,
        },
        {
            "stage_id": METRIC_STAGE_ID,
            "label": "Deduped metric-analysis rows",
            "branch": "metric",
            "filter_side": "dedupe",
            "required_condition": "For each LLM Chess player, keep the highest-scoring eval row for metric-only analysis.",
            "previous_stage_id": JOINED_METRIC_STAGE_ID,
        },
        {
            "stage_id": JOINED_ELO_STAGE_ID,
            "label": "Accepted eval rows joined to LLM Chess rows with non-null Elo",
            "branch": "elo",
            "filter_side": "chess",
            "required_condition": "The mapped LLM Chess player exists and has a non-null Elo.",
            "previous_stage_id": JOINED_METRIC_STAGE_ID,
        },
        {
            "stage_id": ELO_STAGE_ID,
            "label": "Deduped Elo-analysis rows",
            "branch": "elo",
            "filter_side": "dedupe",
            "required_condition": "For each Elo-valid LLM Chess player, keep the highest-scoring eval row for Elo analysis.",
            "previous_stage_id": JOINED_ELO_STAGE_ID,
        },
    ]
    stages = []
    for spec in stage_specs:
        previous_stage_id = spec["previous_stage_id"]
        previous_count = counts[spec["stage_id"]] if previous_stage_id is None else counts[previous_stage_id]
        stages.append(
            {
                **spec,
                "count": counts[spec["stage_id"]],
                "dropped_from_previous": int(previous_count - counts[spec["stage_id"]]),
            }
        )
    return {
        "stages": stages,
        "analysis_split_note": {
            "metric_analysis": "Selected metric relationships and prediction use the metric-analysis sample.",
            "elo_analysis": "Raw Elo relationships and release-controlled Elo relationships use the Elo-analysis sample.",
        },
    }


def _build_dedupe_loser_to_winner(rows: pd.DataFrame, *, score_column: str) -> dict[str, str]:
    if rows.empty:
        return {}
    sorted_rows = rows.sort_values(["llm_chess_player", score_column, "eval_row_id"], ascending=[True, False, True])
    loser_to_winner: dict[str, str] = {}
    for _, group in sorted_rows.groupby("llm_chess_player", sort=False):
        winner = str(group.iloc[0]["eval_row_id"])
        for loser_row_id in group.iloc[1:]["eval_row_id"].tolist():
            loser_to_winner[str(loser_row_id)] = winner
    return loser_to_winner


def _mapping_drop_reason(row: pd.Series) -> str:
    status = row.get("mapping_status")
    if pd.isna(status):
        return "No mapping row exists for this eval row."
    if status == "ambiguous":
        return "Mapping status is ambiguous, so this row is excluded until one LLM Chess player is chosen."
    if status == "unmatched":
        return "Mapping status is unmatched, so no LLM Chess player is assigned."
    if status == "excluded":
        return "Mapping status is excluded, so this row is intentionally kept out of model analysis."
    return f"Mapping status '{status}' is not accepted for analysis."


def _metric_branch_drop(row: pd.Series) -> tuple[str | None, str | None, str | None]:
    if not row["has_numeric_score"]:
        return (NUMERIC_STAGE_ID, "eval", "The eval row has no numeric score.")
    if not row["made_accepted_mapping"]:
        return (ACCEPTED_STAGE_ID, "mapping", _mapping_drop_reason(row))
    if not row["joined_llm_chess_metric_row"]:
        return (
            JOINED_METRIC_STAGE_ID,
            "chess",
            "The mapped LLM Chess player is not present in the current LLM Chess metrics table in data/elo_refined.csv.",
        )
    if not row["survived_metric_dedupe"]:
        kept_row_id = row.get("metric_dedupe_kept_eval_row_id")
        return (
            METRIC_STAGE_ID,
            "dedupe",
            f"Another eval row for this LLM Chess player was kept after max-score metric dedupe: {kept_row_id}.",
        )
    return (None, None, None)


def _elo_branch_drop(row: pd.Series) -> tuple[str | None, str | None, str | None]:
    if not row["has_numeric_score"]:
        return (NUMERIC_STAGE_ID, "eval", "The eval row has no numeric score.")
    if not row["made_accepted_mapping"]:
        return (ACCEPTED_STAGE_ID, "mapping", _mapping_drop_reason(row))
    if not row["joined_llm_chess_metric_row"]:
        return (
            JOINED_METRIC_STAGE_ID,
            "chess",
            "The mapped LLM Chess player is not present in the current LLM Chess metrics table in data/elo_refined.csv.",
        )
    if not row["joined_llm_chess_row_with_non_null_elo"]:
        return (
            JOINED_ELO_STAGE_ID,
            "chess",
            "The mapped LLM Chess player exists in the LLM Chess inputs but its Elo is missing.",
        )
    if not row["survived_elo_dedupe"]:
        kept_row_id = row.get("elo_dedupe_kept_eval_row_id")
        return (
            ELO_STAGE_ID,
            "dedupe",
            f"Another eval row for this Elo-valid LLM Chess player was kept after max-score Elo dedupe: {kept_row_id}.",
        )
    return (None, None, None)


def annotate_coverage_rows(
    merged_mapping: pd.DataFrame,
    *,
    score_column: str,
    metric_joined_rows: pd.DataFrame,
    metric_analysis_rows: pd.DataFrame,
    elo_joined_rows: pd.DataFrame,
    elo_analysis_rows: pd.DataFrame,
) -> pd.DataFrame:
    coverage_output = merged_mapping.copy()
    accepted_mapping = (
        coverage_output["mapping_status"].isin(ACCEPTED_MAPPING_STATUSES) & coverage_output["llm_chess_player"].notna()
    )
    coverage_output["has_numeric_score"] = coverage_output[score_column].notna()
    coverage_output["made_accepted_mapping"] = coverage_output["has_numeric_score"] & accepted_mapping

    metric_joined_ids = set(metric_joined_rows["eval_row_id"].astype(str))
    metric_kept_ids = set(metric_analysis_rows["eval_row_id"].astype(str)) if "eval_row_id" in metric_analysis_rows.columns else set()
    elo_joined_ids = set(elo_joined_rows["eval_row_id"].astype(str))
    elo_kept_ids = set(elo_analysis_rows["eval_row_id"].astype(str)) if "eval_row_id" in elo_analysis_rows.columns else set()

    metric_loser_to_winner = _build_dedupe_loser_to_winner(metric_joined_rows, score_column=score_column)
    elo_loser_to_winner = _build_dedupe_loser_to_winner(elo_joined_rows, score_column=score_column)

    coverage_output["joined_llm_chess_metric_row"] = coverage_output["eval_row_id"].astype(str).isin(metric_joined_ids)
    coverage_output["made_metric_sample_pre_dedupe"] = coverage_output["joined_llm_chess_metric_row"]
    coverage_output["survived_metric_dedupe"] = coverage_output["eval_row_id"].astype(str).isin(metric_kept_ids)
    coverage_output["joined_llm_chess_row_with_non_null_elo"] = coverage_output["eval_row_id"].astype(str).isin(elo_joined_ids)
    coverage_output["survived_elo_dedupe"] = coverage_output["eval_row_id"].astype(str).isin(elo_kept_ids)
    coverage_output["metric_dedupe_kept_eval_row_id"] = coverage_output["eval_row_id"].astype(str).map(metric_loser_to_winner)
    coverage_output["elo_dedupe_kept_eval_row_id"] = coverage_output["eval_row_id"].astype(str).map(elo_loser_to_winner)
    coverage_output["has_llm_chess_match"] = coverage_output["joined_llm_chess_metric_row"]
    coverage_output["has_llm_chess_elo"] = coverage_output["joined_llm_chess_row_with_non_null_elo"]

    metric_drop = coverage_output.apply(_metric_branch_drop, axis=1, result_type="expand")
    metric_drop.columns = ["metric_drop_stage", "metric_drop_side", "metric_drop_reason"]
    elo_drop = coverage_output.apply(_elo_branch_drop, axis=1, result_type="expand")
    elo_drop.columns = ["elo_drop_stage", "elo_drop_side", "elo_drop_reason"]
    coverage_output = pd.concat([coverage_output, metric_drop, elo_drop], axis=1)

    stage_rank = {
        NUMERIC_STAGE_ID: 1,
        ACCEPTED_STAGE_ID: 2,
        JOINED_METRIC_STAGE_ID: 3,
        METRIC_STAGE_ID: 4,
        JOINED_ELO_STAGE_ID: 5,
        ELO_STAGE_ID: 6,
    }

    def first_failure(row: pd.Series) -> tuple[str | None, str | None, str | None]:
        failures = []
        if row["metric_drop_stage"] is not None:
            failures.append((row["metric_drop_stage"], row["metric_drop_side"], row["metric_drop_reason"]))
        if row["elo_drop_stage"] is not None:
            failures.append((row["elo_drop_stage"], row["elo_drop_side"], row["elo_drop_reason"]))
        if not failures:
            return (None, None, None)
        return min(failures, key=lambda failure: stage_rank[failure[0]])

    first_failed = coverage_output.apply(first_failure, axis=1, result_type="expand")
    first_failed.columns = ["first_failed_stage", "first_failed_side", "first_failed_reason"]
    coverage_output = pd.concat([coverage_output, first_failed], axis=1)
    return coverage_output