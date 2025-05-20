"""
Convert aggregated chess game statistics
from a CSV file into a refined format used for Web publishing.
The refined format includes calculated
percentages and differences that are useful for analyzing player performance
over multiple games.

Functions:
    convert_aggregate_to_refined(aggregate_file, refined_file):
        Reads an aggregate CSV file containing game statistics, processes the
        data to calculate additional metrics, and writes the results to a
        refined CSV file with a new structure.

Usage:
    Set constants to path and run as script OR call the convert_aggregate_to_refined() function
"""

import sys
import os
import csv
from tabulate import tabulate  # Add this import for the print_leaderboard function
from results_for_paper import graph_results, graph_scaling_results, graph_loss_reasons, generate_latex_instruction_following_table, generate_winpct_vs_winrate_scatter

# Try relative import first (for tests)
try:
    from .aggregate_logs_to_csv_for_paper import aggregate_models_to_csv, MODEL_OVERRIDES
except ImportError:
    # Add project root to path (for direct script execution)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    # Now try the direct import for paper version
    from data_processing.aggregate_logs_to_csv_for_paper import aggregate_models_to_csv, MODEL_OVERRIDES

# Define a list of log directories to process
# if key/value is provided, the key is the directory path and the value is the alias for all models in that directory
LOGS_DIRS = [
    "_logs/no_reflection",
    "_logs/new/deepseek-v3-0324",
    "_logs/new/anthropic.claude-v3-5-haiku",
    "_logs/new/mercury-coder-small",
    "_logs/new/non_gpt-4o-mini-2024-07-18_t00_07_03",
    "_logs/new/gpt-4o-mini-2024-07-18_moa_baseline_2025-04-12",
    {"_logs/new/llama-4-scout-17b-16e-instruct" : "llama-4-scout-cerebras"},
    "_logs/new/gpt-4.1-mini-2025-04-14",
    "_logs/new/gpt-4.1-nano-2025-04-14",
    "_logs/new/gpt-4.5-preview-2025-02-27_openai",
    "_logs/new/gpt-4.5-preview-2025-02-27",
    {"_logs/new/o4-mini-2025-04-16-low": "o4-mini-2025-04-16-low"},
    {"_logs/new/o4-mini-2025-04-16-medium": "o4-mini-2025-04-16-medium"},
    # {"_logs/new/o4-mini-2025-04-16-high": "o4-mini-2025-04-16-high"},
    # {"_logs/new/claude-3-7-sonnet-20250219-thinking_budget_1024": "claude-v3-7-sonnet-thinking_1024"},
    # {"_logs/new/claude-3-7-sonnet-20250219-thinking_budget_2048": "claude-v3-7-sonnet-thinking_2048"},
    # {"_logs/new/claude-3-7-sonnet-20250219-thinking_budget_5000": "claude-v3-7-sonnet-thinking_5000"},
    {"_logs/new/claude-3-7-sonnet-20250219-thinking_budget_10000": "claude-v3-7-sonnet-thinking_10000"},
    {"_logs/new/o1-2024-12-17-medium": "o1-2024-12-17-medium"},
    {"_logs/new/o1-2024-12-17-medium_openai": "o1-2024-12-17-medium"},
    # {"_logs/ensemble-ai/mini41-2025-04-14_t00_t07_t03": "non_gpt-4.1-mini-2025-04-14_t00_t07_t03"},
    # {"_logs/ensemble-ai/haiku35-t07_haiku35-t10_haiku35-t03": "non-haiku35-t07_haiku35-t10_haiku35-t03"},
    # {"_logs/ensemble-ai/nano41-t00_nano41-t03_nano41-t05_nano41-t07_nano-t10_nano41-t03": "non-nano41-t00_nano41-t03_nano41-t05_nano41-t07_nano-t10_nano41-t03"},
    # {"_logs/ensemble-ai/nano41-t03_nano41-t05_nano41-t07_nano-t10_nano41-t03": "non-nano41-t03_nano41-t05_nano41-t07_nano-t10_nano41-t03"},
    # {"_logs/ensemble-ai/nano41-t05_nano41-t07_nano-t10_nano41-t03": "non-nano41-t05_nano41-t07_nano-t10_nano41-t03"},
    {"_logs/new/o3-2025-04-16-medium-timeout1200": "o3-2025-04-16-medium"},
    {"_logs/new/o3-2025-04-16-low": "o3-2025-04-16-low"},
    # {"_logs/new/o3-mini-2025-01-31-high": "o3-mini-2025-01-31-high"},
    "_logs/new/gemini-2.5-pro-preview-03-25",
    # {"_logs/ensemble-ai/gemini-25pro-t03_mini41-t00_mini41-t03": "non-gemini-25pro-t03_mini41-t00_mini41-t03"},
    # {"_logs/ensemble-ai/r1-t03-with<think>_mini41-t10_mini41-t03": "non-r1-t03_mini41-t10_mini41-t03"},
    # {"_logs/ensemble-ai/haiku35-t07_haiku35-t10_haiku35-t03": "non-haiku35-t07_haiku35-t10_haiku35-t03"},
    # {"_logs/ensemble-ai/r1-14b-t03_haiku35-t10_haiku35-t03": "non-r1-14b-t03_haiku35-t10_haiku35-t03"},
    # {"_logs/ensemble-ai/r1-14b-t03_mini41-t10_mini41-t03": "non-r1-14b-t03_mini41-t10_mini41-t03"},
    # {"_logs/ensemble-ai/r1-t03_mini41-t10_mini41-t03": "non-r1-t03_mini41-t10_mini41-t03"},
    # "_logs/new"
    "_logs/new/gpt-4.1-2025-04-14",
    {"_logs/new/o4-mini-2025-04-16-high": "o4-mini-2025-04-16-high"},
    {"_logs/new/grok-3-mini-beta-low" : "grok-3-mini-beta-low"},
    {"_logs/new/grok-3-mini-beta-high" : "grok-3-mini-beta-high"},
]

