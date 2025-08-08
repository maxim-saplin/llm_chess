import datetime
import os
import json
import statistics  # Import the statistics module
from utils import setup_console_logging, get_llms
from get_run_metadata import collect_run_metadata, write_run_metadata
import llm_chess

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
    "reasoning_effort": "low",
}


LLM_CONFIG_WHITE, LLM_CONFIG_BLACK = get_llms(
    white_hyperparams=WHITE_HYPERPARAMS,
    black_hyperparams=BLACK_HYPERPARAMS,
)


model_name_white = LLM_CONFIG_WHITE["config_list"][0]["model"]
model_name_black = LLM_CONFIG_BLACK["config_list"][0]["model"]

NUM_REPETITIONS = 33  # Set the number of games to run
LOG_FOLDER = f"_logs/new/{model_name_black}/{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}"
# LOG_FOLDER = f"_logs/llm_vs_llm/{model_name_white}-{reasoning_effort_white}_vs_{model_name}-{reasoning_effort_black}"
STORE_INDIVIDUAL_LOGS = True

llm_chess.throttle_delay = 0
llm_chess.dialog_turn_delay = 1
# llm_chess.board_representation_mode = llm_chess.BoardRepresentation.UNICODE_WITH_PGN
# llm_chess.rotate_board_for_white = True

## r"<think>.*?</think>" - Deepseek R1 Distil, Phi-4, Qwen 3 thinking
## r"◁think▷.*?◁/think▷ - Kimi 1.5
## r"<reasoning>.*?</reasoning>" - Reka Flash
llm_chess.remove_text = r"<think>.*?</think>"

# llm_chess.dragon_path = "dragon/dragon-linux"
# llm_chess.dragon_level = 10
# LOG_FOLDER = f"_logs/dragon_vs_llm/lvl-{llm_chess.dragon_level}_vs_{model_name}-{llm_chess.reasoning_effort}/{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}"

# llm_chess.white_player_type = llm_chess.PlayerType.CHESS_ENGINE_DRAGON
# llm_chess.black_player_type = llm_chess.PlayerType.LLM_NON

NON_LLM_CONFIGS_WHITE = [
    {**LLM_CONFIG_WHITE, "temperature": 0.0},
    {**LLM_CONFIG_WHITE, "temperature": 1.0},
]
NON_LLM_CONFIGS_BLACK = [
    {**LLM_CONFIG_BLACK, "temperature": 0.0},
    {**LLM_CONFIG_BLACK, "temperature": 1.0},
]

# llm_chess.non_llm_configs_black = [
#             {
#                 **llm_chess.llm_config_white,
#                 "temperature": 1.0,
#                 "reasoning_effort": "low"
#             },
#             {
#                 **llm_chess.llm_config_white,
#                 "temperature": 1.0,
#                 "reasoning_effort": "low"
#             },
#             {
#                 **llm_chess.llm_config_white,
#                 "temperature": 1.0,
#                 "reasoning_effort": "low"
#             },
#         ]

def run_games():
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


if __name__ == "__main__":
    run_games()
