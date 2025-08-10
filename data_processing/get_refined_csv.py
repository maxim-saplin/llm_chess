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
# Restrict to rand_vs_llm per current requirement
LOGS_DIRS = [
    "_logs/rand_vs_llm",
]

FILTER_OUT_BELOW_N = 30 # 0
DATE_AFTER = None # "2025.04.01_00:00"

# Output files
OUTPUT_DIR = "data_processing"
AGGREGATE_CSV = os.path.join(OUTPUT_DIR, "aggregate.csv")
REFINED_CSV = os.path.join(OUTPUT_DIR, "refined.csv")
# Historical refined CSV to ingest/merge
PREV_REFINED_CSV = os.path.join("_logs", "_pre_aug_2025", "refined.csv")

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

# Unified refined CSV headers used across functions
REFINED_HEADERS = [
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
    "price_per_1000_moves",
    "moe_price_per_1000_moves",
]


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

    with open(aggregate_file, "r", encoding="utf-8") as agg_file:
        reader = csv.DictReader(agg_file)

        # Prepare to write to the refined CSV
        with open(refined_file, "w", newline="", encoding="utf-8") as ref_file:
            writer = csv.DictWriter(ref_file, fieldnames=REFINED_HEADERS)
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
                price_per_1000_moves = float(row.get("price_per_1000_moves", 0))
                moe_price_per_1000_moves = float(row.get("moe_price_per_1000_moves", 0))

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
                        "price_per_1000_moves": round(price_per_1000_moves, 5),
                        "moe_price_per_1000_moves": round(moe_price_per_1000_moves, 5),
                    }
                )

            # Write all rows to the refined CSV
            writer.writerows(rows_to_write)

def merge_refined_csvs(new_refined_file, old_refined_file, output_file):
    """Merge two refined CSVs into one, preferring rows from new_refined_file on Player conflicts.

    If old_refined_file does not exist, simply copy new_refined_file -> output_file.
    """
    # Load rows from new refined file
    with open(new_refined_file, "r", encoding="utf-8") as f_new:
        reader_new = csv.DictReader(f_new)
        by_player = {row.get("Player"): row for row in reader_new if row.get("Player")}

    # Load rows from old refined file if present
    if os.path.exists(old_refined_file):
        with open(old_refined_file, "r", encoding="utf-8") as f_old:
            reader_old = csv.DictReader(f_old)
            for row in reader_old:
                player = row.get("Player")
                if not player:
                    continue
                # Only add if not present; prefer new on conflict
                if player not in by_player:
                    by_player[player] = row

    # Normalize rows to have all required headers
    normalized_rows = []
    for player, row in by_player.items():
        normalized = {}
        for key in REFINED_HEADERS:
            if key in row and row[key] != "":
                normalized[key] = row[key]
            else:
                # Default missing numeric fields to 0, strings to empty
                normalized[key] = "0" if key != "Player" else player
        normalized_rows.append(normalized)

    # Write merged output
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=REFINED_HEADERS)
        writer.writeheader()
        # Sort by Win/Loss desc then Game Duration desc then Tokens asc to keep deterministic output
        def sort_key(x):
            try:
                return (
                    -float(x.get("win_loss", 0) or 0),
                    -float(x.get("game_duration", 0) or 0),
                    float(x.get("completion_tokens_black_per_move", 0) or 0),
                )
            except (ValueError, TypeError):
                return (0, 0, 0)
        for row in sorted(normalized_rows, key=sort_key):
            writer.writerow(row)