FILTER_OUT_BELOW_N = 30 # 0
DATE_AFTER = None # "2025.04.01_00:00"

# Output files
OUTPUT_DIR = "data_processing"
AGGREGATE_CSV = os.path.join(OUTPUT_DIR, "aggregate.csv")
REFINED_CSV = os.path.join(OUTPUT_DIR, "refined.csv")

FILTER_OUT_MODELS = [
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp06",
    "anthropic.claude-v3-5-sonnet",
    "llama-3.1-tulu-3-8b@q4_k_m",
    "llama-3.1-8b-instant",  # Groq
    "meta-llama-3.1-8b-instruct-fp16",  # local
    "gemini-2.0-pro-exp-02-05", # to many errors, I'm done with EXP models, to much trouble, going to use only release versions
    "qwq-32b-thinking-not-cleaned",
    "google_gemma-3-27b-it@q4_k_m",
    "google_gemma-3-12b-it@q4_k_m",
    "ignore",  # models marked to be ignored via aggregate_models_to_csv.MODEL_OVERRIDES
]

ALIASES = {
    "deepseek-r1-distill-qwen-32b@q4_k_m|isol_temp06": "deepseek-r1-distill-qwen-32b@q4_k_m",
    "deepseek-reasoner": "deepseek-reasoner-r1",  # at the time of testing (Jan 2025) R1 was called "deepseek-reasoner"
    "deepseek-chat": "deepseek-chat-v3",  # at the time of testing (Jan 2025) V3 was called "deepseek-chat"
    "deepseek-chat-0324": "deepseek-chat-v3-0324",
    "gemma2-9b-it": "gemma2-9b-it-groq",
    "anthropic.claude-v3-5-sonnet-v1": "claude-v3-5-sonnet-v1",
    "anthropic.claude-v3-5-sonnet-v2": "claude-v3-5-sonnet-v2",
    "anthropic.claude-v3-haiku": "claude-v3-haiku",
    "anthropic.claude-v3-5-haiku": "claude-v3-5-haiku",
    "anthropic.claude-v3-opus": "claude-v3-opus",
    "anthropic.claude-3-7-sonnet-20250219-v1:0": "claude-v3-7-sonnet",
    "google_gemma-3-12b-it@iq4_xs": "gemma-3-12b-it@iq4_xs",
    "google_gemma-3-12b-it@q8_0": "gemma-3-12b-it@q8_0",
    "google_gemma-3-27b-it@iq4_xs": "gemma-3-27b-it@iq4_xs",
}


