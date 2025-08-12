import os
import json
import re
import datetime
import statistics  # Import the statistics module
from typing import Optional, Dict, Tuple
from utils import setup_console_logging, get_llms
from get_run_metadata import collect_run_metadata, write_run_metadata
import llm_chess


# Module-level defaults (allow tests to override)
NUM_REPETITIONS = 33
LOG_FOLDER = None  # If None, computed at runtime; tests may override
STORE_INDIVIDUAL_LOGS = True


def run_games():
    # ---------------------------------------------------------------------------
    # Hyperparameter schema and provider quirks
    # ---------------------------------------------------------------------------
    # Per-side settings passed to get_llms are DICTs with this shape:
    # {
    #   "hyperparams": {                 # Optional. None values are ignored.
    #       "temperature": float | None,
    #       "top_p": float | None,
    #       "top_k": int | None,
    #       "min_p": float | None,
    #       "frequency_penalty": float | None,
    #       "presence_penalty": float | None,
    #   },
    #   "reasoning_effort": str,         # Optional (openai/azure/xai/local only): "low" | "medium" | "high".
    #   "thinking_budget": int,          # Optional (anthropic only). Enables thinking mode with given budget tokens.
    #   "provider_overrides": { ... },   # Optional. Merged into config_list[0] (e.g., base_url, api_version, etc.).
    # }
    #
    # Provider-specific quirks applied by get_llms:
    # - If reasoning_effort is set for provider in (openai, azure, xai, local):
    #   - config["config_list"][0]["reasoning_effort"] = value
    #   - top-level temperature is REMOVED (top_p is kept)
    #
    # - If thinking_budget is set for provider == anthropic:
    #   - config["config_list"][0]["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    #   - top-level temperature and top_p are REMOVED
    #
    # Notes:
    # - Environment variables determine provider base config (model, keys, api_type, etc.).
    # - None-valued hyperparams are skipped and not included in the final config.
    # - White and Black are independent; overrides on one side do not affect the other.
    # - Canonical defaults live in llm_chess.default_hyperparams. We duplicate them below
    #   as experiment-local defaults for clarity and easier tweaking per run.

    # ---------------------------------------------------------------------------
    # Experiment-local default hyper-parameters (duplicated for clarity)
    # ---------------------------------------------------------------------------
    EXPERIMENT_DEFAULT_HYPERPARAMS = {
        "temperature": 0.3,
        "top_p": 1.0,
        "top_k": None,
        "min_p": None,
        "frequency_penalty": None,
        "presence_penalty": None,
    }

    # ---------------------------------------------------------------------------
    # Per-model configuration – edit ONLY these two dicts for experiments
    # ---------------------------------------------------------------------------
    WHITE_HYPERPARAMS = {
        # Start from experiment defaults; adjust as needed per run
        "hyperparams": EXPERIMENT_DEFAULT_HYPERPARAMS.copy(),
        # "reasoning_effort": "high",
        # "thinking_budget": 4096,
    }

    BLACK_HYPERPARAMS = {
        # Start from experiment defaults; adjust as needed per run
        "hyperparams": EXPERIMENT_DEFAULT_HYPERPARAMS.copy(),
        # "reasoning_effort": "low",
    }

    LLM_CONFIG_WHITE, LLM_CONFIG_BLACK = get_llms(
        white_hyperparams=WHITE_HYPERPARAMS,
        black_hyperparams=BLACK_HYPERPARAMS,
    )

    # Pull module-level overrides (NUM_REPETITIONS, STORE_INDIVIDUAL_LOGS)
    global NUM_REPETITIONS, STORE_INDIVIDUAL_LOGS

    llm_chess.throttle_delay = 0
    llm_chess.dialog_turn_delay = 1
    # llm_chess.board_representation_mode = llm_chess.BoardRepresentation.UNICODE_WITH_PGN
    # llm_chess.rotate_board_for_white = True

    ## Regex pattern for removing reasoning sections, such as <think></think>
    llm_chess.remove_text = llm_chess.DEFAULT_REMOVE_TEXT_REGEX

    # llm_chess.dragon_path = "dragon/dragon-linux"
    # llm_chess.dragon_level = 10

    # llm_chess.white_player_type = llm_chess.PlayerType.CHESS_ENGINE_DRAGON
    # llm_chess.black_player_type = llm_chess.PlayerType.LLM_NON

    # Determine LOG_FOLDER lazily to respect external overrides in tests
    global LOG_FOLDER
    if LOG_FOLDER is None:
        LOG_FOLDER = build_log_folder(
            white_player_type=llm_chess.white_player_type,
            black_player_type=llm_chess.black_player_type,
            llm_config_white=LLM_CONFIG_WHITE,
            llm_config_black=LLM_CONFIG_BLACK,
            stockfish_level=llm_chess.stockfish_level,
            dragon_level=llm_chess.dragon_level,
        )

    NON_LLM_CONFIGS_WHITE = [
        {**LLM_CONFIG_WHITE, "temperature": 0.0},
        {**LLM_CONFIG_WHITE, "temperature": 1.0},
    ]
    NON_LLM_CONFIGS_BLACK = [
        {**LLM_CONFIG_BLACK, "temperature": 0.0},
        {**LLM_CONFIG_BLACK, "temperature": 1.0},
    ]

    setup_console_logging(LOG_FOLDER)  # save raw console output to output.txt

    # Create _run.json metadata file (once, before the first game starts)

    _run_metadata = None
    try:
        _run_metadata = collect_run_metadata(
            log_folder_relative=LOG_FOLDER,
            num_repetitions=NUM_REPETITIONS,
            store_individual_logs=STORE_INDIVIDUAL_LOGS,
            llm_config_white=LLM_CONFIG_WHITE,
            llm_config_black=LLM_CONFIG_BLACK,
            non_llm_configs_white=NON_LLM_CONFIGS_WHITE,
            non_llm_configs_black=NON_LLM_CONFIGS_BLACK,
        )
        write_run_metadata(_run_metadata, os.path.join(LOG_FOLDER, "_run.json"))
    except Exception as _meta_err:
        # Do not interrupt the experiment if metadata collection fails
        print(f"[run_metadata] Error: {_meta_err}")
    aggregate_data = {
        # run_metadata will be attached later; initialise as empty dict
        "run_metadata": {},
        "total_games": 0,
        "white_wins": 0,
        "black_wins": 0,
        "draws": 0,
        "total_moves": 0,
        "reasons": {},
        "player_white": {
            "name": "",
            "model": "",
            "total_material": 0,
            "wrong_moves": 0,
            "wrong_actions": 0,
            "material_list": [],
            "reflections_used": 0,
            "reflections_used_before_board": 0,
        },
        "player_black": {
            "name": "",
            "model": "",
            "total_material": 0,
            "wrong_moves": 0,
            "wrong_actions": 0,
            "material_list": [],
            "reflections_used": 0,
            "reflections_used_before_board": 0,
        },
    }

    moves_list = []  # List to track moves for each game

    for _ in range(NUM_REPETITIONS):
        # Call the run function and get the game stats
        game_stats, player_white, player_black = llm_chess.run(
            log_dir=LOG_FOLDER if STORE_INDIVIDUAL_LOGS else None,
            llm_config_white=LLM_CONFIG_WHITE,
            llm_config_black=LLM_CONFIG_BLACK,
            non_llm_configs_white=NON_LLM_CONFIGS_WHITE,
            non_llm_configs_black=NON_LLM_CONFIGS_BLACK,
        )

        moves_list.append(game_stats["number_of_moves"])  # Track moves
        aggregate_data["total_games"] += 1
        aggregate_data["total_moves"] += game_stats["number_of_moves"]

        if game_stats["winner"] == player_white.name:
            aggregate_data["white_wins"] += 1
        elif game_stats["winner"] == player_black.name:
            aggregate_data["black_wins"] += 1
        else:
            aggregate_data["draws"] += 1

        reason = game_stats["reason"]
        if reason in aggregate_data["reasons"]:
            aggregate_data["reasons"][reason] += 1
        else:
            aggregate_data["reasons"][reason] = 1

        # Update player-specific data
        aggregate_data["player_white"]["name"] = player_white.name
        aggregate_data["player_white"]["model"] = (
            player_white.llm_config["config_list"][0]["model"]
            if player_white.llm_config
            else ""
        )
        aggregate_data["player_white"]["total_material"] += game_stats[
            "material_count"
        ]["white"]
        aggregate_data["player_white"]["material_list"].append(
            game_stats["material_count"]["white"]
        )
        aggregate_data["player_white"]["wrong_moves"] += game_stats["player_white"][
            "wrong_moves"
        ]
        aggregate_data["player_white"]["wrong_actions"] += game_stats["player_white"][
            "wrong_actions"
        ]

        aggregate_data["player_black"]["name"] = player_black.name
        aggregate_data["player_black"]["model"] = (
            player_black.llm_config["config_list"][0]["model"]
            if player_black.llm_config
            else ""
        )
        aggregate_data["player_black"]["total_material"] += game_stats[
            "material_count"
        ]["black"]
        aggregate_data["player_black"]["material_list"].append(
            game_stats["material_count"]["black"]
        )
        aggregate_data["player_black"]["wrong_moves"] += game_stats["player_black"][
            "wrong_moves"
        ]
        aggregate_data["player_white"]["reflections_used"] += game_stats[
            "player_white"
        ]["reflections_used"]
        aggregate_data["player_white"]["reflections_used_before_board"] += game_stats[
            "player_white"
        ]["reflections_used_before_board"]

        aggregate_data["player_black"]["reflections_used"] += game_stats[
            "player_black"
        ]["reflections_used"]
        aggregate_data["player_black"]["reflections_used_before_board"] += game_stats[
            "player_black"
        ]["reflections_used_before_board"]

        aggregate_data["player_black"]["wrong_actions"] += game_stats["player_black"][
            "wrong_actions"
        ]

    # Calculate average moves
    aggregate_data["average_moves"] = (
        aggregate_data["total_moves"] / aggregate_data["total_games"]
    )

    # Calculate standard deviation of moves
    aggregate_data["std_dev_moves"] = statistics.stdev(moves_list)
    # Calculate average and standard deviation for material
    aggregate_data["player_white"]["avg_material"] = (
        aggregate_data["player_white"]["total_material"] / aggregate_data["total_games"]
    )
    aggregate_data["player_white"]["std_dev_material"] = statistics.stdev(
        aggregate_data["player_white"]["material_list"]
    )

    aggregate_data["player_black"]["avg_material"] = (
        aggregate_data["player_black"]["total_material"] / aggregate_data["total_games"]
    )
    aggregate_data["player_black"]["std_dev_material"] = statistics.stdev(
        aggregate_data["player_black"]["material_list"]
    )

    # Persist run metadata into aggregate results
    if _run_metadata:
        aggregate_data["run_metadata"] = _run_metadata

    aggregate_filename = os.path.join(LOG_FOLDER, "_aggregate_results.json")
    del aggregate_data["player_white"]["material_list"]
    del aggregate_data["player_black"]["material_list"]
    with open(aggregate_filename, "w", encoding="utf-8") as aggregate_file:
        json.dump(aggregate_data, aggregate_file, indent=4)

    print("\n\n\033[92m" + json.dumps(aggregate_data, indent=4) + "\033[0m")


