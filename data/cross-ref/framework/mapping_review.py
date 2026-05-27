from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework.mapping import load_mapping_file, preferred_mapping_columns
from framework.provider_groups import (
    canonicalize_provider_filter,
    derive_provider_group,
    load_inventory_provider_lookup,
)

UNRESOLVED_MAPPING_STATUSES = {"ambiguous", "unmatched", "excluded", "missing"}
REVIEW_OUTPUT_COLUMNS = [
    "eval_id",
    "mapping_file",
    "eval_row_id",
    "eval_model_label",
    "llm_chess_player",
    "eval_variant_label",
    "mapping_status",
    "review_status",
    "confidence",
    "provider_group",
    "provider_group_source",
    "provider_group_confidence",
    "provider_or_family",
    "version_or_release_clue",
    "reasoning_or_system_config",
    "eval_reasoning_kind",
    "eval_reasoning_effort",
    "llm_chess_reasoning_kind",
    "llm_chess_reasoning_effort",
    "reasoning_rule_applied",
    "evidence_refs",
    "rationale",
    "open_questions",
    "reviewer",
    "source_llm_chess_model",
]


def _join_unique(values: pd.Series) -> str:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique_values.append(text)
    return " | ".join(sorted(unique_values, key=str.casefold))


def _normalize_status_filters(statuses: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for status in statuses or []:
        for piece in str(status).split(","):
            value = piece.strip().lower()
            if value:
                normalized.append(value)
    return sorted(set(normalized))


def _review_output_columns(columns: list[str]) -> list[str]:
    preferred = [column for column in REVIEW_OUTPUT_COLUMNS if column in columns]
    preferred.extend(column for column in preferred_mapping_columns(columns) if column not in preferred)
    preferred.extend(column for column in columns if column not in preferred)
    return preferred


def load_mapping_review_rows(mappings_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for mapping_path in sorted(mappings_dir.glob("*.csv")):
        mapping = load_mapping_file(mapping_path).copy()
        mapping["mapping_file"] = mapping_path.name
        frames.append(mapping)
    if not frames:
        return pd.DataFrame(columns=_review_output_columns(REVIEW_OUTPUT_COLUMNS))
    rows = pd.concat(frames, ignore_index=True)
    inventory_provider_lookup = load_inventory_provider_lookup(
        mappings_dir.parent / "model-identity" / "llm_chess_models.csv"
    )
    provider_groups = rows.apply(derive_provider_group, axis=1, result_type="expand", args=(inventory_provider_lookup,))
    rows = pd.concat([rows, provider_groups], axis=1)
    return rows.loc[:, _review_output_columns(list(rows.columns))]


def filter_mapping_review_rows(
    rows: pd.DataFrame,
    *,
    eval_id: str | None = None,
    player: str | None = None,
    statuses: list[str] | None = None,
    provider: str | None = None,
) -> pd.DataFrame:
    filtered = rows.copy()
    if eval_id:
        filtered = filtered.loc[filtered["eval_id"].fillna("").str.casefold() == eval_id.casefold()]
    if player:
        filtered = filtered.loc[
            filtered["llm_chess_player"].fillna("").str.contains(player, case=False, na=False)
        ]
    normalized_statuses = _normalize_status_filters(statuses)
    if normalized_statuses:
        filtered = filtered.loc[
            filtered["mapping_status"].fillna("missing").str.casefold().isin(normalized_statuses)
        ]
    if provider:
        canonical_provider = canonicalize_provider_filter(provider)
        filtered = filtered.loc[
            filtered["provider_group"].fillna("").str.casefold() == (canonical_provider or "").casefold()
        ]
    filtered = filtered.assign(
        _llm_chess_player_sort=filtered["llm_chess_player"].fillna("zzzzzzzzzz"),
        _llm_chess_player_missing=filtered["llm_chess_player"].fillna("").eq(""),
    )
    filtered = filtered.sort_values(
        [
            "_llm_chess_player_missing",
            "_llm_chess_player_sort",
            "eval_id",
            "mapping_status",
            "eval_model_label",
        ],
        na_position="last",
    )
    return filtered.drop(columns=["_llm_chess_player_sort", "_llm_chess_player_missing"])


def _build_player_matrix_rows(rows: pd.DataFrame) -> list[dict[str, object]]:
    player_rows = rows.loc[rows["llm_chess_player"].fillna("") != ""].copy()
    if player_rows.empty:
        return []
    eval_ids = sorted(player_rows["eval_id"].dropna().unique())
    matrix_rows: list[dict[str, object]] = []
    for llm_chess_player, group in player_rows.groupby("llm_chess_player", sort=True):
        row: dict[str, object] = {
            "llm_chess_player": llm_chess_player,
            "eval_count": int(group["eval_id"].nunique()),
            "eval_ids": _join_unique(group["eval_id"]),
            "mapping_statuses": _join_unique(group["mapping_status"]),
            "providers": _join_unique(group["provider_group"]),
            "source_models": _join_unique(group["eval_model_label"]),
        }
        for eval_id in eval_ids:
            eval_group = group.loc[group["eval_id"] == eval_id]
            row[f"{eval_id}_status"] = _join_unique(eval_group["mapping_status"])
            row[f"{eval_id}_source_models"] = _join_unique(eval_group["eval_model_label"])
        matrix_rows.append(row)
    return matrix_rows


def build_mapping_review(
    mappings_dir: Path,
    *,
    eval_id: str | None = None,
    player: str | None = None,
    statuses: list[str] | None = None,
    provider: str | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    all_rows = load_mapping_review_rows(mappings_dir)
    filtered = filter_mapping_review_rows(
        all_rows,
        eval_id=eval_id,
        player=player,
        statuses=statuses,
        provider=provider,
    )
    unresolved = filtered.loc[
        filtered["mapping_status"].fillna("missing").isin(UNRESOLVED_MAPPING_STATUSES)
    ].copy()
    status_counts = (
        filtered["mapping_status"].fillna("missing").value_counts().sort_index().to_dict()
        if "mapping_status" in filtered.columns
        else {}
    )
    review_status_counts = (
        filtered["review_status"].fillna("missing").value_counts().sort_index().to_dict()
        if "review_status" in filtered.columns
        else {}
    )
    eval_counts = (
        filtered["eval_id"].fillna("missing").value_counts().sort_index().to_dict()
        if "eval_id" in filtered.columns
        else {}
    )
    provider_counts = (
        filtered["provider_group"].fillna("missing").value_counts().sort_index().to_dict()
        if "provider_group" in filtered.columns
        else {}
    )
    serializable_rows = filtered.where(pd.notna(filtered), None)
    serializable_unresolved = unresolved.where(pd.notna(unresolved), None)
    payload = {
        "filters": {
            "eval_id": eval_id,
            "player": player,
            "status": _normalize_status_filters(statuses),
            "provider": provider,
        },
        "summary": {
            "row_count": int(len(filtered)),
            "eval_count": int(filtered["eval_id"].nunique()) if not filtered.empty else 0,
            "unique_llm_chess_players": int(
                filtered.loc[filtered["llm_chess_player"].fillna("") != "", "llm_chess_player"].nunique()
            )
            if not filtered.empty
            else 0,
            "unresolved_row_count": int(len(unresolved)),
        },
        "status_counts": {key: int(value) for key, value in status_counts.items()},
        "review_status_counts": {key: int(value) for key, value in review_status_counts.items()},
        "eval_counts": {key: int(value) for key, value in eval_counts.items()},
        "provider_counts": {key: int(value) for key, value in provider_counts.items()},
        "player_matrix_rows": _build_player_matrix_rows(filtered),
        "unresolved_rows": serializable_unresolved.to_dict(orient="records"),
        "review_rows": serializable_rows.to_dict(orient="records"),
    }
    return filtered, payload