def convert_aggregate_to_refined(
    aggregate_file,
    refined_file,
    filter_out_below_n=30,
    filter_out_models=None,
    model_aliases=None,
):
    if filter_out_models is None:
        filter_out_models = []
    if model_aliases is None:
        model_aliases = {}

    with open(aggregate_file, "r") as agg_file:
        reader = csv.DictReader(agg_file)

        # Define the headers for the refined CSV
        refined_headers = [
            "Player",
            "total_games",
            "player_wins",
            "opponent_wins",
            "draws",
            "player_wins_percent",
            "player_draws_percent",
            "average_moves",
            "moe_average_moves",
            "total_moves",
            "player_wrong_actions",
            "player_wrong_moves",
            "wrong_actions_per_1000moves",
            "wrong_moves_per_1000moves",
            "mistakes_per_1000moves",
            "moe_mistakes_per_1000moves",
            "player_avg_material",
            "opponent_avg_material",
            "material_diff_player_llm_minus_opponent",
            "moe_material_diff_llm_minus_rand",
            "completion_tokens_black_per_move",
            "moe_completion_tokens_black_per_move",
            "moe_black_llm_win_rate",
            "moe_draw_rate",
            "moe_black_llm_loss_rate",
            "win_loss",
            "moe_win_loss", 
            "win_loss_non_interrupted",
            "moe_win_loss_non_interrupted",
            "game_duration",
            "moe_game_duration",
            "games_interrupted",
            "games_interrupted_percent",
            "moe_games_interrupted",
            "games_not_interrupted",
            "games_not_interrupted_percent",
            "moe_games_not_interrupted",
            "average_game_cost",
            "moe_average_game_cost",
            # For reasons
            "reason_too_many_wrong_actions",
            "reason_checkmate",
            "reason_stalemate",
            "reason_insufficient_material",
            "reason_seventyfive_moves",
            "reason_fivefold_repetition",
            "reason_max_turns",
            "reason_unknown_issue",
            "reason_max_moves",
            "reason_error",
            # Add white and black checkmate columns
            "white_checkmates",
        "black_checkmates",
        # API actions per move metrics
        "get_board_actions_per_move",
        "get_legal_moves_per_move",
        "make_move_per_move",
        ]

        # Prepare to write to the refined CSV
        with open(refined_file, "w", newline="") as ref_file:
            writer = csv.DictWriter(ref_file, fieldnames=refined_headers)
            writer.writeheader()

            rows_to_write = []

            for row in reader:
                # Filter out models based on the filter_out_models list
                model_name = row["model_name"]
                if model_name in filter_out_models:
                    continue

                # Use alias for the model name if available
                model_name = model_aliases.get(model_name, model_name)

                # Calculate the necessary fields for the refined CSV
                total_games = int(row["total_games"])
                if total_games < filter_out_below_n:
                    continue

                player_wins = int(row["black_llm_wins"])
                opponent_wins = int(row["white_rand_wins"])
                draws = int(row["draws"])
                total_moves = int(row["llm_total_moves"])
                player_wrong_actions = int(row["llm_wrong_actions"])
                player_wrong_moves = int(row["llm_wrong_moves"])
                player_avg_material = float(row["llm_avg_material"])
                opponent_avg_material = float(row["rand_avg_material"])
                material_diff = float(row["material_diff_llm_minus_rand"])
                wrong_actions_per_1000moves = float(row["wrong_actions_per_1000moves"])
                wrong_moves_per_1000moves = float(row["wrong_moves_per_1000moves"])
                mistakes_per_1000moves = float(row["mistakes_per_1000moves"])
                average_moves = float(row["average_moves"])
                completion_tokens_black_per_move = float(
                    row["completion_tokens_black_per_move"]
                )
                moe_average_moves = float(row["moe_avg_moves"])
                moe_material_diff_llm_minus_rand = float(
                    row["moe_material_diff_llm_minus_rand"]
                )
                moe_mistakes_per_1000moves = float(row["moe_mistakes_per_1000moves"])
                moe_completion_tokens_black_per_move = float(
                    row["moe_completion_tokens_black_per_move"]
                )

                # Calculate percentages
                player_wins_percent = float(row["black_llm_wins_percent"])
                player_draws_percent = float(row["black_llm_draws_percent"])

                moe_black_llm_win_rate = float(row["moe_black_llm_win_rate"])
                moe_draw_rate = float(row["moe_draw_rate"])

                # Calculate pct of losses for each reason
                total_losses = opponent_wins + draws
                reason_sum = sum(
                    [int(row["reason_too_many_wrong_actions"]),
                    int(row["reason_checkmate"]),
                    int(row["reason_stalemate"]),
                    int(row["reason_insufficient_material"]),
                    int(row["reason_seventyfive_moves"]),
                    int(row["reason_fivefold_repetition"]),
                    int(row["reason_max_turns"]),
                    int(row["reason_unknown_issue"]),
                    int(row["reason_max_moves"]),
                    int(row["reason_error"])]
                )
                assert reason_sum == total_games, (
                    f"Sum of reasons does not equal total games for {model_name}: {reason_sum} != {total_games}"
                )
                reason_too_many_wrong_actions = int(row["reason_too_many_wrong_actions"])/total_games
                reason_checkmate = int(row["reason_checkmate"])/total_games
                reason_stalemate = int(row["reason_stalemate"])/total_games
                reason_insufficient_material = int(row["reason_insufficient_material"])/total_games
                reason_seventyfive_moves = int(row["reason_seventyfive_moves"])/total_games
                reason_fivefold_repetition = int(row["reason_fivefold_repetition"])/total_games
                reason_max_turns = int(row["reason_max_turns"])/total_games
                reason_unknown_issue = int(row["reason_unknown_issue"])/total_games
                reason_max_moves = int(row["reason_max_moves"])/total_games
                reason_error = int(row["reason_error"])/total_games
                white_checkmates = int(row["white_rand_checkmates"])
                black_checkmates = int(row["black_llm_checkmates"])
                # API actions per move metrics
                get_board_actions_per_move = float(row.get("get_board_actions_per_move", 0))
                get_legal_moves_per_move = float(row.get("get_legal_moves_per_move", 0))
                make_move_per_move = float(row.get("make_move_per_move", 0))

                # Calculate loss rate statistics
                moe_black_llm_loss_rate = float(row["moe_black_llm_loss_rate"])

                # Get new metrics
                win_loss = float(row["win_loss"])
                moe_win_loss = float(row["moe_win_loss"])
                win_loss_non_interrupted = float(row["win_loss_non_interrupted"])
                moe_win_loss_non_interrupted = float(row["moe_win_loss_non_interrupted"])
                game_duration = float(row["game_duration"])
                moe_game_duration = float(row["moe_game_duration"])
                games_interrupted = int(row["games_interrupted"])
                games_interrupted_percent = float(row["games_interrupted_percent"])
                moe_games_interrupted = float(row["moe_games_interrupted"])
                games_not_interrupted = int(row["games_not_interrupted"])
                games_not_interrupted_percent = float(row["games_not_interrupted_percent"])
                moe_games_not_interrupted = float(row["moe_games_not_interrupted"])

                # Get cost metrics
                average_game_cost = float(row.get("average_game_cost", 0))
                moe_average_game_cost = float(row.get("moe_average_game_cost", 0))

                # Append the row to the list of rows to write
                rows_to_write.append(
                    {
                        "Player": model_name,
                        "total_games": total_games,
                        "player_wins": player_wins,
                        "opponent_wins": opponent_wins,
                        "draws": draws,
                        "player_wins_percent": round(player_wins_percent, 3),
                        "player_draws_percent": round(player_draws_percent, 3),
                        "average_moves": round(average_moves, 3),
                        "moe_average_moves": round(moe_average_moves, 3),
                        "total_moves": total_moves,
                        "player_wrong_actions": player_wrong_actions,
                        "player_wrong_moves": player_wrong_moves,
                        "wrong_actions_per_1000moves": round(wrong_actions_per_1000moves, 3),
                        "wrong_moves_per_1000moves": round(wrong_moves_per_1000moves, 3),
                        "mistakes_per_1000moves": round(mistakes_per_1000moves, 3),
                        "moe_mistakes_per_1000moves": round(moe_mistakes_per_1000moves, 3),
                        "player_avg_material": round(player_avg_material, 3),
                        "opponent_avg_material": round(opponent_avg_material, 3),
                        "material_diff_player_llm_minus_opponent": round(material_diff, 3),
                        "moe_material_diff_llm_minus_rand": round(moe_material_diff_llm_minus_rand, 3),
                        "completion_tokens_black_per_move": round(completion_tokens_black_per_move, 3),
                        "moe_completion_tokens_black_per_move": round(moe_completion_tokens_black_per_move, 3),
                        "moe_black_llm_win_rate": round(moe_black_llm_win_rate, 3),
                        "moe_draw_rate": round(moe_draw_rate, 3),
                        "moe_black_llm_loss_rate": round(moe_black_llm_loss_rate, 3),
                        "win_loss": round(win_loss, 3),
                        "moe_win_loss": round(moe_win_loss, 3),
                        "win_loss_non_interrupted": round(win_loss_non_interrupted, 3),
                        "moe_win_loss_non_interrupted": round(moe_win_loss_non_interrupted, 3),
                        "game_duration": round(game_duration, 3),
                        "moe_game_duration": round(moe_game_duration, 3),
                        "games_interrupted": games_interrupted,
                        "games_interrupted_percent": round(games_interrupted_percent, 3),
                        "moe_games_interrupted": round(moe_games_interrupted, 3),
                        "games_not_interrupted": games_not_interrupted,
                        "games_not_interrupted_percent": round(games_not_interrupted_percent, 3),
                        "moe_games_not_interrupted": round(moe_games_not_interrupted, 3),
                        "average_game_cost": round(average_game_cost, 5),
                        "moe_average_game_cost": round(moe_average_game_cost, 5),
                        # reasons
                        "reason_too_many_wrong_actions": reason_too_many_wrong_actions,
                        "reason_checkmate": reason_checkmate,
                        "reason_stalemate": reason_stalemate,
                        "reason_insufficient_material": reason_insufficient_material,
                        "reason_seventyfive_moves": reason_seventyfive_moves,
                        "reason_fivefold_repetition": reason_fivefold_repetition,
                        "reason_max_turns": reason_max_turns,
                        "reason_unknown_issue": reason_unknown_issue,
                        "reason_max_moves": reason_max_moves,
                        "reason_error": reason_error,
                        # Add white and black checkmate columns
                        "white_checkmates": white_checkmates,
                        "black_checkmates": black_checkmates,
                        # API actions per move metrics
                        "get_board_actions_per_move": round(get_board_actions_per_move, 3),
                        "get_legal_moves_per_move": round(get_legal_moves_per_move, 3),
                        "make_move_per_move": round(make_move_per_move, 3),
                    }
                )

            # Write all rows to the refined CSV
            writer.writerows(rows_to_write)

