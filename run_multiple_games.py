import datetime
import os
import json
import statistics  # Import the statistics module
from utils import setup_console_logging, get_llms_autogen
import llm_chess

HYPERPARAMS = llm_chess.default_hyperparams
# # Qwen 3 thinking recomended params
# HYPERPARAMS = {
#     "temperature": 0.7,
#     "top_p": 0.8,
# }

REASONING_EFFORT = None # Default is None, used with OpenAI models low, medium, or high
THINKING_BUDGET = None # Anrhropic thinking budget, e.g. 4096

LLM_CONFIG_WHITE, LLM_CONFIG_BLACK = get_llms_autogen(
    HYPERPARAMS,
    REASONING_EFFORT,
    THINKING_BUDGET)

# reasoning_effort_white = "high"
# reasoning_effort_black = "low"
# LLM_CONFIG_WHITE["config_list"][0]["reasoning_effort"] = reasoning_effort_white
# LLM_CONFIG_BLACK["config_list"][0]["reasoning_effort"] = reasoning_effort_black
# llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE

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
    setup_console_logging(LOG_FOLDER) # save raw console output to output.txt
    aggregate_data = {
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

    aggregate_filename = os.path.join(LOG_FOLDER, "_aggregate_results.json")
    del aggregate_data["player_white"]["material_list"]
    del aggregate_data["player_black"]["material_list"]
    with open(aggregate_filename, "w") as aggregate_file:
        json.dump(aggregate_data, aggregate_file, indent=4)

    print("\n\n\033[92m" + json.dumps(aggregate_data, indent=4) + "\033[0m")


if __name__ == "__main__":
    run_games()