def convert_aggregate_to_refined_rows(
    aggregate_file,
    filter_out_below_n=30,
    filter_out_models=None,
    model_aliases=None,
):
    """Convert an aggregate CSV to refined row dicts in memory (no file I/O for refined)."""
    if filter_out_models is None:
        filter_out_models = []
    if model_aliases is None:
        model_aliases = {}

    refined_rows = []
    with open(aggregate_file, "r", encoding="utf-8") as agg_file:
        reader = csv.DictReader(agg_file)
        for row in reader:
            model_name = row["model_name"]
            if model_name in filter_out_models:
                continue
            model_name = model_aliases.get(model_name, model_name)
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
            completion_tokens_black_per_move = float(row["completion_tokens_black_per_move"])
            moe_average_moves = float(row["moe_avg_moves"])
            moe_material_diff_llm_minus_rand = float(row["moe_material_diff_llm_minus_rand"])
            moe_mistakes_per_1000moves = float(row["moe_mistakes_per_1000moves"])
            moe_completion_tokens_black_per_move = float(row["moe_completion_tokens_black_per_move"])
            player_wins_percent = float(row["black_llm_wins_percent"])
            player_draws_percent = float(row["black_llm_draws_percent"])
            moe_black_llm_win_rate = float(row["moe_black_llm_win_rate"])
            moe_draw_rate = float(row["moe_draw_rate"])
            moe_black_llm_loss_rate = float(row["moe_black_llm_loss_rate"])
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
            average_game_cost = float(row.get("average_game_cost", 0))
            moe_average_game_cost = float(row.get("moe_average_game_cost", 0))
            price_per_1000_moves = float(row.get("price_per_1000_moves", 0))
            moe_price_per_1000_moves = float(row.get("moe_price_per_1000_moves", 0))

            refined_rows.append({
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
                "price_per_1000_moves": round(price_per_1000_moves, 5),
                "moe_price_per_1000_moves": round(moe_price_per_1000_moves, 5),
            })
    return refined_rows

def merge_refined_rows_and_old(new_rows, old_refined_file):
    """Merge refined rows in memory with an existing refined.csv from disk.

    Prefers new_rows on Player conflicts.
    Returns merged, normalized, sorted rows.
    """
    by_player = {row.get("Player"): row for row in new_rows if row.get("Player")}

    if os.path.exists(old_refined_file):
        with open(old_refined_file, "r", encoding="utf-8") as f_old:
            reader_old = csv.DictReader(f_old)
            for row in reader_old:
                player = row.get("Player")
                if player and player not in by_player:
                    by_player[player] = row

    normalized_rows = []
    for player, row in by_player.items():
        normalized = {}
        for key in REFINED_HEADERS:
            normalized[key] = row.get(key, "0") if key != "Player" else player
        normalized_rows.append(normalized)

    def sort_key(x):
        try:
            return (
                -float(x.get("win_loss", 0) or 0),
                -float(x.get("game_duration", 0) or 0),
                float(x.get("completion_tokens_black_per_move", 0) or 0),
            )
        except (ValueError, TypeError):
            return (0, 0, 0)

    return sorted(normalized_rows, key=sort_key)

def write_refined_csv(rows, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=REFINED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

def print_leaderboard(csv_file, top_n=None):
    """Print a formatted leaderboard to the console with the same metrics as the web version."""
    rows = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
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


def main():
    # Step 1: Aggregate logs from specified directories to a single CSV
    print(f"Processing logs from {len(LOGS_DIRS)} directories: {LOGS_DIRS}")
    aggregate_models_to_csv(LOGS_DIRS, AGGREGATE_CSV, MODEL_OVERRIDES, only_after_date=DATE_AFTER)
    print(f"Successfully aggregated data to {AGGREGATE_CSV}")

    # Step 2: Convert aggregated CSV to refined rows in memory
    new_rows = convert_aggregate_to_refined_rows(
        AGGREGATE_CSV,
        filter_out_below_n=FILTER_OUT_BELOW_N,
        filter_out_models=FILTER_OUT_MODELS,
        model_aliases=ALIASES,
    )
    print(f"Successfully refined new data in memory: {len(new_rows)} rows")

    # Step 3: Merge with historical refined CSV and write final refined CSV (no intermediate files)
    merged_rows = merge_refined_rows_and_old(new_rows, PREV_REFINED_CSV)
    write_refined_csv(merged_rows, REFINED_CSV)
    print(f"Merged in-memory rows with {PREV_REFINED_CSV} into {REFINED_CSV}")

    # Step 4: Print the leaderboard for the merged refined data
    print("\n=== LLM CHESS LEADERBOARD (Merged) ===\n")
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