# ---------------------------------------------------------------------------
# Log folder construction helpers (moved here from log_paths.py)
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Replace disallowed characters with '-'; allow A-Z a-z 0-9 . _ -.
    Collapse multiple dashes and trim.
    """
    if name is None:
        return "unknown"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "unknown"


def _extract_llm_model_and_suffix(cfg: Optional[Dict]) -> str:
    """Return model name with suffixes based on reasoning_effort and thinking budget.

    Suffix rules:
    - add '-<reasoning_effort>' if present (low|medium|high)
    - add '-tb_<budget>' if thinking enabled with budget_tokens
    Order: reasoning first, then thinking budget.
    """
    if not cfg or not isinstance(cfg, dict):
        return "unknown"
    provider_conf = (cfg.get("config_list") or [{}])[0]
    model_name = _slugify(provider_conf.get("model", "unknown"))

    suffix_parts = []
    reasoning = provider_conf.get("reasoning_effort")
    if isinstance(reasoning, str) and reasoning:
        suffix_parts.append(reasoning)

    # Thinking may be inside provider_conf["thinking"]["budget_tokens"],
    # but check also top-level for resilience
    thinking = provider_conf.get("thinking") or cfg.get("thinking")
    if isinstance(thinking, dict):
        budget = thinking.get("budget_tokens")
        if isinstance(budget, int) and budget > 0:
            suffix_parts.append(f"tb_{budget}")

    if suffix_parts:
        return f"{model_name}-{'-'.join(_slugify(p) for p in suffix_parts)}"
    return model_name


def _engine_id_and_level(
    player_type: llm_chess.PlayerType,
    stockfish_level_override: Optional[int] = None,
    dragon_level_override: Optional[int] = None,
) -> Optional[Tuple[str, int]]:
    if player_type == llm_chess.PlayerType.CHESS_ENGINE_STOCKFISH:
        level = (
            stockfish_level_override
            if stockfish_level_override is not None
            else llm_chess.stockfish_level
        )
        return ("stockfish", int(level))
    if player_type == llm_chess.PlayerType.CHESS_ENGINE_DRAGON:
        level = (
            dragon_level_override
            if dragon_level_override is not None
            else llm_chess.dragon_level
        )
        return ("dragon", int(level))
    return None


def _is_llm(player_type: llm_chess.PlayerType) -> bool:
    return player_type in (
        llm_chess.PlayerType.LLM_WHITE,
        llm_chess.PlayerType.LLM_BLACK,
        llm_chess.PlayerType.LLM_NON,
    )


def _now_timestamp() -> str:
    # Local time with seconds
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def build_log_folder(
    white_player_type: llm_chess.PlayerType,
    black_player_type: llm_chess.PlayerType,
    llm_config_white: Optional[Dict] = None,
    llm_config_black: Optional[Dict] = None,
    *,
    stockfish_level: Optional[int] = None,
    dragon_level: Optional[int] = None,
) -> str:
    """Compute the log folder path per project rules.

    Categories:
    - _logs/rand_vs_llm/<llm>/<ts>
    - _logs/engine_vs_llm/<engine-lvl>/<llm>/<ts>
    - _logs/engine_vs_engine/<whiteEngine-lvl>_vs_<blackEngine-lvl>/<ts>
    - _logs/llm_vs_llm/<whiteLLM>_vs_<blackLLM>/<ts>
    - _logs/misc/<ts>  (fallback for other setups, incl. rand_vs_rand or engine_vs_rand)
    """
    ts = _now_timestamp()

    white_engine = _engine_id_and_level(
        white_player_type, stockfish_level, dragon_level
    )
    black_engine = _engine_id_and_level(
        black_player_type, stockfish_level, dragon_level
    )

    white_is_llm = _is_llm(white_player_type)
    black_is_llm = _is_llm(black_player_type)

    # 1) rand_vs_llm
    if (white_player_type == llm_chess.PlayerType.RANDOM_PLAYER and black_is_llm) or (
        black_player_type == llm_chess.PlayerType.RANDOM_PLAYER and white_is_llm
    ):
        llm_cfg = llm_config_black if black_is_llm else llm_config_white
        llm_name = _extract_llm_model_and_suffix(llm_cfg)
        return f"_logs/rand_vs_llm/{llm_name}/{ts}"

    # 2) engine_vs_llm (color agnostic, engine segment first)
    if (white_engine and black_is_llm) or (black_engine and white_is_llm):
        engine_id, level = white_engine if white_engine else black_engine  # type: ignore
        llm_cfg = llm_config_black if black_is_llm else llm_config_white
        llm_name = _extract_llm_model_and_suffix(llm_cfg)
        return f"_logs/engine_vs_llm/{engine_id}-lvl-{level}/{llm_name}/{ts}"

    # 3) engine_vs_engine (ordered by color: white first, then black)
    if white_engine and black_engine:
        w_id, w_lvl = white_engine
        b_id, b_lvl = black_engine
        return f"_logs/engine_vs_engine/{w_id}-lvl-{w_lvl}_vs_{b_id}-lvl-{b_lvl}/{ts}"

    # 4) llm_vs_llm (ordered by color)
    if white_is_llm and black_is_llm:
        white_name = _extract_llm_model_and_suffix(llm_config_white)
        black_name = _extract_llm_model_and_suffix(llm_config_black)
        return f"_logs/llm_vs_llm/{white_name}_vs_{black_name}/{ts}"

    # 5) misc (engine_vs_random, random_vs_random, or anything else)
    return f"_logs/misc/{ts}"


if __name__ == "__main__":
    run_games()