def print_leaderboard(csv_file, top_n=None):
    """Print a formatted leaderboard to the console with the same metrics as the web version."""
    rows = []
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    # Sort data using the same logic as in the web version:
    # Win/Loss DESC, then Game Duration DESC, then Tokens ASC
    sorted_data = sorted(
        data, 
        key=lambda x: (
            -float(x['win_loss']),  # DESC
            -float(x['game_duration']),  # DESC
            float(x['completion_tokens_black_per_move'])  # ASC
        )
    )
    
    # Limit to top N if specified
    if top_n:
        sorted_data = sorted_data[:top_n]
    
    # Prepare data for tabulate
    total_cost_all_models = 0.0
    for rank, row in enumerate(sorted_data, 1):
        player_name = row['Player']
        
        # Format the metrics like in the web version
        win_loss = f"{float(row['win_loss']) * 100:.2f}%"
        game_duration = f"{float(row['game_duration']) * 100:.2f}%"
        tokens = float(row['completion_tokens_black_per_move'])
        tokens_str = f"{tokens:.1f}" if tokens > 1000 else f"{tokens:.2f}"
        
        # Format the cost with margin of error
        cost = float(row['average_game_cost'])
        moe = float(row['moe_average_game_cost'])
        cost_str = f"${cost:.4f}±{moe:.4f}"
        
        # Calculate total cost per model
        total_games = int(row['total_games'])
        total_cost = cost * total_games
        total_cost_str = f"${total_cost:.2f}"
        total_cost_all_models += total_cost
        
        # Calculate estimated time per game - simplified approach
        avg_moves = float(row['average_moves'])
        tokens_per_game = tokens * avg_moves
        # Multiply by 1.05 to account for input processing time
        adjusted_tokens = tokens_per_game * 1.05
        # Assume 100 tokens/second processing speed
        total_time = adjusted_tokens / 100  # seconds
        
        # Format time based on duration
        if total_time < 60:
            time_str = f"{total_time:.1f}s"
        elif total_time < 3600:
            time_str = f"{total_time/60:.1f}m"
        else:
            time_str = f"{total_time/3600:.2f}h"
        
        rows.append([
            rank,
            player_name,
            win_loss,
            game_duration,
            tokens_str,
            cost_str,
            time_str,
            total_games,
            total_cost_str
        ])
    
    # Print the table with headers
    headers = ['#', 'Player', 'Win/Loss', 'Game Duration', 'Tokens', 'Cost/Game', 'Time/Game', 'Games', 'Total Cost']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal cost across all models: ${total_cost_all_models:.2f}")

