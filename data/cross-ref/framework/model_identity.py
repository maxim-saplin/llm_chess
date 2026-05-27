from __future__ import annotations

import re

import pandas as pd


INVENTORY_COLUMNS = [
    "llm_chess_player",
    "review_status",
    "provider_or_family",
    "date_released",
    "reasoning_status",
    "reasoning_kind_inferred",
    "reasoning_effort_inferred",
]


def infer_provider_or_family(label: object) -> tuple[str, str]:
    raw = "" if label is None else str(label).strip()
    if not raw:
        return "unknown", "unknown"
    if "." in raw:
        prefix = raw.split(".", 1)[0].strip()
        if prefix:
            return prefix, "dot_prefix"
    family = re.split(r"[-_@:|\s]+", raw, maxsplit=1)[0].strip()
    return family or raw, "leading_token"


def infer_reasoning_kind(label: object, reasoning_status: object) -> str:
    reasoning_text = "" if reasoning_status is None else str(reasoning_status).strip().lower()
    label_text = "" if label is None else str(label).strip().lower()
    if reasoning_text in {"reasoning", "thinking"}:
        return "reasoning"
    if reasoning_text in {"not_reasoning", "non_reasoning", "base"}:
        return "not_reasoning"
    if any(token in label_text for token in ["thinking", "reasoning", "_high", "_medium", "_low", "_max", "xhigh"]):
        return "reasoning"
    return "unknown"


def infer_reasoning_effort(label: object) -> str:
    text = "" if label is None else str(label).strip().lower()
    for marker in ["xhigh", "max", "high", "medium", "low"]:
        if marker in text:
            return marker
    thinking_match = re.search(r"thinking[_-]?(\d+)", text)
    if thinking_match:
        return f"thinking_{thinking_match.group(1)}"
    return ""


def build_llm_chess_inventory(elo: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    elo_inventory = elo[["Player"]].copy().rename(columns={"Player": "llm_chess_player"})
    metadata_inventory = metadata[["model", "date_released", "reasoning_status"]].copy().rename(
        columns={"model": "llm_chess_player"}
    )

    merged = elo_inventory.merge(
        metadata_inventory,
        on="llm_chess_player",
        how="outer",
        suffixes=("", "_metadata"),
        indicator=True,
    )
    merged["provider_or_family"], merged["provider_or_family_method"] = zip(
        *(infer_provider_or_family(value) for value in merged["llm_chess_player"]),
        strict=False,
    )
    merged["reasoning_kind_inferred"] = [
        infer_reasoning_kind(label, status)
        for label, status in zip(merged["llm_chess_player"], merged.get("reasoning_status"), strict=False)
    ]
    merged["reasoning_effort_inferred"] = [infer_reasoning_effort(value) for value in merged["llm_chess_player"]]
    merged["review_status"] = merged["_merge"].map(
        {
            "both": "exact-match",
            "left_only": "elo-only",
            "right_only": "metadata-only",
        }
    )
    existing_columns = [column for column in INVENTORY_COLUMNS if column in merged.columns]
    return merged[existing_columns].sort_values("llm_chess_player", na_position="last").reset_index(drop=True)


def inventory_summary(inventory: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(len(inventory)),
        "elo_only": int((inventory["review_status"] == "elo-only").sum()),
        "metadata_only": int((inventory["review_status"] == "metadata-only").sum()),
        "exact_match": int((inventory["review_status"] == "exact-match").sum()),
    }