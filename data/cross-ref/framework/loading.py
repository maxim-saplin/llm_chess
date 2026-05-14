from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from framework.data_quality import apply_elo_data_quality_overrides


def clean_key_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        return
    df[column] = df[column].astype(str).str.strip()
    df[column] = df[column].replace({"": np.nan, "nan": np.nan, "NaN": np.nan})


def summarize_input_contract(
    *,
    df: pd.DataFrame,
    file_path: Path,
    required_columns: list[str],
    key_column: str | None,
    numeric_columns: list[str] | None = None,
    optional_columns: list[str] | None = None,
) -> dict[str, object]:
    numeric_columns = numeric_columns or []
    optional_columns = optional_columns or []
    missing_required_columns = [column for column in required_columns if column not in df.columns]
    if missing_required_columns:
        raise ValueError(
            f"{file_path} is missing required columns: {', '.join(missing_required_columns)}"
        )

    duplicate_keys = 0
    key_non_null = None
    if key_column:
        key_non_null = int(df[key_column].notna().sum())
        duplicate_keys = int(df[key_column].dropna().duplicated().sum())

    numeric_parse_rates = {}
    for column in numeric_columns:
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        non_null = int(df[column].notna().sum())
        parsed = int(numeric_series.notna().sum())
        numeric_parse_rates[column] = 1.0 if non_null == 0 else parsed / non_null

    optional_present = {column: column in df.columns for column in optional_columns}
    return {
        "file": str(file_path),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "required_columns": required_columns,
        "optional_columns_present": optional_present,
        "key_column": key_column,
        "key_non_null": key_non_null,
        "duplicate_keys": duplicate_keys,
        "numeric_parse_rates": numeric_parse_rates,
    }


def load_llm_chess_inputs(repo_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    elo_path = repo_root / "data" / "elo_refined.csv"
    metadata_path = repo_root / "data" / "models_metadata.csv"

    elo = pd.read_csv(elo_path)
    metadata = pd.read_csv(metadata_path)

    clean_key_column(elo, "Player")
    clean_key_column(metadata, "model")

    elo["elo"] = pd.to_numeric(elo["elo"], errors="coerce")
    elo["elo_moe_95"] = pd.to_numeric(elo["elo_moe_95"], errors="coerce")
    elo["total_games"] = pd.to_numeric(elo["total_games"], errors="coerce")
    metadata["date_released"] = metadata["date_released"].astype(str).str.strip()
    elo, data_quality = apply_elo_data_quality_overrides(elo)

    elo_contract = summarize_input_contract(
        df=elo,
        file_path=elo_path,
        required_columns=[
            "Player",
            "elo",
            "elo_moe_95",
            "total_games",
            "player_wins_percent",
            "player_draws_percent",
            "games_interrupted_percent",
            "wrong_moves_per_1000moves",
            "mistakes_per_1000moves",
            "average_moves",
            "average_time_per_game_seconds",
            "average_game_cost",
            "completion_tokens_black_per_move",
            "material_diff_player_llm_minus_opponent",
        ],
        key_column="Player",
        numeric_columns=[
            "elo",
            "elo_moe_95",
            "total_games",
            "average_game_cost",
            "average_time_per_game_seconds",
        ],
    )
    metadata_contract = summarize_input_contract(
        df=metadata,
        file_path=metadata_path,
        required_columns=[
            "model",
            "1m_prompt",
            "1m_completion",
            "date_released",
            "reasoning_status",
            "comment",
        ],
        key_column="model",
        numeric_columns=["1m_prompt", "1m_completion"],
    )

    elo_players = set(elo["Player"].dropna())
    metadata_models = set(metadata["model"].dropna())
    join_overlap = elo_players & metadata_models
    contract = {
        "elo_refined": elo_contract,
        "models_metadata": metadata_contract,
        "join_coverage": {
            "elo_players": int(len(elo_players)),
            "metadata_models": int(len(metadata_models)),
            "joined_models": int(len(join_overlap)),
            "elo_without_metadata": int(len(elo_players - metadata_models)),
            "metadata_without_elo": int(len(metadata_models - elo_players)),
        },
        "data_quality": data_quality,
    }
    return elo, metadata, contract