def clean_names_mapping(REFINED_CSV):
    """Mapping from model names to their cleaned versions."""
    # first print all the names in the csv
    with open(REFINED_CSV, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    # Get all unique model names
    model_names = set(row['Player'] for row in data)
    # Print the model names
    print("Unique model names in the CSV:")
    for name in model_names:
        print(name)
    # The logic is for the main body we remove quantization tags, as well as dates iff we only have one model with that name. If we have multiple models with the same name (e.g., gpt-4o-2024-05-13 and gpt-4o-2024-11-20) we keep the date.
    api_name_mapping = {
        "gpt-4-0613": "GPT-4",
        "qwen2.5-7b-instruct-1m": "Qwen2.5-7B-Instruct",
        "internlm3-8b-instruct": "InternLM3-8B-Instruct",
        "qwen-max-2025-01-25": "Qwen2.5-Max",  # double check
        "qwen2.5-14b-instruct@q8_0": "Qwen2.5-14B-Instruct (Q8)",
        "qwq-32b": "QWQ-32B",
        "o3-2025-04-16-low": "o3 (low)",
        "gpt-4o-2024-08-06": "GPT-4o (2024-08-06)",
        "mistral-nemo-12b-instruct-2407": "Mistral-Nemo-Instruct-2407",
        "gpt-35-turbo-1106": "GPT-3.5 Turbo (11/06)",
        "o1-preview-2024-09-12": "o1-preview",
        "grok-3-mini-beta-high": "Grok 3 Mini (high)",
        "claude-v3-5-sonnet-v1": "Claude 3.5 Sonnet",
        "amazon.nova-lite-v1": "Amazon Nova Lite",
        "gemini-2.0-flash-exp": "Gemini 2.0 Flash (exp)",
        "o4-mini-2025-04-16-low": "o4-mini (low)",
        "llama-3-70b-instruct-awq": "Llama-3-70B-Instruct",
        "gpt-4.5-preview-2025-02-27": "GPT-4.5",
        "deepseek-chat-v3": "DeepSeek-V3",
        "gemma-2-27b-it@q6_k_l": "Gemma 2 27B",
        "llama3.1-8b": "Llama-3.1-8B",
        "claude-v3-5-haiku": "Claude 3.5 Haiku",
        "qwen2.5-72b-instruct": "Qwen2.5-72B-Instruct",
        "gpt-4.1-nano-2025-04-14": "GPT-4.1 Nano",
        "granite-3.1-8b-instruct": "Granite-3.1-8B-Instruct",
        "llama3-8b-8192": "Llama-3-8B",
        "gemma2-9b-it-groq": "Gemma 2 9B",
        "qwen-turbo-2024-11-01": "Qwen Turbo",
        "gpt-4o-2024-11-20": "GPT-4o (2024-11-20)",
        "amazon.nova-pro-v1": "Amazon Nova Pro",
        "o1-2024-12-17-low": "o1 (low)",
        "qwen-plus-2025-01-25": "Qwen Plus",
        "gpt-35-turbo-0301": "GPT-3.5 Turbo (03/01)",
        "mercury-coder-small": "Mercury Coder Small",
        "deephermes-3-llama-3-8b-preview@q8": "DeepHermes-3-Llama-3-8B-Preview",
        "o4-mini-2025-04-16-high": "o4-mini (high)",
        "gpt-4o-mini-2024-07-18": "GPT-4o Mini",
        "gpt-4-turbo-2024-04-09": "GPT-4 Turbo",
        "o4-mini-2025-04-16-medium": "o4-mini (medium)",
        "gemini-2.5-pro-preview-03-25": "Gemini 2.5 Pro Preview",
        "gpt-4-32k-0613": "GPT-4 32K",
        "phi-4": "Phi-4",
        "gemini-2.0-flash-thinking-exp-1219": "Gemini 2.0 Flash Thinking",
        "mistral-small-instruct-2409": "Mistral-Small-Instruct-2409",
        "mistral-small-24b-instruct-2501@q4_k_m": "Mistral-Small-24B-Instruct-2501",
        "llama-2-7b-chat": "Llama-2-7B-Chat",
        "gemma-3-12b-it@iq4_xs": "Gemma 3 12B (iq4)",
        "claude-v3-7-sonnet-thinking_10000": "Claude 3.7 Sonnet Thinking",
        "gemini-1.5-flash-001": "Gemini 1.5 Flash",
        "deepseek-chat-v3-0324": "DeepSeek-V3 (0324)",
        "deepseek-reasoner-r1": "Deepseek-R1",
        "llama-4-scout-cerebras": "Llama 4 Scout",
        "chat-bison-32k@002": "Chat-Bison-32K",
        "qwen2.5-14b-instruct-1m": "Qwen2.5-14B-Instruct",
        "o1-2024-12-17-medium": "o1 (medium)",
        "claude-v3-haiku": "Claude 3 Haiku",
        "grok-3-mini-beta-low": "Grok 3 Mini (low)",
        "o3-mini-2025-01-31-low": "o3-mini (low)",
        "llama-3.1-tulu-3-8b@q8_0": "Llama-3.1-Tulu-3-8B",
        "gpt-4o-2024-05-13": "GPT-4o (2024-05-13)",
        "gpt-35-turbo-0125": "GPT-3.5 Turbo (01/25)",
        "claude-v3-7-sonnet": "Claude 3.7 Sonnet",
        "gemma-2-9b-it-8bit": "Gemma 2 9B (8bit)",
        "gpt-35-turbo-0613": "GPT-3.5 Turbo (06/13)",
        "gemini-2.0-flash-lite-preview-02-05": "Gemini 2.0 Flash Lite (preview)",
        "o3-mini-2025-01-31-medium": "o3-mini (medium)",
        "gpt-4.1-2025-04-14": "GPT-4.1",
        "gemini-2.0-flash-lite-001": "Gemini 2.0 Flash Lite",
        "o3-2025-04-16-medium": "o3 (medium)",
        "gemini-2.0-flash-001": "Gemini 2.0 Flash",
        "deepseek-r1-distill-qwen-14b@q8_0": "DeepSeek-R1-Distill-Qwen-14B",
        "ministral-8b-instruct-2410": "Mistral 8B Instruct",
        "deepseek-r1-distill-qwen-32b@q4_k_m": "DeepSeek-R1-Distill-Qwen-32B",
        "llama-3.3-70b": "Llama-3.3-70B",
        "grok-2-1212": "Grok-2",
        "gemma-3-12b-it@q8_0": "Gemma 3 12B (q8)",
        "gemma-3-27b-it@iq4_xs": "Gemma 3 27B",
        "claude-v3-5-sonnet-v2": "Claude 3.5 Sonnet v2",
        "gpt-4.1-mini-2025-04-14": "GPT-4.1 Mini",
    }
    # assert that all the names in the mapping are unique
    if len(api_name_mapping) != len(set(api_name_mapping.values())):
        # print the duplicates
        duplicates = {}
        for name in api_name_mapping.values():
            if name in duplicates:
                duplicates[name] += 1
            else:
                duplicates[name] = 1
        duplicates = {k: v for k, v in duplicates.items() if v > 1}
        print("Duplicates in the mapping:")
        print(duplicates)
        quit()
    # print a booktabs table of the mapping
    print("\n\\begin{table}[h]")
    print("\\centering")
    print("\\begin{tabular}{ll}")
    print("\\toprule")
    print("Model Name & API Name \\\\")
    print("\\midrule")
    for model_name, api_name in api_name_mapping.items():
        print(f"{model_name} & {api_name} \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\caption{Model name mapping}")
    print("\\label{tab:model_name_mapping}")
    print("\\end{table}")
    # now change the refined csv to use the mapping and re-save it.
    with open(REFINED_CSV, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    # Change the names in the data
    for row in data:
        model_name = row['Player']
        if model_name in api_name_mapping:
            row['Player'] = api_name_mapping[model_name]
            
    # Save the data back to the csv
    with open(REFINED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return
        

def main():
    # Step 1: Aggregate logs from all directories to a single CSV
    print(f"Processing logs from {len(LOGS_DIRS)} directories")
    aggregate_models_to_csv(LOGS_DIRS, AGGREGATE_CSV, MODEL_OVERRIDES, only_after_date=DATE_AFTER)
    print(f"Successfully aggregated data to {AGGREGATE_CSV}")

    # Step 2: Convert aggregated CSV to refined CSV
    convert_aggregate_to_refined(
        AGGREGATE_CSV,
        REFINED_CSV,
        filter_out_below_n=FILTER_OUT_BELOW_N,
        filter_out_models=FILTER_OUT_MODELS,
        model_aliases=ALIASES,
    )
    print(f"Successfully refined data to {REFINED_CSV}")

    # Step 2.5: Make a graph.
    clean_names_mapping(REFINED_CSV)
    graph_results(REFINED_CSV)
    graph_scaling_results(REFINED_CSV)
    graph_loss_reasons(REFINED_CSV)
    import pdb; pdb.set_trace()
    generate_winpct_vs_winrate_scatter(REFINED_CSV)
    # Instruction-following metrics table
    print("\n--- Instruction-Following Metrics Table ---\n")
    table_str = generate_latex_instruction_following_table(REFINED_CSV)
    print(table_str)
    input("Press Enter to continue...")
    
    # Step 3: Print the leaderboard
    print("\n=== LLM CHESS LEADERBOARD ===\n")
    print_leaderboard(REFINED_CSV)
    
    print("\nMETRICS EXPLANATION:")
    print("- Win/Loss: Difference between wins and losses as a percentage (0-100%). Higher is better.")
    print("- Game Duration: Percentage of maximum possible game length completed (0-100%). Higher indicates better instruction following.")
    print("- Tokens: Number of tokens generated per move. Shows model verbosity/efficiency.")
    print("- Cost/Game: Average cost per game with margin of error. Lower is more economical.")
    print("- Time/Game: Estimated time per game (output at 100 tok/s + 5% input processing time).")
    print("- Total Cost: Total cost across all games for this model.")


if __name__ == "__main__":
    main()
