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

# Try relative import first (for tests)
try:
    from .aggregate_logs_to_csv import aggregate_models_to_csv, MODEL_OVERRIDES
except ImportError:
    # Add project root to path (for direct script execution)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    # Now try the direct import
    from data_processing.aggregate_logs_to_csv import aggregate_models_to_csv, MODEL_OVERRIDES

# Define a list of log directories to process
LOGS_DIRS = [
    "_logs/no_reflection",
    "_logs/new/deepseek-v3-0324"
    # "_logs/new"
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
        
        rows.append([
            rank,
            player_name,
            win_loss,
            game_duration,
            tokens_str,
            cost_str,
            total_games,
            total_cost_str
        ])
    
    # Print the table with headers
    headers = ['#', 'Player', 'Win/Loss', 'Game Duration', 'Tokens', 'Cost/Game', 'Games', 'Total Cost']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal cost across all models: ${total_cost_all_models:.2f}")


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
    
    # Step 3: Print the leaderboard
    print("\n=== LLM CHESS LEADERBOARD ===\n")
    print_leaderboard(REFINED_CSV)
    
    print("\nMETRICS EXPLANATION:")
    print("- Win/Loss: Difference between wins and losses as a percentage (0-100%). Higher is better.")
    print("- Game Duration: Percentage of maximum possible game length completed (0-100%). Higher indicates better instruction following.")
    print("- Tokens: Number of tokens generated per move. Shows model verbosity/efficiency.")
    print("- Cost/Game: Average cost per game with margin of error. Lower is more economical.")
    print("- Total Cost: Total cost across all games for this model.")


if __name__ == "__main__":
    main()
