from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework.model_identity import infer_provider_or_family

MAPPING_COLUMNS = [
    "eval_id",
    "eval_row_id",
    "eval_model_label",
    "llm_chess_player",
    "eval_variant_label",
    "mapping_status",
    "review_status",
    "confidence",
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
]
OPTIONAL_MAPPING_COLUMNS = ["source_llm_chess_model"]
ACCEPTED_MAPPING_STATUSES = {"accepted", "alias", "variant-compatible"}


def preferred_mapping_columns(columns: list[str]) -> list[str]:
    preferred = [column for column in MAPPING_COLUMNS if column in columns]
    preferred.extend(column for column in OPTIONAL_MAPPING_COLUMNS if column in columns)
    preferred.extend(column for column in columns if column not in preferred)
    return preferred


def reorder_mapping_columns(mapping: pd.DataFrame) -> pd.DataFrame:
    return mapping.loc[:, preferred_mapping_columns(list(mapping.columns))]


def load_mapping_file(mapping_path: Path) -> pd.DataFrame:
    mapping = pd.read_csv(mapping_path)
    missing_columns = [column for column in MAPPING_COLUMNS if column not in mapping.columns]
    if missing_columns:
        raise ValueError(
            f"{mapping_path} is missing required mapping columns: {', '.join(missing_columns)}"
        )
    return reorder_mapping_columns(mapping)


def apply_mapping(normalized: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    duplicate_eval_rows = mapping["eval_row_id"].duplicated(keep=False)
    if duplicate_eval_rows.any():
        duplicates = sorted(mapping.loc[duplicate_eval_rows, "eval_row_id"].unique())
        raise ValueError(f"Mapping file contains duplicate eval_row_id values: {duplicates[:10]}")
    merged = normalized.merge(
        mapping,
        on=["eval_id", "eval_row_id", "eval_model_label", "eval_variant_label"],
        how="left",
        suffixes=("", "_mapping"),
    )
    return merged


def summarize_mapping(
    merged: pd.DataFrame,
    *,
    score_column: str,
    qa_verdict: str | None = None,
) -> dict[str, object]:
    status_counts = (
        merged["mapping_status"].fillna("missing").value_counts().sort_index().to_dict()
        if "mapping_status" in merged.columns
        else {}
    )
    review_counts = (
        merged["review_status"].fillna("missing").value_counts().sort_index().to_dict()
        if "review_status" in merged.columns
        else {}
    )
    unresolved = merged[
        merged["mapping_status"].fillna("missing").isin(["ambiguous", "unmatched", "excluded", "missing"])
    ].copy()
    unresolved = unresolved.sort_values(score_column, ascending=False, na_position="last")
    unresolved_rows = unresolved[
        [
            "eval_row_id",
            "eval_model_label",
            score_column,
            "mapping_status",
            "confidence",
            "open_questions",
        ]
    ].head(15)
    unresolved_rows = unresolved_rows.where(pd.notna(unresolved_rows), None)
    return {
        "mapping_file_status_counts": {key: int(value) for key, value in status_counts.items()},
        "mapping_review_status_counts": {key: int(value) for key, value in review_counts.items()},
        "accepted_count": int(merged["mapping_status"].isin(ACCEPTED_MAPPING_STATUSES).sum()),
        "ambiguous_count": int((merged["mapping_status"] == "ambiguous").sum()),
        "unmatched_count": int((merged["mapping_status"] == "unmatched").sum()),
        "excluded_count": int((merged["mapping_status"] == "excluded").sum()),
        "qa_verdict": qa_verdict or "pending",
        "unresolved_high_impact_rows": unresolved_rows.to_dict(orient="records"),
    }


def seed_eci_mapping(normalized: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    inventory_lookup = inventory.set_index("llm_chess_player")
    rows = []
    for row in normalized.itertuples(index=False):
        llm_chess_player = row.source_llm_chess_model if pd.notna(row.source_llm_chess_model) else ""
        provider_or_family, _ = infer_provider_or_family(row.eval_model_label)
        inventory_row = inventory_lookup.loc[llm_chess_player] if llm_chess_player and llm_chess_player in inventory_lookup.index else None
        rows.append(
            {
                "eval_id": row.eval_id,
                "eval_row_id": row.eval_row_id,
                "eval_model_label": row.eval_model_label,
                "eval_variant_label": row.eval_variant_label,
                "llm_chess_player": llm_chess_player,
                "mapping_status": "accepted" if llm_chess_player else "unmatched",
                "confidence": "seed-medium" if llm_chess_player else "low",
                "provider_or_family": provider_or_family,
                "version_or_release_clue": "legacy_bridge_column",
                "reasoning_or_system_config": "",
                "eval_reasoning_kind": "unknown",
                "eval_reasoning_effort": "",
                "llm_chess_reasoning_kind": "" if inventory_row is None else str(inventory_row.get("reasoning_kind_inferred", "")),
                "llm_chess_reasoning_effort": "" if inventory_row is None else str(inventory_row.get("reasoning_effort_inferred", "")),
                "reasoning_rule_applied": "",
                "evidence_refs": "legacy_source_column:llm_chess_model",
                "rationale": "Generated from the legacy ECI bridge-column workflow and retained as the published reviewed mapping source of truth.",
                "open_questions": "" if llm_chess_player else "No legacy bridge value present.",
                "reviewer": "orchestrator",
                "review_status": "qa_passed",
                "source_llm_chess_model": row.source_llm_chess_model,
            }
        )
    return reorder_mapping_columns(pd.DataFrame(rows))