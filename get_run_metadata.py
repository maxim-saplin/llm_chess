import json
import os
import platform
from typing import Any, Dict, List, Optional
from enum import Enum

import llm_chess

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enum_to_string(value: Any) -> Any:
    """Convert Enum values to their name strings, leave the rest untouched."""
    if isinstance(value, Enum):
        return value.name
    return value


def _sanitize_config_list_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a single provider config entry with sensitive fields redacted."""
    entry = entry.copy()
    # Redact API keys and potentially sensitive headers
    if "api_key" in entry:
        entry["api_key"] = "REDACTED"
    # Default headers may contain keys – just drop them for simplicity
    entry.pop("default_headers", None)
    return entry


_HYPERPARAM_KEYS = [
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "frequency_penalty",
    "presence_penalty",
]
_PROVIDER_KEYS = [
    "model",
    "api_type",
    "api_version",
    "max_tokens",
]


def _simplify_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the autogen-style config into a more readable subset per spec."""
    simplified: Dict[str, Any] = {}

    # Provider-level information (model, api_type, etc.)
    provider_conf = config.get("config_list", [{}])[0]
    provider_conf = _sanitize_config_list_entry(provider_conf)

    for key in _PROVIDER_KEYS:
        if key in provider_conf and provider_conf[key] is not None:
            simplified[key] = provider_conf[key]

    # Always include api_key redacted if present
    if "api_key" in provider_conf:
        simplified["api_key"] = provider_conf["api_key"]

    # Timing / misc top-level keys
    if "timeout" in config and config["timeout"] is not None:
        simplified["timeout"] = config["timeout"]

    # Thinking budget is nested inside the "thinking" dict for Anthropic conf
    if "thinking" in config and isinstance(config["thinking"], dict):
        budget = config["thinking"].get("budget_tokens")
        if budget is not None:
            simplified["thinking_budget"] = budget

    # Reasoning effort should come from provider-level section only
    if "reasoning_effort" in provider_conf and provider_conf["reasoning_effort"] is not None:
        simplified["reasoning_effort"] = provider_conf["reasoning_effort"]

    # Hyper-parameters may also appear at the top level
    for key in _HYPERPARAM_KEYS:
        if key in config and config[key] is not None:
            simplified[key] = config[key]

    # Ensure no stray api_key slipped in
    if "api_key" in simplified:
        simplified["api_key"] = "REDACTED"

    return simplified


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collect_run_metadata(
    *,
    log_folder_relative: str,
    num_repetitions: int,
    store_individual_logs: bool,
    llm_config_white: Optional[Dict[str, Any]] = None,
    llm_config_black: Optional[Dict[str, Any]] = None,
    non_llm_configs_white: Optional[List[Dict[str, Any]]] = None,
    non_llm_configs_black: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Gather a dictionary that matches the _run.json specification."""
    # ---------------------------------------------------------------------
    # Metadata section
    # ---------------------------------------------------------------------
    metadata_section: Dict[str, Any] = {
        "time_started_formatted": llm_chess.time.strftime("%Y.%m.%d_%H:%M"),
        "log_folder_relative": log_folder_relative,
        "num_repetitions": num_repetitions,
        "store_individual_logs": store_individual_logs,
        "python_version": platform.python_version(),
    }

    # ---------------------------------------------------------------------
    # Player types section
    # ---------------------------------------------------------------------
    player_types_section: Dict[str, str] = {
        "white_player_type": _enum_to_string(llm_chess.white_player_type),
        "black_player_type": _enum_to_string(llm_chess.black_player_type),
    }

    # ---------------------------------------------------------------------
    # Config section – a subset of llm_chess global config knobs
    # ---------------------------------------------------------------------
    config_section: Dict[str, Any] = {
        "enable_reflection": llm_chess.enable_reflection,
        "board_representation_mode": _enum_to_string(
            llm_chess.board_representation_mode
        ),
        "rotate_board_for_white": llm_chess.rotate_board_for_white,
        "max_game_moves": llm_chess.max_game_moves,
        "max_llm_turns": llm_chess.max_llm_turns,
        "max_failed_attempts": llm_chess.max_failed_attempts,
        "throttle_delay": llm_chess.throttle_delay,
        "dialog_turn_delay": llm_chess.dialog_turn_delay,
        "max_api_retries": llm_chess.max_api_retries,
        "api_retry_delay": llm_chess.api_retry_delay,
        "random_print_board": llm_chess.random_print_board,
        "visualize_board": llm_chess.visualize_board,
        "remove_text": llm_chess.remove_text,
    }

    # ---------------------------------------------------------------------
    # Chess-engines section – include only when an engine player is involved
    # ---------------------------------------------------------------------
    include_engine_players = any(
        pt in (
            llm_chess.PlayerType.CHESS_ENGINE_STOCKFISH,
            llm_chess.PlayerType.CHESS_ENGINE_DRAGON,
        )
        for pt in (llm_chess.white_player_type, llm_chess.black_player_type)
    )

    chess_engines_section: Optional[Dict[str, Any]] = None
    if include_engine_players:
        chess_engines_section = {
            "stockfish": {
                "path": llm_chess.stockfish_path,
                "reset_history": llm_chess.reset_stockfish_history,
                "level": llm_chess.stockfish_level,
                "time_per_move": llm_chess.stockfish_time_per_move,
            },
            "dragon": {
                "path": llm_chess.dragon_path,
                "reset_history": llm_chess.reset_dragon_history,
                "level": llm_chess.dragon_level,
                "time_per_move": llm_chess.dragon_time_per_move,
            },
        }

    # ---------------------------------------------------------------------
    # LLM configs – include only for sides actually controlled by an LLM
    # ---------------------------------------------------------------------
    llm_configs_section: Dict[str, Any] = {}

    if llm_config_white and llm_chess.white_player_type in (
        llm_chess.PlayerType.LLM_WHITE,
        llm_chess.PlayerType.LLM_NON,
    ):
        llm_configs_section["white"] = _simplify_llm_config(llm_config_white)

    if llm_config_black and llm_chess.black_player_type in (
        llm_chess.PlayerType.LLM_BLACK,
        llm_chess.PlayerType.LLM_NON,
    ):
        llm_configs_section["black"] = _simplify_llm_config(llm_config_black)

    if not llm_configs_section:
        llm_configs_section = None

    # ---------------------------------------------------------------------
    # Non-LLM configs – conditionally included for NoN players
    # ---------------------------------------------------------------------
    include_non_llm = any(
        pt == llm_chess.PlayerType.LLM_NON
        for pt in (llm_chess.white_player_type, llm_chess.black_player_type)
    )

    non_llm_section: Optional[Dict[str, Any]] = None
    if include_non_llm and non_llm_configs_white and non_llm_configs_black:
        non_llm_section = {
            "white": [_simplify_llm_config(cfg) for cfg in non_llm_configs_white],
            "black": [_simplify_llm_config(cfg) for cfg in non_llm_configs_black],
        }

    # ---------------------------------------------------------------------
    # Assemble final structure
    # ---------------------------------------------------------------------
    run_metadata: Dict[str, Any] = {
        "metadata": metadata_section,
        "player_types": player_types_section,
        "config": config_section,
    }

    if chess_engines_section is not None:
        run_metadata["chess_engines"] = chess_engines_section

    if llm_configs_section is not None:
        run_metadata["llm_configs"] = llm_configs_section

    if non_llm_section is not None:
        run_metadata["non_llm_configs"] = non_llm_section

    return run_metadata


def write_run_metadata(metadata: Dict[str, Any], path: str):
    """Write the metadata JSON file once. If the file exists already, skip."""
    if os.path.exists(path):
        # Do not overwrite
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

